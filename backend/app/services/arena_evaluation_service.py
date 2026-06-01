"""Arena evaluation service — runs the same dataset against multiple contestant models."""

import asyncio

import litellm
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JudgeConfigParams, Score
from app.adapters.factory import create_evaluation_adapter
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation, JudgeConfig
from app.models.result import Result
from app.services.provider_utils import proxy_env, resolve_judge_config, resolve_model_config
from app.websocket.progress import broadcast_progress

logger = structlog.get_logger()


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


async def run_arena_evaluation(evaluation_id: str, db: AsyncSession) -> None:
    """Orchestrate an arena evaluation run across multiple contestant models."""
    try:
        # 1. Load evaluation
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
        evaluation = eval_result.scalar_one_or_none()
        if not evaluation:
            logger.error("arena.not_found", evaluation_id=evaluation_id)
            return
        if evaluation.status != "pending":
            logger.warning("arena.skipped", evaluation_id=evaluation_id, status=evaluation.status)
            return

        # 2. Update status to running
        evaluation.status = "running"
        await db.commit()

        # 3. Load dataset
        if not evaluation.dataset_id:
            logger.error("arena.no_dataset", evaluation_id=evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        dataset_result = await db.execute(select(Dataset).where(Dataset.id == evaluation.dataset_id))
        dataset = dataset_result.scalar_one_or_none()
        if not dataset:
            logger.error("arena.dataset_not_found", dataset_id=evaluation.dataset_id, evaluation_id=evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        # 4. Validate contestants
        config = evaluation.config or {}
        contestants = config.get("contestants", [])

        if not contestants or len(contestants) < 2:
            logger.error(
                "arena.insufficient_contestants",
                evaluation_id=evaluation_id,
                count=len(contestants),
            )
            evaluation.status = "failed"
            await db.commit()
            return

        # 5. Load judge config
        judge_config = None
        if evaluation.judge_config_id:
            jc_result = await db.execute(select(JudgeConfig).where(JudgeConfig.id == evaluation.judge_config_id))
            judge_config = jc_result.scalar_one_or_none()
            if not judge_config:
                logger.error(
                    "arena.judge_config_not_found",
                    judge_config_id=evaluation.judge_config_id,
                    evaluation_id=evaluation_id,
                )
                evaluation.status = "failed"
                await db.commit()
                return

        judge_params = _to_judge_params(judge_config)

        # 6. Resolve judge model
        try:
            judge_resolved = resolve_judge_config(config, judge_params)
        except ValueError:
            logger.error("arena.no_judge_model", evaluation_id=evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        logger.info(
            "arena.judge_resolved",
            model=judge_resolved.model,
            api_base=judge_resolved.api_base,
            has_key=bool(judge_resolved.api_key),
        )

        adapter = create_evaluation_adapter(
            model=judge_resolved.model,
            api_key=judge_resolved.api_key,
            api_base=judge_resolved.api_base,
            max_concurrency=config.get("max_concurrency", 10),
        )

        # 7. Resolve contestant model configs
        resolved_contestants = []
        for contestant in contestants:
            try:
                resolved = resolve_model_config(contestant)
                resolved_contestants.append((contestant.get("litellm_model") or resolved.model, resolved))
            except ValueError as e:
                logger.error(
                    "arena.contestant_resolve_failed",
                    contestant=contestant,
                    error=str(e),
                )
                # Mark this contestant as unresolvable — we'll skip it
                continue

        if len(resolved_contestants) < 2:
            logger.error(
                "arena.insufficient_resolved_contestants",
                evaluation_id=evaluation_id,
                count=len(resolved_contestants),
            )
            evaluation.status = "failed"
            await db.commit()
            return

        # 8. Process each contestant x each dataset item
        items = sorted(dataset.items, key=lambda i: i.order_index)
        total = len(resolved_contestants) * len(items)
        completed_counter = 0
        counter_lock = asyncio.Lock()
        max_concurrency = config.get("max_concurrency", 10)
        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_contestant_item(
            contestant_name: str,
            resolved_model,
            item: DatasetItem,
        ) -> Result:
            nonlocal completed_counter

            # Call the contestant model
            litellm_kwargs: dict = {
                "model": resolved_model.model,
                "messages": [{"role": "user", "content": item.question}],
            }
            if resolved_model.api_key:
                litellm_kwargs["api_key"] = resolved_model.api_key
            if resolved_model.api_base:
                litellm_kwargs["api_base"] = resolved_model.api_base

            with proxy_env(resolved_model.proxy):
                response = await litellm.acompletion(**litellm_kwargs)
            actual_answer = response.choices[0].message.content or ""

            # Score via judge adapter
            score: Score = await adapter.evaluate_qa(
                question=item.question,
                expected_answer=item.expected_answer or "",
                actual_answer=actual_answer,
                judge_config=judge_params,
            )

            result = Result(
                evaluation_id=evaluation_id,
                dataset_item_id=item.id,
                contestant_model=contestant_name,
                score=score.value,
                passed=score.passed,
                actual_answer=actual_answer,
                judge_reasoning=score.reasoning,
                scores_breakdown=score.breakdown,
            )

            # Broadcast progress
            async with counter_lock:
                completed_counter += 1
                current_completed = completed_counter
            await broadcast_progress(
                evaluation_id=evaluation_id,
                completed=current_completed,
                total=total,
                current_item=item.question[:100],
                contestant_model=contestant_name,
            )

            return result

        async def bounded_process(
            contestant_name: str,
            resolved_model,
            item: DatasetItem,
        ) -> Result | Exception:
            async with semaphore:
                return await process_contestant_item(contestant_name, resolved_model, item)

        # Build tasks: all contestants x all items
        tasks = []
        task_meta = []  # Track (contestant_name, item_index) for error reporting
        for contestant_name, resolved_model in resolved_contestants:
            for idx, item in enumerate(items):
                tasks.append(bounded_process(contestant_name, resolved_model, item))
                task_meta.append((contestant_name, idx))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 9. Collect results into the session
        contestants_with_errors: set[str] = set()
        contestants_with_success: set[str] = set()

        for i, r in enumerate(results):
            contestant_name, item_idx = task_meta[i]
            if isinstance(r, Exception):
                contestants_with_errors.add(contestant_name)
                logger.error(
                    "arena.item_error",
                    contestant=contestant_name,
                    item_index=item_idx,
                    evaluation_id=evaluation_id,
                    error=str(r),
                )
                error_result = Result(
                    evaluation_id=evaluation_id,
                    dataset_item_id=items[item_idx].id if item_idx < len(items) else None,
                    contestant_model=contestant_name,
                    score=None,
                    passed=False,
                    actual_answer=None,
                    judge_reasoning=str(r),
                )
                db.add(error_result)
            else:
                contestants_with_success.add(contestant_name)
                db.add(r)

        # 10. Update evaluation status
        # "completed" if any contestant succeeded, "failed" only if ALL failed
        if contestants_with_success:
            evaluation.status = "completed"
        else:
            evaluation.status = "failed"
        await db.commit()

        logger.info(
            "arena.completed",
            evaluation_id=evaluation_id,
            status=evaluation.status,
            successful_contestants=list(contestants_with_success),
            failed_contestants=list(contestants_with_errors - contestants_with_success),
        )

    except Exception:
        logger.exception("arena.unhandled_error", evaluation_id=evaluation_id)
        try:
            eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
            evaluation = eval_result.scalar_one_or_none()
            if evaluation:
                evaluation.status = "failed"
                await db.commit()
        except Exception:
            logger.exception("arena.status_update_failed", evaluation_id=evaluation_id)
