"""RAG evaluation service.

Orchestrates end-to-end RAG evaluation runs: calls a configurable RAG endpoint
via httpx, extracts answer + context chunks, and scores them with the LiteLLM
judge adapter.
"""

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JudgeConfigParams, Score
from app.adapters.litellm_judge import LiteLLMJudgeAdapter
from app.core.config import settings
from app.core.providers import provider_registry
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation, JudgeConfig
from app.models.result import Result
from app.websocket.progress import broadcast_progress

logger = logging.getLogger(__name__)


def _to_judge_params(judge_config: JudgeConfig | None) -> JudgeConfigParams:
    """Convert ORM JudgeConfig to adapter-layer JudgeConfigParams dataclass."""
    if judge_config is None:
        return JudgeConfigParams()
    return JudgeConfigParams(
        model=judge_config.model,
        temperature=judge_config.temperature,
        prompt_template=judge_config.prompt_template,
        pass_threshold=judge_config.pass_threshold,
        dimensions=judge_config.dimensions,
        aggregation=judge_config.aggregation,
    )


def _normalize_chunks(raw_chunks: list[Any]) -> list[dict[str, Any]]:
    """Normalize chunks to a list of dicts, each containing at least a 'content' key.

    Handles:
    - list of dicts (pass through, ensure 'content' key exists)
    - list of strings (wrap each in {"content": str})
    """
    normalized: list[dict[str, Any]] = []
    for chunk in raw_chunks:
        if isinstance(chunk, dict):
            if "content" not in chunk:
                # Try common alternatives
                text = chunk.get("text") or chunk.get("page_content") or str(chunk)
                chunk = {**chunk, "content": text}
            normalized.append(chunk)
        elif isinstance(chunk, str):
            normalized.append({"content": chunk})
        else:
            normalized.append({"content": str(chunk)})
    return normalized


async def run_rag_evaluation(evaluation_id: str, db: AsyncSession) -> None:
    """Orchestrate a full RAG evaluation run."""
    try:
        # 1. Load evaluation
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
        evaluation = eval_result.scalar_one_or_none()
        if not evaluation:
            logger.error("Evaluation %s not found", evaluation_id)
            return
        if evaluation.status != "pending":
            logger.warning("Evaluation %s has status '%s', skipping", evaluation_id, evaluation.status)
            return

        # 2. Update status to running
        evaluation.status = "running"
        await db.commit()

        # 3. Load dataset
        if not evaluation.dataset_id:
            logger.error("Evaluation %s has no dataset_id", evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        dataset_result = await db.execute(select(Dataset).where(Dataset.id == evaluation.dataset_id))
        dataset = dataset_result.scalar_one_or_none()
        if not dataset:
            logger.error("Dataset %s not found for evaluation %s", evaluation.dataset_id, evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        # 4. Load judge config
        judge_config = None
        if evaluation.judge_config_id:
            jc_result = await db.execute(select(JudgeConfig).where(JudgeConfig.id == evaluation.judge_config_id))
            judge_config = jc_result.scalar_one_or_none()
            if not judge_config:
                logger.error("JudgeConfig %s not found for evaluation %s", evaluation.judge_config_id, evaluation_id)
                evaluation.status = "failed"
                await db.commit()
                return

        judge_params = _to_judge_params(judge_config)

        # 5. Validate RAG endpoint config
        config = evaluation.config or {}
        rag_endpoint = config.get("rag_endpoint", {})
        rag_url = rag_endpoint.get("url")
        if not rag_url:
            logger.error("No RAG endpoint URL configured for evaluation %s", evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        rag_query_field = rag_endpoint.get("query_field", "query")
        rag_answer_field = rag_endpoint.get("answer_field", "answer")
        rag_chunks_field = rag_endpoint.get("chunks_field", "source_documents")
        rag_auth_header = rag_endpoint.get("auth_header")
        rag_metrics = rag_endpoint.get("metrics", ["faithfulness", "relevancy"])

        # 6. Resolve judge model (same pattern as QA service)
        judge_api_key: str | None = None
        judge_api_base: str | None = None
        judge_model: str | None = None

        judge_ref = config.get("judge_config", {})
        judge_provider_id = judge_ref.get("provider_id") if isinstance(judge_ref, dict) else None
        judge_provider = provider_registry.get_provider(judge_provider_id) if judge_provider_id else None

        if judge_provider:
            judge_model = judge_provider.litellm_model
            judge_api_key = judge_provider.api_key
            judge_api_base = judge_provider.api_base
        elif judge_params.model:
            judge_model = judge_params.model
            judge_api_key = settings.litellm_api_key if settings.litellm_api_key else None
        elif settings.litellm_model:
            judge_model = settings.litellm_model
            judge_api_key = settings.litellm_api_key if settings.litellm_api_key else None

        if not judge_model:
            logger.error("No judge model configured for evaluation %s", evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        logger.info(
            "Judge resolved for RAG eval: model=%s, api_base=%s, has_key=%s, provider=%s",
            judge_model,
            judge_api_base,
            bool(judge_api_key),
            judge_provider_id or "none",
        )

        adapter = LiteLLMJudgeAdapter(
            model=judge_model,
            api_key=judge_api_key,
            api_base=judge_api_base,
            max_concurrency=config.get("max_concurrency", 10),
        )

        # 7. Process each dataset item
        items = sorted(dataset.items, key=lambda i: i.order_index)
        total = len(items)
        completed_counter = 0
        counter_lock = asyncio.Lock()

        async def process_item(idx: int, item: DatasetItem, client: httpx.AsyncClient) -> Result:
            nonlocal completed_counter

            # Step A: Call the RAG endpoint
            headers: dict[str, str] = {}
            if rag_auth_header:
                headers.update(rag_auth_header)

            request_body = {rag_query_field: item.question}
            response = await client.post(rag_url, json=request_body, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            # Step B: Extract answer and chunks
            actual_answer = response_json.get(rag_answer_field, "")
            raw_chunks = response_json.get(rag_chunks_field, [])
            chunks = _normalize_chunks(raw_chunks)
            chunk_contents = [c.get("content", "") for c in chunks]

            # Step C: Score with adapter (catch NotImplementedError gracefully)
            score_value: float | None = None
            passed: bool | None = None
            reasoning: str | None = None
            scores_breakdown: dict[str, float] | None = None

            try:
                metric_scores: dict[str, Score] = await adapter.evaluate_rag(
                    question=item.question,
                    context_chunks=chunk_contents,
                    answer=actual_answer,
                    expected_answer=item.expected_answer,
                    metrics=rag_metrics,
                )
                # Compute overall score as average of metric scores
                if metric_scores:
                    scores_breakdown = {k: v.value for k, v in metric_scores.items()}
                    score_value = sum(v.value for v in metric_scores.values()) / len(metric_scores)
                    threshold = judge_params.pass_threshold or 0.7
                    passed = score_value >= threshold
                    reasoning_parts = [f"{k}: {v.reasoning}" for k, v in metric_scores.items() if v.reasoning]
                    reasoning = "; ".join(reasoning_parts) if reasoning_parts else None
            except NotImplementedError:
                logger.warning(
                    "evaluate_rag not implemented in adapter; skipping scoring for evaluation %s",
                    evaluation_id,
                )
                # Leave score/breakdown as None -- we still store the answer + chunks

            # Step D: Build Result record
            result = Result(
                evaluation_id=evaluation_id,
                dataset_item_id=item.id,
                score=score_value,
                passed=passed,
                actual_answer=actual_answer,
                judge_reasoning=reasoning,
                scores_breakdown=scores_breakdown,
                retrieved_chunks=chunks,
            )

            # Step E: Broadcast progress
            async with counter_lock:
                completed_counter += 1
                current_completed = completed_counter
            await broadcast_progress(
                evaluation_id=evaluation_id,
                completed=current_completed,
                total=total,
                current_item=item.question[:100],
            )

            return result

        max_concurrency = config.get("max_concurrency", 10)
        semaphore = asyncio.Semaphore(max_concurrency)

        async def bounded_process(idx: int, item: DatasetItem, client: httpx.AsyncClient) -> Result | Exception:
            async with semaphore:
                return await process_item(idx, item, client)

        async with httpx.AsyncClient(timeout=60.0) as client:
            results = await asyncio.gather(
                *[bounded_process(i, item, client) for i, item in enumerate(items)],
                return_exceptions=True,
            )

        # 8. Collect results into the session sequentially
        error_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                error_count += 1
                logger.error("Error processing item %d for RAG evaluation %s: %s", i, evaluation_id, r)
                error_result = Result(
                    evaluation_id=evaluation_id,
                    dataset_item_id=items[i].id if i < len(items) else None,
                    score=None,
                    passed=False,
                    actual_answer=None,
                    judge_reasoning=str(r),
                )
                db.add(error_result)
            else:
                db.add(r)

        # 9. Update evaluation status
        if error_count == total:
            evaluation.status = "failed"
        else:
            evaluation.status = "completed"
        await db.commit()

    except Exception:
        logger.exception("Unhandled error in RAG evaluation %s", evaluation_id)
        try:
            eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
            evaluation = eval_result.scalar_one_or_none()
            if evaluation:
                evaluation.status = "failed"
                await db.commit()
        except Exception:
            logger.exception("Failed to update evaluation %s status to failed", evaluation_id)
