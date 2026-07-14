"""Consolidated evaluation runner.

Replaces the three copy-pasted orchestration skeletons
(evaluation_service, arena_evaluation_service, rag_evaluation_service)
with one shared lifecycle and pluggable per-mode runners.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import EvaluationAdapter, JudgeConfigParams, Score
from app.adapters.factory import create_adapter_from_config
from app.core.config import settings
from app.core.exceptions import sanitize_error_for_client
from app.core.rate_limiter import AsyncRateLimiter
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.models.rubric import Rubric
from app.rag_backends.factory import create_rag_adapter
from app.schemas.evaluation import EvaluationStatus
from app.services.artifact_generation import generate_evaluation_artifacts
from app.services.judge_utils import to_judge_params
from app.services.provider_utils import (
    ResolvedModel,
    call_model,
    merge_llm_params,
    resolve_judge_config,
    resolve_model_config,
)
from app.websocket.progress import broadcast_log, broadcast_progress, broadcast_status

logger = structlog.get_logger()


@dataclass
class TaskSpec:
    """A single unit of work for the evaluation fan-out."""

    item: DatasetItem
    index: int
    contestant_name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ItemOutcome:
    """Result of processing one TaskSpec."""

    actual_answer: str | None = None
    score: float | None = None
    passed: bool | None = None
    reasoning: str | None = None
    scores_breakdown: dict[str, float] | None = None
    retrieved_chunks: list[dict] | None = None
    contestant_model: str | None = None


@runtime_checkable
class ModeRunner(Protocol):
    async def prepare(self, evaluation: Evaluation, config: dict, evaluation_id: str) -> None: ...
    def tasks(self, items: list[DatasetItem]) -> list[TaskSpec]: ...
    async def run_item(
        self, spec: TaskSpec, adapter: EvaluationAdapter, judge_params: JudgeConfigParams, evaluation_id: str
    ) -> ItemOutcome: ...
    async def cleanup(self) -> None: ...


async def _fail(evaluation: Evaluation, db: AsyncSession, detail: str) -> None:
    evaluation.status = EvaluationStatus.FAILED
    evaluation.error = detail
    await db.commit()
    await broadcast_status(evaluation.id, EvaluationStatus.FAILED, error=detail)


async def run_evaluation(evaluation_id: str, db: AsyncSession) -> None:
    """Single orchestrator for Q&A, Arena, and RAG evaluation modes."""
    runner: ModeRunner | None = None
    try:
        # 1. Atomically claim: pending → running (compare-and-set)
        cas = await db.execute(
            update(Evaluation)
            .where(Evaluation.id == evaluation_id, Evaluation.status == EvaluationStatus.PENDING)
            .values(status=EvaluationStatus.RUNNING)
        )
        await db.commit()
        if cas.rowcount == 0:
            logger.warning("evaluation.already_claimed", evaluation_id=evaluation_id)
            return

        # 2. Load the now-running evaluation
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
        evaluation = eval_result.scalar_one_or_none()
        if not evaluation:
            logger.error("evaluation.not_found", evaluation_id=evaluation_id)
            return

        # 3. Resolve mode runner
        runner_cls = MODE_RUNNERS.get(evaluation.mode)
        if not runner_cls:
            await _fail(evaluation, db, f"Unknown evaluation mode: {evaluation.mode}")
            return
        runner = runner_cls()

        # 4. Load dataset
        if not evaluation.dataset_id:
            await _fail(evaluation, db, "Dataset not configured")
            return

        dataset_result = await db.execute(select(Dataset).where(Dataset.id == evaluation.dataset_id))
        dataset = dataset_result.scalar_one_or_none()
        if not dataset:
            await _fail(evaluation, db, f"Dataset '{evaluation.dataset_id}' not found")
            return

        # 5. Load rubric
        config = evaluation.config or {}
        rubric = None
        if evaluation.rubric_id:
            rubric_result = await db.execute(select(Rubric).where(Rubric.id == evaluation.rubric_id))
            rubric = rubric_result.scalar_one_or_none()

        judge_params = to_judge_params(rubric)

        # 6. Mode-specific preparation
        try:
            await runner.prepare(evaluation, config, evaluation_id)
        except ValueError as e:
            await _fail(evaluation, db, str(e))
            return

        # 7. Resolve judge model + create adapter
        try:
            judge_resolved = resolve_judge_config(config, judge_params)
        except ValueError:
            await _fail(evaluation, db, "Judge model resolution failed")
            return

        judge_llm_params = merge_llm_params(judge_resolved.default_params, config.get("judge_params"))

        logger.info(
            "evaluation.judge_resolved",
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

        try:
            adapter = create_adapter_from_config(config, judge_resolved, judge_llm_params)
        except ValueError as e:
            await _fail(evaluation, db, str(e))
            return

        # 8. Build task specs and fan out
        items = sorted(dataset.items, key=lambda i: i.order_index)

        # Optional: filter to specific dataset items (used by clone-and-rerun failures_only)
        dataset_item_ids = config.get("dataset_item_ids")
        if dataset_item_ids:
            allowed_ids = set(dataset_item_ids)
            items = [item for item in items if item.id in allowed_ids]
            if not items:
                await _fail(evaluation, db, "No matching dataset items found for the provided dataset_item_ids filter.")
                return

        task_specs = runner.tasks(items)
        total = len(task_specs)

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Starting evaluation: {evaluation.name} ({evaluation.mode}), {total} items",
        )

        completed_counter = 0
        counter_lock = asyncio.Lock()
        max_concurrency = config.get("max_concurrency", 10)
        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_task(spec: TaskSpec) -> Result:
            nonlocal completed_counter

            outcome = await runner.run_item(spec, adapter, judge_params, evaluation_id)

            result = Result(
                evaluation_id=evaluation_id,
                dataset_item_id=spec.item.id,
                score=outcome.score,
                passed=outcome.passed,
                actual_answer=outcome.actual_answer,
                judge_reasoning=outcome.reasoning,
                scores_breakdown=outcome.scores_breakdown,
                retrieved_chunks=outcome.retrieved_chunks,
                contestant_model=outcome.contestant_model,
            )

            async with counter_lock:
                completed_counter += 1
                current_completed = completed_counter
            await broadcast_progress(
                evaluation_id=evaluation_id,
                completed=current_completed,
                total=total,
                current_item=spec.item.question[:100],
                **({"contestant_model": spec.contestant_name} if spec.contestant_name else {}),
            )

            return result

        async def bounded_process(spec: TaskSpec) -> Result | Exception:
            async with semaphore:
                return await process_task(spec)

        results = await asyncio.gather(
            *[bounded_process(spec) for spec in task_specs],
            return_exceptions=True,
        )

        # 9. Collect results
        error_count = 0
        passed_count = 0
        total_score = 0.0
        scored_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                error_count += 1
                spec = task_specs[i]
                logger.error(
                    "evaluation.item_error",
                    item_index=spec.index,
                    evaluation_id=evaluation_id,
                    error=str(r),
                    **({"contestant": spec.contestant_name} if spec.contestant_name else {}),
                )
                await broadcast_log(
                    evaluation_id=evaluation_id,
                    level="error",
                    message=f"Error on item {spec.index + 1}: {sanitize_error_for_client(r)}",
                    **({"details": {"contestant_model": spec.contestant_name}} if spec.contestant_name else {}),
                )
                error_result = Result(
                    evaluation_id=evaluation_id,
                    dataset_item_id=spec.item.id,
                    contestant_model=spec.contestant_name,
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

        # 10. Final status
        if error_count == total:
            evaluation.status = EvaluationStatus.FAILED
            evaluation.error = f"All {total} items failed"
        else:
            evaluation.status = EvaluationStatus.COMPLETED
        await db.commit()
        await broadcast_status(evaluation_id, evaluation.status, error=evaluation.error)

        avg_score = total_score / scored_count if scored_count > 0 else 0.0
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Evaluation completed: {passed_count}/{total} passed, avg score: {avg_score:.2f}",
        )

        await generate_evaluation_artifacts(evaluation_id, db, settings.artifacts_dir)

    except Exception as exc:
        logger.exception("evaluation.unhandled_error", evaluation_id=evaluation_id)
        try:
            eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
            evaluation = eval_result.scalar_one_or_none()
            if evaluation:
                evaluation.status = EvaluationStatus.FAILED
                evaluation.error = sanitize_error_for_client(exc)
                await db.commit()
                await broadcast_status(evaluation_id, EvaluationStatus.FAILED, error=evaluation.error)
        except Exception:
            logger.exception("evaluation.status_update_failed", evaluation_id=evaluation_id)
    finally:
        if runner is not None:
            await runner.cleanup()


# ---------------------------------------------------------------------------
# Mode runners
# ---------------------------------------------------------------------------


class QARunner:
    """Runs Q&A benchmark items: call model under test, then judge."""

    def __init__(self) -> None:
        self._resolved: ResolvedModel | None = None
        self._model_params: dict | None = None
        self._rate_limiter: AsyncRateLimiter | None = None
        self._model_name: str = "custom"

    async def prepare(self, evaluation: Evaluation, config: dict, evaluation_id: str) -> None:
        model_endpoint = config.get("model_endpoint", {})
        resolution_config = dict(model_endpoint)
        if "default_model" not in resolution_config and "model" not in resolution_config:
            top_level_model = config.get("model")
            if top_level_model:
                resolution_config["model"] = top_level_model

        try:
            self._resolved = resolve_model_config(resolution_config)
        except ValueError as e:
            raise ValueError("Model resolution failed") from e

        self._model_name = self._resolved.model or self._resolved.endpoint_url or "custom"
        self._model_params = merge_llm_params(self._resolved.default_params, config.get("model_params"))

        logger.info(
            "evaluation.model_resolved",
            model=self._model_name,
            api_base=self._resolved.api_base,
            has_key=bool(self._resolved.api_key),
            provider=model_endpoint.get("provider_id") or "none",
            provider_type=self._resolved.provider_type,
        )
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Model resolved: {self._model_name}",
            details={"model": self._model_name, "api_base": self._resolved.api_base},
        )

        if self._resolved.rate_limited and self._resolved.rate_limits:
            self._rate_limiter = AsyncRateLimiter(self._resolved.rate_limits)
            logger.info(
                "evaluation.rate_limiter_enabled",
                evaluation_id=evaluation_id,
                rules=len(self._resolved.rate_limits),
            )
            await broadcast_log(
                evaluation_id=evaluation_id,
                level="info",
                message=f"Rate limiting enabled: {len(self._resolved.rate_limits)} rule(s)",
            )

    def tasks(self, items: list[DatasetItem]) -> list[TaskSpec]:
        return [TaskSpec(item=item, index=i) for i, item in enumerate(items)]

    async def run_item(
        self, spec: TaskSpec, adapter: EvaluationAdapter, judge_params: JudgeConfigParams, evaluation_id: str
    ) -> ItemOutcome:
        assert self._resolved is not None

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Processing item {spec.index + 1}: {spec.item.question[:80]}",
        )

        if self._rate_limiter:
            await self._rate_limiter.acquire()
        actual_answer = await call_model(self._resolved, spec.item.question, extra_params=self._model_params)

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Model response received ({len(actual_answer)} chars)",
            details={"model": self._model_name},
        )

        score: Score = await adapter.evaluate_qa(
            question=spec.item.question,
            expected_answer=spec.item.expected_answer or "",
            actual_answer=actual_answer,
            judge_config=judge_params,
        )

        passed_label = "PASS" if score.passed else "FAIL"
        reasoning_preview = (score.reasoning or "")[:100]
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Score: {score.value:.2f} ({passed_label}) — {reasoning_preview}",
        )

        return ItemOutcome(
            actual_answer=actual_answer,
            score=score.value,
            passed=score.passed,
            reasoning=score.reasoning,
            scores_breakdown=score.breakdown,
        )

    async def cleanup(self) -> None:
        pass


class ArenaRunner:
    """Runs arena items: each contestant model x each dataset item."""

    def __init__(self) -> None:
        self._resolved_contestants: list[tuple[str, ResolvedModel, dict]] = []

    async def prepare(self, evaluation: Evaluation, config: dict, evaluation_id: str) -> None:
        contestants = config.get("contestants", [])
        if not contestants or len(contestants) < 2:
            raise ValueError(f"At least 2 contestants required, got {len(contestants)}")

        eval_model_params = config.get("model_params")

        for contestant in contestants:
            try:
                resolved = resolve_model_config(contestant)
                contestant_params = merge_llm_params(resolved.default_params, eval_model_params)
                contestant_name = contestant.get("default_model") or resolved.model or resolved.endpoint_url or "custom"
                self._resolved_contestants.append((contestant_name, resolved, contestant_params))
            except ValueError as e:
                logger.error("arena.contestant_resolve_failed", contestant=contestant, error=str(e))
                continue

        if len(self._resolved_contestants) < 2:
            raise ValueError(
                f"Not enough contestants could be resolved ({len(self._resolved_contestants)} of {len(contestants)})"
            )

        contestant_names = [name for name, _, _ in self._resolved_contestants]
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=(f"Starting evaluation: {evaluation.name} (arena), models: {', '.join(contestant_names)}"),
        )
        for contestant_name, resolved_model, _ in self._resolved_contestants:
            await broadcast_log(
                evaluation_id=evaluation_id,
                level="info",
                message=f"Model resolved: {contestant_name}",
                details={"model": resolved_model.model, "api_base": resolved_model.api_base},
            )

    def tasks(self, items: list[DatasetItem]) -> list[TaskSpec]:
        specs = []
        for contestant_name, resolved_model, contestant_params in self._resolved_contestants:
            for idx, item in enumerate(items):
                specs.append(
                    TaskSpec(
                        item=item,
                        index=idx,
                        contestant_name=contestant_name,
                        extra={
                            "resolved_model": resolved_model,
                            "contestant_params": contestant_params,
                        },
                    )
                )
        return specs

    async def run_item(
        self, spec: TaskSpec, adapter: EvaluationAdapter, judge_params: JudgeConfigParams, evaluation_id: str
    ) -> ItemOutcome:
        resolved_model: ResolvedModel = spec.extra["resolved_model"]
        contestant_params: dict = spec.extra["contestant_params"]

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Processing: {spec.item.question[:80]}",
            details={"contestant_model": spec.contestant_name},
        )

        actual_answer = await call_model(resolved_model, spec.item.question, extra_params=contestant_params)

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Model response received ({len(actual_answer)} chars)",
            details={"contestant_model": spec.contestant_name},
        )

        score: Score = await adapter.evaluate_qa(
            question=spec.item.question,
            expected_answer=spec.item.expected_answer or "",
            actual_answer=actual_answer,
            judge_config=judge_params,
        )

        passed_label = "PASS" if score.passed else "FAIL"
        reasoning_preview = (score.reasoning or "")[:100]
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Score: {score.value:.2f} ({passed_label}) — {reasoning_preview}",
            details={"contestant_model": spec.contestant_name},
        )

        return ItemOutcome(
            actual_answer=actual_answer,
            score=score.value,
            passed=score.passed,
            reasoning=score.reasoning,
            scores_breakdown=score.breakdown,
            contestant_model=spec.contestant_name,
        )

    async def cleanup(self) -> None:
        pass


def _build_rag_adapter_config(rag_endpoint: dict[str, Any]) -> dict[str, Any]:
    """Build a config dict suitable for create_rag_adapter from the evaluation's rag_endpoint.

    Resolves env-var indirection: ``auth_token_env`` -> ``auth_header`` dict,
    ``generator_api_key_env`` -> ``generator_api_key`` value.
    """
    adapter_config: dict[str, Any] = {
        "backend_type": rag_endpoint.get("backend_type", "http"),
    }

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

    if "auth_token_env" in rag_endpoint:
        env_name = rag_endpoint["auth_token_env"]
        token = os.environ.get(env_name, "")
        if token:
            adapter_config["auth_header"] = {"Authorization": f"Bearer {token}"}
        else:
            logger.warning("rag.auth_token_env_missing", env_var=env_name)

    if "generator_api_key_env" in rag_endpoint:
        env_name = rag_endpoint["generator_api_key_env"]
        api_key = os.environ.get(env_name, "")
        if api_key:
            adapter_config["generator_api_key"] = api_key
        else:
            logger.warning("rag.generator_api_key_env_missing", env_var=env_name)

    if "url" not in adapter_config and "endpoint_url" in adapter_config:
        adapter_config["url"] = adapter_config.pop("endpoint_url")

    return adapter_config


class RAGRunner:
    """Runs RAG evaluation items: retrieve + generate via RAG adapter, then judge."""

    def __init__(self) -> None:
        self._rag_adapter: Any = None

    async def prepare(self, evaluation: Evaluation, config: dict, evaluation_id: str) -> None:
        rag_endpoint = config.get("rag_endpoint", {})
        rag_url = rag_endpoint.get("url") or rag_endpoint.get("endpoint_url")

        backend_type = rag_endpoint.get("backend_type", "http")
        if backend_type == "http" and not rag_url:
            raise ValueError("RAG endpoint URL not configured")

        rag_adapter_config = _build_rag_adapter_config(rag_endpoint)
        self._rag_adapter = create_rag_adapter(rag_adapter_config)
        self._rag_metrics = rag_endpoint.get("metrics", ["faithfulness", "relevancy"])

    def tasks(self, items: list[DatasetItem]) -> list[TaskSpec]:
        return [TaskSpec(item=item, index=i) for i, item in enumerate(items)]

    async def run_item(
        self, spec: TaskSpec, adapter: EvaluationAdapter, judge_params: JudgeConfigParams, evaluation_id: str
    ) -> ItemOutcome:
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Processing item {spec.index + 1}: {spec.item.question[:80]}",
        )

        rag_response = await self._rag_adapter.retrieve_and_generate(spec.item.question)
        actual_answer = rag_response.answer
        chunks = rag_response.chunks
        chunk_contents = [c.get("content", "") for c in chunks]

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Model response received ({len(actual_answer)} chars)",
            details={"chunks_retrieved": len(chunks)},
        )

        score_value: float | None = None
        passed: bool | None = None
        reasoning: str | None = None
        scores_breakdown: dict[str, float] | None = None

        try:
            metric_scores: dict[str, Score] = await adapter.evaluate_rag(
                question=spec.item.question,
                context_chunks=chunk_contents,
                answer=actual_answer,
                expected_answer=spec.item.expected_answer,
                metrics=self._rag_metrics,
                judge_config=judge_params,
            )
            if metric_scores:
                scores_breakdown = {k: v.value for k, v in metric_scores.items()}
                score_value = sum(v.value for v in metric_scores.values()) / len(metric_scores)
                threshold = judge_params.pass_threshold or 0.7
                passed = score_value >= threshold
                reasoning_parts = [f"{k}: {v.reasoning}" for k, v in metric_scores.items() if v.reasoning]
                reasoning = "\n\n".join(reasoning_parts) if reasoning_parts else None
        except NotImplementedError:
            logger.warning("rag_evaluation.scoring_not_implemented", evaluation_id=evaluation_id)

        if score_value is not None:
            passed_label = "PASS" if passed else "FAIL"
            reasoning_preview = (reasoning or "")[:100]
            await broadcast_log(
                evaluation_id=evaluation_id,
                level="info",
                message=f"Score: {score_value:.2f} ({passed_label}) — {reasoning_preview}",
            )

        return ItemOutcome(
            actual_answer=actual_answer,
            score=score_value,
            passed=passed,
            reasoning=reasoning,
            scores_breakdown=scores_breakdown,
            retrieved_chunks=chunks,
        )

    async def cleanup(self) -> None:
        if self._rag_adapter is not None:
            await self._rag_adapter.close()


MODE_RUNNERS: dict[str, type[QARunner] | type[ArenaRunner] | type[RAGRunner]] = {
    "qa": QARunner,
    "arena": ArenaRunner,
    "rag": RAGRunner,
}
