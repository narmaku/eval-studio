import asyncio

import litellm
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JudgeConfigParams, Score
from app.adapters.litellm_judge import LiteLLMJudgeAdapter
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


async def run_qa_evaluation(evaluation_id: str, db: AsyncSession) -> None:
    """Orchestrate a full Q&A evaluation run."""
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
            await db.commit()
            return

        dataset_result = await db.execute(select(Dataset).where(Dataset.id == evaluation.dataset_id))
        dataset = dataset_result.scalar_one_or_none()
        if not dataset:
            logger.error("dataset.not_found", dataset_id=evaluation.dataset_id, evaluation_id=evaluation_id)
            evaluation.status = "failed"
            await db.commit()
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
                await db.commit()
                return

        judge_params = _to_judge_params(judge_config)

        # 5. Determine the model under test (with provider profile support)
        config = evaluation.config or {}
        model_endpoint = config.get("model_endpoint", {})

        # Merge top-level "model" key as fallback for backward compatibility
        resolution_config = dict(model_endpoint)
        if "litellm_model" not in resolution_config and "model" not in resolution_config:
            top_level_model = config.get("model")
            if top_level_model:
                resolution_config["model"] = top_level_model

        try:
            resolved = resolve_model_config(resolution_config)
        except ValueError:
            logger.error("evaluation.no_model", evaluation_id=evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        model_under_test = resolved.model
        model_api_base = resolved.api_base
        model_api_key = resolved.api_key
        model_proxy = resolved.proxy

        logger.info(
            "evaluation.model_resolved",
            model=model_under_test,
            api_base=model_api_base,
            has_key=bool(model_api_key),
            provider=model_endpoint.get("provider_id") or "none",
        )

        # 6. Resolve judge: provider profile > DB judge config > LITELLM_MODEL env
        try:
            judge_resolved = resolve_judge_config(config, judge_params)
        except ValueError:
            logger.error("evaluation.no_judge_model", evaluation_id=evaluation_id)
            evaluation.status = "failed"
            await db.commit()
            return

        logger.info(
            "evaluation.judge_resolved",
            model=judge_resolved.model,
            api_base=judge_resolved.api_base,
            has_key=bool(judge_resolved.api_key),
        )

        adapter = LiteLLMJudgeAdapter(
            model=judge_resolved.model,
            api_key=judge_resolved.api_key,
            api_base=judge_resolved.api_base,
            max_concurrency=config.get("max_concurrency", 10),
        )

        # 7. Process each dataset item
        items = sorted(dataset.items, key=lambda i: i.order_index)
        total = len(items)
        completed_counter = 0
        counter_lock = asyncio.Lock()

        async def process_item(idx: int, item: DatasetItem) -> Result:
            nonlocal completed_counter

            # Step A: Call the model under test (with proxy support)
            litellm_kwargs: dict = {
                "model": model_under_test,
                "messages": [{"role": "user", "content": item.question}],
            }
            if model_api_key:
                litellm_kwargs["api_key"] = model_api_key
            if model_api_base:
                litellm_kwargs["api_base"] = model_api_base
            with proxy_env(model_proxy):
                response = await litellm.acompletion(**litellm_kwargs)
            actual_answer = response.choices[0].message.content or ""

            # Step B: Score the response using the judge
            score: Score = await adapter.evaluate_qa(
                question=item.question,
                expected_answer=item.expected_answer or "",
                actual_answer=actual_answer,
                judge_config=judge_params,
            )

            # Step C: Build Result record (do NOT add to session here;
            # the session is shared and not safe for concurrent mutations)
            result = Result(
                evaluation_id=evaluation_id,
                dataset_item_id=item.id,
                score=score.value,
                passed=score.passed,
                actual_answer=actual_answer,
                judge_reasoning=score.reasoning,
                scores_breakdown=score.breakdown,
            )

            # Step D: Broadcast progress with accurate counter
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

        # 8. Collect results into the session sequentially (session is not
        # safe for concurrent mutations from multiple coroutines).
        error_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                error_count += 1
                logger.error("evaluation.item_error", item_index=i, evaluation_id=evaluation_id, error=str(r))
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
        logger.exception("evaluation.unhandled_error", evaluation_id=evaluation_id)
        try:
            eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
            evaluation = eval_result.scalar_one_or_none()
            if evaluation:
                evaluation.status = "failed"
                await db.commit()
        except Exception:
            logger.exception("evaluation.status_update_failed", evaluation_id=evaluation_id)
