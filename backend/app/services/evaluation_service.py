import asyncio
import logging

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import JudgeConfigParams, Score
from app.adapters.litellm_judge import LiteLLMJudgeAdapter
from app.core.config import settings
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


async def run_qa_evaluation(evaluation_id: str, db: AsyncSession) -> None:
    """Orchestrate a full Q&A evaluation run."""
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
            jc_result = await db.execute(
                select(JudgeConfig).where(JudgeConfig.id == evaluation.judge_config_id)
            )
            judge_config = jc_result.scalar_one_or_none()
            if not judge_config:
                logger.error("JudgeConfig %s not found for evaluation %s", evaluation.judge_config_id, evaluation_id)
                evaluation.status = "failed"
                await db.commit()
                return

        judge_params = _to_judge_params(judge_config)

        # 5. Determine the model under test
        config = evaluation.config or {}
        model_under_test = config.get("model", settings.litellm_model)

        # 6. Instantiate the adapter
        adapter = LiteLLMJudgeAdapter(
            model=judge_params.model,
            api_key=settings.litellm_api_key,
            max_concurrency=config.get("max_concurrency", 10),
        )

        # 7. Process each dataset item
        items = sorted(dataset.items, key=lambda i: i.order_index)
        total = len(items)

        async def process_item(idx: int, item: DatasetItem) -> Result:
            # Step A: Call the model under test
            response = await litellm.acompletion(
                model=model_under_test,
                messages=[{"role": "user", "content": item.question}],
                api_key=settings.litellm_api_key,
            )
            actual_answer = response.choices[0].message.content or ""

            # Step B: Score the response using the judge
            score: Score = await adapter.evaluate_qa(
                question=item.question,
                expected_answer=item.expected_answer or "",
                actual_answer=actual_answer,
                judge_config=judge_params,
            )

            # Step C: Create Result record
            result = Result(
                evaluation_id=evaluation_id,
                dataset_item_id=item.id,
                score=score.value,
                passed=score.passed,
                actual_answer=actual_answer,
                judge_reasoning=score.reasoning,
                scores_breakdown=score.breakdown,
            )
            db.add(result)

            # Step D: Broadcast progress
            await broadcast_progress(
                evaluation_id=evaluation_id,
                completed=idx + 1,
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

        # 8. Handle per-item errors
        error_count = 0
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                error_count += 1
                logger.error("Error processing item %d for evaluation %s: %s", i, evaluation_id, r)
                error_result = Result(
                    evaluation_id=evaluation_id,
                    dataset_item_id=items[i].id if i < len(items) else None,
                    score=None,
                    passed=False,
                    actual_answer=None,
                    judge_reasoning=str(r),
                )
                db.add(error_result)

        # 9. Update evaluation status
        if error_count == total:
            evaluation.status = "failed"
        else:
            evaluation.status = "completed"
        await db.commit()

    except Exception:
        logger.exception("Unhandled error in evaluation %s", evaluation_id)
        try:
            eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
            evaluation = eval_result.scalar_one_or_none()
            if evaluation:
                evaluation.status = "failed"
                await db.commit()
        except Exception:
            logger.exception("Failed to update evaluation %s status to failed", evaluation_id)
