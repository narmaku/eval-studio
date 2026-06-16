"""RAG evaluation service.

Orchestrates end-to-end RAG evaluation runs: instantiates a pluggable RAG
backend adapter (HTTP, pgvector, etc.) via the adapter factory, retrieves
answer + context chunks, and scores them with the LiteLLM judge adapter.
"""

import asyncio
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import Score
from app.adapters.factory import create_evaluation_adapter
from app.core.config import settings
from app.core.exceptions import sanitize_error_for_client
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation, JudgeConfig
from app.models.result import Result
from app.rag_backends.base import RAGBackendAdapter
from app.rag_backends.factory import create_rag_adapter
from app.services.artifact_generation import generate_evaluation_artifacts
from app.services.judge_utils import to_judge_params
from app.services.provider_utils import merge_llm_params, resolve_judge_config
from app.websocket.progress import broadcast_log, broadcast_progress, broadcast_status

logger = structlog.get_logger()


def _build_rag_adapter_config(rag_endpoint: dict[str, Any]) -> dict[str, Any]:
    """Build a config dict suitable for create_rag_adapter from the evaluation's rag_endpoint."""
    # Default to HTTP backend if no explicit backend_type is set
    adapter_config: dict[str, Any] = {
        "backend_type": rag_endpoint.get("backend_type", "http"),
    }

    # Pass through all keys from rag_endpoint to the adapter config
    for key in (
        "url",
        "endpoint_url",
        "auth_header",
        "query_field",
        "answer_field",
        "chunks_field",
        "connection_string",
        "table_name",
        "embedding_column",
        "content_column",
        "top_k",
        "generator_model",
        "generator_api_key",
        "generator_api_base",
    ):
        if key in rag_endpoint:
            adapter_config[key] = rag_endpoint[key]

    # Normalize: if frontend sent endpoint_url but not url, map it for the adapter
    if "url" not in adapter_config and "endpoint_url" in adapter_config:
        adapter_config["url"] = adapter_config.pop("endpoint_url")

    return adapter_config


async def run_rag_evaluation(evaluation_id: str, db: AsyncSession) -> None:
    """Orchestrate a full RAG evaluation run."""
    rag_adapter: RAGBackendAdapter | None = None
    try:
        # 1. Load evaluation
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
        evaluation = eval_result.scalar_one_or_none()
        if not evaluation:
            logger.error("evaluation.not_found", evaluation_id=evaluation_id)
            return
        if evaluation.status != "pending":
            logger.warning("evaluation.skipped", evaluation_id=evaluation_id, status=evaluation.status)
            return

        # 2. Update status to running
        evaluation.status = "running"
        await db.commit()

        # 3. Load dataset
        if not evaluation.dataset_id:
            logger.error("evaluation.no_dataset", evaluation_id=evaluation_id)
            evaluation.status = "failed"
            evaluation.error = "Dataset not configured"
            await db.commit()
            await broadcast_status(evaluation_id, "failed", error=evaluation.error)
            return

        dataset_result = await db.execute(select(Dataset).where(Dataset.id == evaluation.dataset_id))
        dataset = dataset_result.scalar_one_or_none()
        if not dataset:
            logger.error("dataset.not_found", dataset_id=evaluation.dataset_id, evaluation_id=evaluation_id)
            evaluation.status = "failed"
            evaluation.error = f"Dataset '{evaluation.dataset_id}' not found"
            await db.commit()
            await broadcast_status(evaluation_id, "failed", error=evaluation.error)
            return

        # 4. Load judge config
        judge_config = None
        if evaluation.judge_config_id:
            jc_result = await db.execute(select(JudgeConfig).where(JudgeConfig.id == evaluation.judge_config_id))
            judge_config = jc_result.scalar_one_or_none()
            if not judge_config:
                logger.error(
                    "judge_config.not_found",
                    judge_config_id=evaluation.judge_config_id,
                    evaluation_id=evaluation_id,
                )
                evaluation.status = "failed"
                evaluation.error = "Judge configuration not found"
                await db.commit()
                await broadcast_status(evaluation_id, "failed", error=evaluation.error)
                return

        judge_params = to_judge_params(judge_config)

        # 5. Validate RAG endpoint config and create adapter
        config = evaluation.config or {}
        rag_endpoint = config.get("rag_endpoint", {})
        rag_url = rag_endpoint.get("url") or rag_endpoint.get("endpoint_url")

        # For HTTP backend (default), URL is required
        backend_type = rag_endpoint.get("backend_type", "http")
        if backend_type == "http" and not rag_url:
            logger.error("rag_evaluation.no_endpoint_url", evaluation_id=evaluation_id)
            evaluation.status = "failed"
            evaluation.error = "RAG endpoint URL not configured"
            await db.commit()
            await broadcast_status(evaluation_id, "failed", error=evaluation.error)
            return

        rag_adapter_config = _build_rag_adapter_config(rag_endpoint)
        rag_adapter = create_rag_adapter(rag_adapter_config)

        rag_metrics = rag_endpoint.get("metrics", ["faithfulness", "relevancy"])

        # 6. Resolve judge model (same pattern as QA service)
        try:
            judge_resolved = resolve_judge_config(config, judge_params)
        except ValueError:
            logger.error("rag_evaluation.no_judge_model", evaluation_id=evaluation_id)
            evaluation.status = "failed"
            evaluation.error = "Judge model resolution failed"
            await db.commit()
            await broadcast_status(evaluation_id, "failed", error=evaluation.error)
            return

        # Merge judge LLM params: judge provider defaults < eval-level judge_params
        judge_llm_params = merge_llm_params(judge_resolved.default_params, config.get("judge_params"))

        logger.info(
            "rag_evaluation.judge_resolved",
            model=judge_resolved.model,
            api_base=judge_resolved.api_base,
            has_key=bool(judge_resolved.api_key),
        )
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Judge model: {judge_resolved.model}",
            details={"model": judge_resolved.model, "api_base": judge_resolved.api_base},
        )

        adapter = create_evaluation_adapter(
            model=judge_resolved.model,
            api_key=judge_resolved.api_key,
            api_base=judge_resolved.api_base,
            max_concurrency=config.get("max_concurrency", 10),
            extra_params=judge_llm_params if judge_llm_params else None,
        )

        # 7. Process each dataset item
        items = sorted(dataset.items, key=lambda i: i.order_index)
        total = len(items)
        completed_counter = 0
        counter_lock = asyncio.Lock()

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Starting evaluation: {evaluation.name} (rag), {total} items",
        )

        async def process_item(idx: int, item: DatasetItem) -> Result:
            nonlocal completed_counter

            await broadcast_log(
                evaluation_id=evaluation_id,
                level="info",
                message=f"Processing item {idx + 1}/{total}: {item.question[:80]}",
            )

            # Step A: Call the RAG backend via adapter
            rag_response = await rag_adapter.retrieve_and_generate(item.question)

            # Step B: Extract answer and chunks from adapter response
            actual_answer = rag_response.answer
            chunks = rag_response.chunks
            chunk_contents = [c.get("content", "") for c in chunks]

            await broadcast_log(
                evaluation_id=evaluation_id,
                level="info",
                message=f"Model response received ({len(actual_answer)} chars)",
                details={"chunks_retrieved": len(chunks)},
            )

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
                    judge_config=judge_params,
                )
                # Compute overall score as average of metric scores
                if metric_scores:
                    scores_breakdown = {k: v.value for k, v in metric_scores.items()}
                    score_value = sum(v.value for v in metric_scores.values()) / len(metric_scores)
                    threshold = judge_params.pass_threshold or 0.7
                    passed = score_value >= threshold
                    reasoning_parts = [f"{k}: {v.reasoning}" for k, v in metric_scores.items() if v.reasoning]
                    reasoning = "\n\n".join(reasoning_parts) if reasoning_parts else None
            except NotImplementedError:
                logger.warning(
                    "rag_evaluation.scoring_not_implemented",
                    evaluation_id=evaluation_id,
                )
                # Leave score/breakdown as None -- we still store the answer + chunks

            if score_value is not None:
                passed_label = "PASS" if passed else "FAIL"
                reasoning_preview = (reasoning or "")[:100]
                await broadcast_log(
                    evaluation_id=evaluation_id,
                    level="info",
                    message=f"Score: {score_value:.2f} ({passed_label}) — {reasoning_preview}",
                )

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

        async def bounded_process(idx: int, item: DatasetItem) -> Result | Exception:
            async with semaphore:
                return await process_item(idx, item)

        results = await asyncio.gather(
            *[bounded_process(i, item) for i, item in enumerate(items)],
            return_exceptions=True,
        )

        # 8. Collect results into the session sequentially
        error_count = 0
        passed_count = 0
        total_score = 0.0
        scored_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                error_count += 1
                logger.error("rag_evaluation.item_error", item_index=i, evaluation_id=evaluation_id, error=str(r))
                await broadcast_log(
                    evaluation_id=evaluation_id,
                    level="error",
                    message=f"Error on item {i + 1}: {sanitize_error_for_client(r)}",
                )
                error_result = Result(
                    evaluation_id=evaluation_id,
                    dataset_item_id=items[i].id if i < len(items) else None,
                    score=None,
                    passed=False,
                    actual_answer=None,
                    judge_reasoning=sanitize_error_for_client(r),
                )
                db.add(error_result)
            else:
                db.add(r)
                if r.passed:
                    passed_count += 1
                if r.score is not None:
                    total_score += r.score
                    scored_count += 1

        # 9. Update evaluation status
        if error_count == total:
            evaluation.status = "failed"
            evaluation.error = f"All {total} items failed"
        else:
            evaluation.status = "completed"
        await db.commit()
        await broadcast_status(evaluation_id, evaluation.status, error=evaluation.error)

        avg_score = total_score / scored_count if scored_count > 0 else 0.0
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Evaluation completed: {passed_count}/{total} passed, avg score: {avg_score:.2f}",
        )

        # Generate downloadable artifacts (errors are caught internally)
        await generate_evaluation_artifacts(evaluation_id, db, settings.artifacts_dir)

    except Exception as exc:
        logger.exception("rag_evaluation.unhandled_error", evaluation_id=evaluation_id)
        try:
            eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
            evaluation = eval_result.scalar_one_or_none()
            if evaluation:
                evaluation.status = "failed"
                evaluation.error = sanitize_error_for_client(exc)
                await db.commit()
                await broadcast_status(evaluation_id, "failed", error=evaluation.error)
        except Exception:
            logger.exception("rag_evaluation.status_update_failed", evaluation_id=evaluation_id)
    finally:
        if rag_adapter is not None:
            await rag_adapter.close()
