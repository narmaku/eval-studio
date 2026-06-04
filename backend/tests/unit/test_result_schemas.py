"""Unit tests for arena result schemas."""

from app.schemas.result import ArenaContestantSummary, ArenaLeaderboardResponse, ResultResponse


def test_result_response_has_contestant_model():
    """ResultResponse should include contestant_model field."""
    result = ResultResponse(
        id="r1",
        evaluation_id="e1",
        dataset_item_id="d1",
        session_id=None,
        score=0.85,
        passed=True,
        actual_answer="answer",
        judge_reasoning="good",
        scores_breakdown=None,
        created_at="2025-01-01T00:00:00",
        contestant_model="model-a",
    )
    assert result.contestant_model == "model-a"


def test_result_response_contestant_model_default_none():
    """ResultResponse contestant_model defaults to None for backward compat."""
    result = ResultResponse(
        id="r1",
        evaluation_id="e1",
        dataset_item_id="d1",
        session_id=None,
        score=0.85,
        passed=True,
        actual_answer="answer",
        judge_reasoning="good",
        scores_breakdown=None,
        created_at="2025-01-01T00:00:00",
    )
    assert result.contestant_model is None


def test_arena_contestant_summary_schema():
    """ArenaContestantSummary validates correctly."""
    summary = ArenaContestantSummary(
        contestant_model="gpt-4",
        total_items=10,
        passed_count=8,
        failed_count=1,
        errored_count=1,
        average_score=0.82,
        min_score=0.3,
        max_score=1.0,
    )
    assert summary.contestant_model == "gpt-4"
    assert summary.total_items == 10
    assert summary.passed_count == 8
    assert summary.failed_count == 1
    assert summary.errored_count == 1
    assert summary.average_score == 0.82
    assert summary.min_score == 0.3
    assert summary.max_score == 1.0


def test_arena_contestant_summary_null_scores():
    """ArenaContestantSummary with all errored results has null min/max."""
    summary = ArenaContestantSummary(
        contestant_model="broken-model",
        total_items=5,
        passed_count=0,
        failed_count=0,
        errored_count=5,
        average_score=0.0,
        min_score=None,
        max_score=None,
    )
    assert summary.min_score is None
    assert summary.max_score is None


def test_arena_leaderboard_response_schema():
    """ArenaLeaderboardResponse validates with sorted contestants."""
    leaderboard = ArenaLeaderboardResponse(
        evaluation_id="e1",
        evaluation_name="Arena Test",
        contestants=[
            ArenaContestantSummary(
                contestant_model="best-model",
                total_items=5,
                passed_count=5,
                failed_count=0,
                errored_count=0,
                average_score=0.95,
                min_score=0.9,
                max_score=1.0,
            ),
            ArenaContestantSummary(
                contestant_model="ok-model",
                total_items=5,
                passed_count=3,
                failed_count=2,
                errored_count=0,
                average_score=0.65,
                min_score=0.4,
                max_score=0.9,
            ),
        ],
    )
    assert leaderboard.evaluation_id == "e1"
    assert len(leaderboard.contestants) == 2
    # First contestant has higher score (sorted desc)
    assert leaderboard.contestants[0].average_score > leaderboard.contestants[1].average_score


def test_arena_contestant_summary_average_breakdown_default_none():
    """average_breakdown defaults to None when not provided."""
    summary = ArenaContestantSummary(
        contestant_model="model-a",
        total_items=5,
        passed_count=4,
        failed_count=1,
        errored_count=0,
        average_score=0.8,
        min_score=0.5,
        max_score=1.0,
    )
    assert summary.average_breakdown is None


def test_arena_contestant_summary_with_average_breakdown():
    """average_breakdown is correctly set when provided."""
    breakdown = {"faithfulness": 0.85, "relevance": 0.72, "fluency": 0.91}
    summary = ArenaContestantSummary(
        contestant_model="model-a",
        total_items=5,
        passed_count=4,
        failed_count=1,
        errored_count=0,
        average_score=0.8,
        min_score=0.5,
        max_score=1.0,
        average_breakdown=breakdown,
    )
    assert summary.average_breakdown is not None
    assert summary.average_breakdown["faithfulness"] == 0.85
    assert summary.average_breakdown["relevance"] == 0.72
    assert summary.average_breakdown["fluency"] == 0.91
    assert len(summary.average_breakdown) == 3


def test_arena_leaderboard_with_average_breakdown():
    """ArenaLeaderboardResponse correctly includes average_breakdown per contestant."""
    leaderboard = ArenaLeaderboardResponse(
        evaluation_id="e1",
        evaluation_name="Arena with Breakdown",
        contestants=[
            ArenaContestantSummary(
                contestant_model="model-a",
                total_items=5,
                passed_count=4,
                failed_count=1,
                errored_count=0,
                average_score=0.82,
                min_score=0.6,
                max_score=1.0,
                average_breakdown={"accuracy": 0.9, "clarity": 0.74},
            ),
            ArenaContestantSummary(
                contestant_model="model-b",
                total_items=5,
                passed_count=3,
                failed_count=2,
                errored_count=0,
                average_score=0.65,
                min_score=0.3,
                max_score=0.9,
                average_breakdown={"accuracy": 0.6, "clarity": 0.7},
            ),
        ],
    )
    assert leaderboard.contestants[0].average_breakdown == {"accuracy": 0.9, "clarity": 0.74}
    assert leaderboard.contestants[1].average_breakdown == {"accuracy": 0.6, "clarity": 0.7}
