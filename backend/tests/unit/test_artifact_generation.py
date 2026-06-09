"""Tests for the artifact generation helper."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.artifact import Artifact
from app.models.dataset import Dataset, DatasetItem
from app.models.evaluation import Evaluation
from app.models.result import Result
from app.services.artifact_generation import _serialize_result, generate_evaluation_artifacts


class TestGenerateEvaluationArtifacts:
    """Tests for the generate_evaluation_artifacts function."""

    async def _seed_evaluation(self, db_session, tmp_path, *, mode="qa", status="completed", config=None):
        """Helper to create a completed evaluation with dataset and results."""
        dataset = Dataset(name="Test Dataset", format="qa_pairs", item_count=2)
        db_session.add(dataset)
        await db_session.commit()
        await db_session.refresh(dataset)

        item1 = DatasetItem(
            dataset_id=dataset.id,
            question="What is Python?",
            expected_answer="A programming language",
            order_index=0,
        )
        item2 = DatasetItem(
            dataset_id=dataset.id,
            question="What is FastAPI?",
            expected_answer="A web framework",
            order_index=1,
        )
        db_session.add_all([item1, item2])
        await db_session.commit()
        await db_session.refresh(item1)
        await db_session.refresh(item2)

        evaluation = Evaluation(
            name="Test Evaluation",
            mode=mode,
            status=status,
            dataset_id=dataset.id,
            config=config or {"model": "test-model"},
        )
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        result1 = Result(
            evaluation_id=evaluation.id,
            dataset_item_id=item1.id,
            score=0.9,
            passed=True,
            actual_answer="Python is a programming language",
            judge_reasoning="Good answer",
            scores_breakdown={"accuracy": 0.9, "completeness": 0.85},
        )
        result2 = Result(
            evaluation_id=evaluation.id,
            dataset_item_id=item2.id,
            score=0.6,
            passed=False,
            actual_answer="FastAPI is a tool",
            judge_reasoning="Incomplete answer",
            scores_breakdown={"accuracy": 0.6, "completeness": 0.5},
        )
        db_session.add_all([result1, result2])
        await db_session.commit()

        return evaluation

    @pytest.mark.asyncio
    async def test_creates_three_artifacts(self, db_session, tmp_path):
        """generate_evaluation_artifacts creates exactly 3 artifact files."""
        evaluation = await self._seed_evaluation(db_session, tmp_path)
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        result = await db_session.execute(select(Artifact).where(Artifact.evaluation_id == evaluation.id))
        artifacts = result.scalars().all()
        assert len(artifacts) == 3

        filenames = {a.filename for a in artifacts}
        assert "results.json" in filenames
        assert "summary.md" in filenames
        assert "config.json" in filenames

    @pytest.mark.asyncio
    async def test_results_json_content(self, db_session, tmp_path):
        """results.json contains the correct structure with scores, answers, and reasoning."""
        evaluation = await self._seed_evaluation(db_session, tmp_path)
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        result = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "results.json")
        )
        artifact = result.scalar_one()

        from pathlib import Path

        file_path = Path(artifacts_dir) / artifact.storage_path
        data = json.loads(file_path.read_text())

        assert "evaluation_id" in data
        assert "results" in data
        assert len(data["results"]) == 2

        first_result = data["results"][0]
        assert "score" in first_result
        assert "passed" in first_result
        assert "actual_answer" in first_result
        assert "judge_reasoning" in first_result
        assert "scores_breakdown" in first_result

    @pytest.mark.asyncio
    async def test_summary_md_content(self, db_session, tmp_path):
        """summary.md contains evaluation name, mode, metrics, and per-item table."""
        evaluation = await self._seed_evaluation(db_session, tmp_path)
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        result = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "summary.md")
        )
        artifact = result.scalar_one()

        from pathlib import Path

        file_path = Path(artifacts_dir) / artifact.storage_path
        content = file_path.read_text()

        # Check metadata
        assert "Test Evaluation" in content
        assert "qa" in content

        # Check aggregate metrics
        assert "Pass Rate" in content or "pass rate" in content.lower()
        assert "1" in content  # 1 passed
        assert "2" in content  # 2 total

        # Check per-item table exists (markdown table format)
        assert "|" in content  # Markdown table delimiter
        assert "Score" in content or "score" in content.lower()

    @pytest.mark.asyncio
    async def test_config_json_content(self, db_session, tmp_path):
        """config.json contains frozen evaluation configuration."""
        config = {"model": "gpt-4", "max_concurrency": 5, "model_params": {"temperature": 0.7}}
        evaluation = await self._seed_evaluation(db_session, tmp_path, config=config)
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        result = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "config.json")
        )
        artifact = result.scalar_one()

        from pathlib import Path

        file_path = Path(artifacts_dir) / artifact.storage_path
        data = json.loads(file_path.read_text())

        assert data["evaluation_name"] == "Test Evaluation"
        assert data["mode"] == "qa"
        assert data["config"]["model"] == "gpt-4"
        assert data["config"]["max_concurrency"] == 5

    @pytest.mark.asyncio
    async def test_creates_artifacts_for_failed_evaluation(self, db_session, tmp_path):
        """Artifacts are created even when an evaluation has failed status."""
        evaluation = await self._seed_evaluation(db_session, tmp_path, status="failed")
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        result = await db_session.execute(select(Artifact).where(Artifact.evaluation_id == evaluation.id))
        artifacts = result.scalars().all()
        assert len(artifacts) == 3

    @pytest.mark.asyncio
    async def test_errors_are_caught_and_logged(self, db_session, tmp_path):
        """Artifact generation errors are caught and logged, never raising."""
        evaluation = await self._seed_evaluation(db_session, tmp_path)
        # Use an invalid artifacts_dir (a file instead of a directory) to force an error
        invalid_dir = str(tmp_path / "not_a_dir")
        (tmp_path / "not_a_dir").write_text("i am a file")

        # Should not raise
        await generate_evaluation_artifacts(evaluation.id, db_session, invalid_dir)

    @pytest.mark.asyncio
    async def test_nonexistent_evaluation_does_not_raise(self, db_session, tmp_path):
        """Calling with a non-existent evaluation_id does not raise."""
        artifacts_dir = str(tmp_path / "artifacts")

        # Should not raise
        await generate_evaluation_artifacts("nonexistent-id", db_session, artifacts_dir)

    @pytest.mark.asyncio
    async def test_results_json_includes_retrieved_chunks(self, db_session, tmp_path):
        """results.json includes retrieved_chunks when present (RAG mode)."""
        dataset = Dataset(name="RAG Dataset", format="qa_pairs", item_count=1)
        db_session.add(dataset)
        await db_session.commit()
        await db_session.refresh(dataset)

        item = DatasetItem(
            dataset_id=dataset.id,
            question="What is RAG?",
            expected_answer="Retrieval-Augmented Generation",
            order_index=0,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        evaluation = Evaluation(
            name="RAG Eval",
            mode="rag",
            status="completed",
            dataset_id=dataset.id,
            config={"model": "test-model"},
        )
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        result = Result(
            evaluation_id=evaluation.id,
            dataset_item_id=item.id,
            score=0.8,
            passed=True,
            actual_answer="RAG is a technique",
            judge_reasoning="Good",
            retrieved_chunks=[{"content": "chunk 1"}, {"content": "chunk 2"}],
        )
        db_session.add(result)
        await db_session.commit()

        artifacts_dir = str(tmp_path / "artifacts")
        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_result = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "results.json")
        )
        artifact = artifact_result.scalar_one()

        from pathlib import Path

        file_path = Path(artifacts_dir) / artifact.storage_path
        data = json.loads(file_path.read_text())

        assert data["results"][0]["retrieved_chunks"] == [{"content": "chunk 1"}, {"content": "chunk 2"}]

    @pytest.mark.asyncio
    async def test_results_json_includes_contestant_model(self, db_session, tmp_path):
        """results.json includes contestant_model when present (arena mode)."""
        dataset = Dataset(name="Arena Dataset", format="qa_pairs", item_count=1)
        db_session.add(dataset)
        await db_session.commit()
        await db_session.refresh(dataset)

        item = DatasetItem(
            dataset_id=dataset.id,
            question="Hello?",
            expected_answer="Hi",
            order_index=0,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        evaluation = Evaluation(
            name="Arena Eval",
            mode="arena",
            status="completed",
            dataset_id=dataset.id,
            config={"contestants": [{"model": "model-a"}, {"model": "model-b"}]},
        )
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        result = Result(
            evaluation_id=evaluation.id,
            dataset_item_id=item.id,
            contestant_model="model-a",
            score=0.8,
            passed=True,
            actual_answer="Hi!",
            judge_reasoning="Good",
        )
        db_session.add(result)
        await db_session.commit()

        artifacts_dir = str(tmp_path / "artifacts")
        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_result = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "results.json")
        )
        artifact = artifact_result.scalar_one()

        from pathlib import Path

        file_path = Path(artifacts_dir) / artifact.storage_path
        data = json.loads(file_path.read_text())

        assert data["results"][0]["contestant_model"] == "model-a"

    @pytest.mark.asyncio
    async def test_broadcasts_log_on_success(self, db_session, tmp_path):
        """A log message is broadcast when artifacts are generated successfully."""
        evaluation = await self._seed_evaluation(db_session, tmp_path)
        artifacts_dir = str(tmp_path / "artifacts")

        with patch("app.services.artifact_generation.broadcast_log", new_callable=AsyncMock) as mock_log:
            await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

            # Check that at least one broadcast_log call mentions artifacts
            calls = mock_log.call_args_list
            messages = [call.kwargs.get("message", "") for call in calls]
            assert any("artifact" in m.lower() for m in messages), f"Expected artifact log, got: {messages}"

    @pytest.mark.asyncio
    async def test_broadcasts_log_on_error(self, db_session, tmp_path):
        """A log message is broadcast when artifact generation fails."""
        evaluation = await self._seed_evaluation(db_session, tmp_path)
        invalid_dir = str(tmp_path / "not_a_dir")
        (tmp_path / "not_a_dir").write_text("i am a file")

        with patch("app.services.artifact_generation.broadcast_log", new_callable=AsyncMock) as mock_log:
            await generate_evaluation_artifacts(evaluation.id, db_session, invalid_dir)

            calls = mock_log.call_args_list
            # Should have an error-level log
            levels = [call.kwargs.get("level", "") for call in calls]
            assert "error" in levels, f"Expected error log level, got: {levels}"


class TestArtifactGenerationEdgeCases:
    """Tests for edge cases and uncovered branches in artifact generation."""

    async def _create_evaluation_with_results(self, db_session, *, results_data=None, mode="qa", config=None):
        """Helper to create an evaluation with custom result data."""
        dataset = Dataset(name="Edge Case Dataset", format="qa_pairs", item_count=1)
        db_session.add(dataset)
        await db_session.commit()
        await db_session.refresh(dataset)

        item = DatasetItem(
            dataset_id=dataset.id,
            question="Test question?",
            expected_answer="Test answer",
            order_index=0,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        evaluation = Evaluation(
            name="Edge Case Eval",
            mode=mode,
            status="completed",
            dataset_id=dataset.id,
            config=config,
        )
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        if results_data:
            for rd in results_data:
                rd.setdefault("evaluation_id", evaluation.id)
                rd.setdefault("dataset_item_id", item.id)
                result = Result(**rd)
                db_session.add(result)
            await db_session.commit()

        return evaluation

    @pytest.mark.asyncio
    async def test_empty_results_summary_omits_mean_and_median(self, db_session, tmp_path):
        """summary.md omits Mean/Median Score when there are no results."""
        evaluation = await self._create_evaluation_with_results(db_session, results_data=[])
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "summary.md")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        content = (Path(artifacts_dir) / artifact.storage_path).read_text()

        assert "Total Items**: 0" in content
        assert "Mean Score" not in content
        assert "Median Score" not in content
        # Pass rate should not appear when total_count == 0
        assert "Pass Rate" not in content

    @pytest.mark.asyncio
    async def test_empty_results_json_has_empty_array(self, db_session, tmp_path):
        """results.json contains an empty results array when no results exist."""
        evaluation = await self._create_evaluation_with_results(db_session, results_data=[])
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "results.json")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        data = json.loads((Path(artifacts_dir) / artifact.storage_path).read_text())
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_results_with_none_scores_excluded_from_mean(self, db_session, tmp_path):
        """Results with score=None are excluded from mean/median calculations."""
        evaluation = await self._create_evaluation_with_results(
            db_session,
            results_data=[
                {"score": 0.8, "passed": True, "actual_answer": "a"},
                {"score": None, "passed": False, "actual_answer": "b"},
            ],
        )
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "summary.md")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        content = (Path(artifacts_dir) / artifact.storage_path).read_text()

        # Mean should be 0.800 (only one scored result)
        assert "0.800" in content
        # Median should also be 0.800
        assert "Median Score**: 0.800" in content

    @pytest.mark.asyncio
    async def test_odd_result_count_median_calculation(self, db_session, tmp_path):
        """Median uses single middle element when result count is odd."""
        dataset = Dataset(name="Odd Dataset", format="qa_pairs", item_count=3)
        db_session.add(dataset)
        await db_session.commit()
        await db_session.refresh(dataset)

        items = []
        for i in range(3):
            item = DatasetItem(
                dataset_id=dataset.id,
                question=f"Q{i}?",
                expected_answer=f"A{i}",
                order_index=i,
            )
            db_session.add(item)
            items.append(item)
        await db_session.commit()
        for item in items:
            await db_session.refresh(item)

        evaluation = Evaluation(
            name="Odd Count Eval",
            mode="qa",
            status="completed",
            dataset_id=dataset.id,
            config={"model": "test"},
        )
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        # Scores: 0.3, 0.7, 0.9 -> sorted: [0.3, 0.7, 0.9], median = 0.7
        scores = [0.3, 0.7, 0.9]
        for i, score in enumerate(scores):
            result = Result(
                evaluation_id=evaluation.id,
                dataset_item_id=items[i].id,
                score=score,
                passed=score >= 0.5,
                actual_answer=f"Answer {i}",
            )
            db_session.add(result)
        await db_session.commit()

        artifacts_dir = str(tmp_path / "artifacts")
        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "summary.md")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        content = (Path(artifacts_dir) / artifact.storage_path).read_text()

        assert "Median Score**: 0.700" in content

    @pytest.mark.asyncio
    async def test_summary_md_contestant_table_format(self, db_session, tmp_path):
        """summary.md uses the contestant table format when contestant_model is present."""
        evaluation = await self._create_evaluation_with_results(
            db_session,
            mode="arena",
            results_data=[
                {"score": 0.9, "passed": True, "actual_answer": "a", "contestant_model": "model-x"},
                {"score": 0.4, "passed": False, "actual_answer": "b", "contestant_model": "model-y"},
            ],
        )
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "summary.md")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        content = (Path(artifacts_dir) / artifact.storage_path).read_text()

        # Should include the Contestant column header
        assert "Contestant" in content
        assert "model-x" in content
        assert "model-y" in content

    @pytest.mark.asyncio
    async def test_summary_md_pipe_in_reasoning_is_escaped(self, db_session, tmp_path):
        """Pipe characters in judge_reasoning are escaped in the markdown table."""
        evaluation = await self._create_evaluation_with_results(
            db_session,
            results_data=[
                {
                    "score": 0.5,
                    "passed": False,
                    "actual_answer": "a",
                    "judge_reasoning": "Score is 5|10 because of |issues|",
                },
            ],
        )
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "summary.md")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        content = (Path(artifacts_dir) / artifact.storage_path).read_text()

        # Pipe chars should be escaped with backslash in the table
        assert "\\|" in content

    @pytest.mark.asyncio
    async def test_summary_md_none_judge_reasoning(self, db_session, tmp_path):
        """summary.md handles None judge_reasoning without errors."""
        evaluation = await self._create_evaluation_with_results(
            db_session,
            results_data=[
                {"score": 0.5, "passed": False, "actual_answer": "a", "judge_reasoning": None},
            ],
        )
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "summary.md")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        content = (Path(artifacts_dir) / artifact.storage_path).read_text()

        # Should contain a table row with empty reasoning
        assert "FAIL" in content

    @pytest.mark.asyncio
    async def test_config_json_with_none_config(self, db_session, tmp_path):
        """config.json uses empty dict when evaluation.config is None."""
        evaluation = await self._create_evaluation_with_results(
            db_session, results_data=[], config=None
        )
        artifacts_dir = str(tmp_path / "artifacts")

        await generate_evaluation_artifacts(evaluation.id, db_session, artifacts_dir)

        artifact_row = await db_session.execute(
            select(Artifact).where(Artifact.evaluation_id == evaluation.id, Artifact.filename == "config.json")
        )
        artifact = artifact_row.scalar_one()

        from pathlib import Path

        data = json.loads((Path(artifacts_dir) / artifact.storage_path).read_text())
        assert data["config"] == {}

    @pytest.mark.asyncio
    async def test_broadcast_failure_in_error_handler_does_not_raise(self, db_session, tmp_path):
        """When both artifact generation and broadcast_log fail, nothing is raised."""
        evaluation = await self._create_evaluation_with_results(db_session, results_data=[])
        invalid_dir = str(tmp_path / "not_a_dir")
        (tmp_path / "not_a_dir").write_text("i am a file")

        # Make broadcast_log itself raise to hit the nested except
        with patch(
            "app.services.artifact_generation.broadcast_log",
            new_callable=AsyncMock,
            side_effect=RuntimeError("broadcast broken"),
        ):
            # Should not raise despite both failures
            await generate_evaluation_artifacts(evaluation.id, db_session, invalid_dir)


class TestSerializeResult:
    """Unit tests for the _serialize_result helper function."""

    def test_basic_result_fields(self):
        """_serialize_result includes all required fields."""
        result = Result(
            id="r-1",
            dataset_item_id="di-1",
            score=0.85,
            passed=True,
            actual_answer="Test answer",
            judge_reasoning="Good",
            scores_breakdown={"accuracy": 0.85},
        )
        data = _serialize_result(result)

        assert data["id"] == "r-1"
        assert data["dataset_item_id"] == "di-1"
        assert data["score"] == 0.85
        assert data["passed"] is True
        assert data["actual_answer"] == "Test answer"
        assert data["judge_reasoning"] == "Good"
        assert data["scores_breakdown"] == {"accuracy": 0.85}

    def test_excludes_retrieved_chunks_when_none(self):
        """_serialize_result omits retrieved_chunks when it is None."""
        result = Result(
            id="r-2",
            score=0.5,
            passed=False,
            retrieved_chunks=None,
            contestant_model=None,
        )
        data = _serialize_result(result)

        assert "retrieved_chunks" not in data
        assert "contestant_model" not in data

    def test_includes_retrieved_chunks_when_present(self):
        """_serialize_result includes retrieved_chunks when not None."""
        chunks = [{"text": "chunk1"}]
        result = Result(id="r-3", score=0.5, passed=True, retrieved_chunks=chunks)
        data = _serialize_result(result)

        assert data["retrieved_chunks"] == chunks

    def test_includes_contestant_model_when_present(self):
        """_serialize_result includes contestant_model when not None."""
        result = Result(id="r-4", score=0.5, passed=True, contestant_model="gpt-4")
        data = _serialize_result(result)

        assert data["contestant_model"] == "gpt-4"

    def test_none_score_preserved(self):
        """_serialize_result preserves None score value."""
        result = Result(id="r-5", score=None, passed=False)
        data = _serialize_result(result)

        assert data["score"] is None
