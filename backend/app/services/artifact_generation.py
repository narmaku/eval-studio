"""Shared helper for generating evaluation artifacts.

Produces three downloadable artifacts after an evaluation completes:
- results.json: full results array with scores, answers, reasoning
- summary.md: human-readable markdown report with aggregate metrics
- config.json: frozen evaluation configuration snapshot

Errors are caught and logged — artifact generation never fails the evaluation.
"""

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.result import Result
from app.services.artifact_service import save_artifact
from app.websocket.progress import broadcast_log

logger = structlog.get_logger()


async def generate_evaluation_artifacts(evaluation_id: str, db: AsyncSession, artifacts_dir: str) -> None:
    """Generate downloadable artifacts for a completed evaluation.

    Creates three artifact files: results.json, summary.md, and config.json.
    All errors are caught and logged — this function never raises.

    Args:
        evaluation_id: The ID of the evaluation to generate artifacts for.
        db: The async database session.
        artifacts_dir: The base directory for artifact storage.
    """
    try:
        # Load the evaluation
        eval_result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
        evaluation = eval_result.scalar_one_or_none()
        if not evaluation:
            logger.warning("artifact_generation.evaluation_not_found", evaluation_id=evaluation_id)
            return

        # Load results for this evaluation
        results_query = await db.execute(select(Result).where(Result.evaluation_id == evaluation_id))
        results = results_query.scalars().all()

        # Generate all three artifacts
        await _generate_results_json(evaluation, results, db, artifacts_dir)
        await _generate_summary_md(evaluation, results, db, artifacts_dir)
        await _generate_config_json(evaluation, db, artifacts_dir)

        await broadcast_log(
            evaluation_id=evaluation_id,
            level="info",
            message=f"Artifacts generated: 3 files saved for evaluation '{evaluation.name}'",
        )
        logger.info("artifact_generation.success", evaluation_id=evaluation_id, artifact_count=3)

    except Exception as exc:
        logger.error("artifact_generation.failed", evaluation_id=evaluation_id, error=str(exc))
        await broadcast_log(
            evaluation_id=evaluation_id,
            level="error",
            message=f"Artifact generation failed: {exc}",
        )


def _serialize_result(result: Result) -> dict[str, Any]:
    """Serialize a Result model instance to a JSON-safe dictionary."""
    data: dict[str, Any] = {
        "id": result.id,
        "dataset_item_id": result.dataset_item_id,
        "score": result.score,
        "passed": result.passed,
        "actual_answer": result.actual_answer,
        "judge_reasoning": result.judge_reasoning,
        "scores_breakdown": result.scores_breakdown,
    }
    if result.retrieved_chunks is not None:
        data["retrieved_chunks"] = result.retrieved_chunks
    if result.contestant_model is not None:
        data["contestant_model"] = result.contestant_model
    return data


async def _generate_results_json(
    evaluation: Evaluation, results: list[Result], db: AsyncSession, artifacts_dir: str
) -> None:
    """Generate the results.json artifact with full evaluation results."""
    data = {
        "evaluation_id": evaluation.id,
        "evaluation_name": evaluation.name,
        "mode": evaluation.mode,
        "status": evaluation.status,
        "generated_at": datetime.now(UTC).isoformat(),
        "results": [_serialize_result(r) for r in results],
    }

    content = json.dumps(data, indent=2, default=str).encode("utf-8")
    await save_artifact(
        db=db,
        evaluation_id=evaluation.id,
        filename="results.json",
        content=content,
        content_type="application/json",
        artifacts_dir=artifacts_dir,
        description="Full evaluation results with scores, answers, and reasoning",
    )


async def _generate_summary_md(
    evaluation: Evaluation, results: list[Result], db: AsyncSession, artifacts_dir: str
) -> None:
    """Generate the summary.md artifact with a human-readable report."""
    lines: list[str] = []

    # Header
    lines.append(f"# Evaluation Report: {evaluation.name}")
    lines.append("")
    lines.append(f"- **Mode**: {evaluation.mode}")
    lines.append(f"- **Status**: {evaluation.status}")
    lines.append(f"- **Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # Aggregate metrics
    scored_results = [r for r in results if r.score is not None]
    passed_count = sum(1 for r in results if r.passed)
    failed_count = sum(1 for r in results if not r.passed)
    total_count = len(results)

    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append(f"- **Total Items**: {total_count}")
    lines.append(f"- **Passed**: {passed_count}")
    lines.append(f"- **Failed**: {failed_count}")

    if total_count > 0:
        pass_rate = (passed_count / total_count) * 100
        lines.append(f"- **Pass Rate**: {pass_rate:.1f}%")

    if scored_results:
        scores = [r.score for r in scored_results if r.score is not None]
        mean_score = sum(scores) / len(scores)
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        median_score = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2 if n % 2 == 0 else sorted_scores[n // 2]

        lines.append(f"- **Mean Score**: {mean_score:.3f}")
        lines.append(f"- **Median Score**: {median_score:.3f}")
    lines.append("")

    # Per-item summary table
    lines.append("## Per-Item Results")
    lines.append("")

    has_contestant = any(r.contestant_model for r in results)
    if has_contestant:
        lines.append("| # | Contestant | Score | Passed | Reasoning |")
        lines.append("|---|-----------|-------|--------|-----------|")
        for i, r in enumerate(results, 1):
            score_str = f"{r.score:.2f}" if r.score is not None else "N/A"
            passed_str = "PASS" if r.passed else "FAIL"
            reasoning_preview = (r.judge_reasoning or "")[:80].replace("|", "\\|")
            contestant = r.contestant_model or "N/A"
            lines.append(f"| {i} | {contestant} | {score_str} | {passed_str} | {reasoning_preview} |")
    else:
        lines.append("| # | Score | Passed | Reasoning |")
        lines.append("|---|-------|--------|-----------|")
        for i, r in enumerate(results, 1):
            score_str = f"{r.score:.2f}" if r.score is not None else "N/A"
            passed_str = "PASS" if r.passed else "FAIL"
            reasoning_preview = (r.judge_reasoning or "")[:80].replace("|", "\\|")
            lines.append(f"| {i} | {score_str} | {passed_str} | {reasoning_preview} |")

    lines.append("")

    content = "\n".join(lines).encode("utf-8")
    await save_artifact(
        db=db,
        evaluation_id=evaluation.id,
        filename="summary.md",
        content=content,
        content_type="text/markdown",
        artifacts_dir=artifacts_dir,
        description="Human-readable evaluation summary with aggregate metrics",
    )


async def _generate_config_json(evaluation: Evaluation, db: AsyncSession, artifacts_dir: str) -> None:
    """Generate the config.json artifact with frozen evaluation configuration."""
    data = {
        "evaluation_id": evaluation.id,
        "evaluation_name": evaluation.name,
        "mode": evaluation.mode,
        "status": evaluation.status,
        "dataset_id": evaluation.dataset_id,
        "judge_config_id": evaluation.judge_config_id,
        "config": evaluation.config or {},
        "generated_at": datetime.now(UTC).isoformat(),
    }

    content = json.dumps(data, indent=2, default=str).encode("utf-8")
    await save_artifact(
        db=db,
        evaluation_id=evaluation.id,
        filename="config.json",
        content=content,
        content_type="application/json",
        artifacts_dir=artifacts_dir,
        description="Frozen evaluation configuration snapshot",
    )
