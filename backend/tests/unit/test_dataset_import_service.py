"""Unit tests for the dataset import service."""

import json
import time

import pytest
import yaml

from app.services.dataset_import_service import (
    AnalyzedFile,
    DetectedFormat,
    _analysis_sessions,
    apply_mapping,
    create_session,
    delete_session,
    detect_format,
    extract_schema,
    get_session,
    suggest_mapping,
)

# -----------------------------------------------------------------------
# detect_format tests
# -----------------------------------------------------------------------


class TestDetectFormat:
    """Tests for format detection from filename and content."""

    def test_yaml_extension(self):
        content = b"- question: hello\n  answer: world\n"
        assert detect_format("data.yaml", content) == DetectedFormat.yaml

    def test_yml_extension(self):
        content = b"- question: hello\n"
        assert detect_format("data.yml", content) == DetectedFormat.yaml

    def test_jsonl_extension(self):
        content = b'{"q": "a"}\n{"q": "b"}\n'
        assert detect_format("data.jsonl", content) == DetectedFormat.jsonl

    def test_json_extension(self):
        content = b'[{"q": "a"}]'
        assert detect_format("data.json", content) == DetectedFormat.json

    def test_csv_extension(self):
        content = b"question,answer\nhello,world\n"
        assert detect_format("data.csv", content) == DetectedFormat.csv

    def test_tsv_extension(self):
        content = b"question\tanswer\nhello\tworld\n"
        assert detect_format("data.tsv", content) == DetectedFormat.tsv

    def test_binary_rejection(self):
        content = b"\x00\x01\x02\x03\x04\x05binary garbage"
        assert detect_format("data.bin", content) == DetectedFormat.unknown

    def test_binary_rejection_with_yaml_extension(self):
        content = b"\x00\x01\x02\x03\x04\x05binary garbage"
        assert detect_format("data.yaml", content) == DetectedFormat.unknown

    def test_content_sniff_json_array(self):
        content = b'[{"question": "hi"}]'
        assert detect_format("data.txt", content) == DetectedFormat.json

    def test_content_sniff_jsonl(self):
        content = b'{"q": "a"}\n{"q": "b"}\n{"q": "c"}\n'
        assert detect_format("data.txt", content) == DetectedFormat.jsonl

    def test_content_sniff_tsv(self):
        content = b"col1\tcol2\nval1\tval2\n"
        assert detect_format("data.txt", content) == DetectedFormat.tsv

    def test_content_sniff_csv(self):
        content = b"col1,col2\nval1,val2\n"
        assert detect_format("data.txt", content) == DetectedFormat.csv

    def test_empty_content(self):
        assert detect_format("data.txt", b"") == DetectedFormat.unknown

    def test_unknown_content(self):
        assert detect_format("data.txt", b"just some text without structure") == DetectedFormat.unknown


# -----------------------------------------------------------------------
# extract_schema tests
# -----------------------------------------------------------------------


class TestExtractSchema:
    """Tests for schema extraction from different formats."""

    def test_yaml_flat_list(self):
        data = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
        content = yaml.dump(data).encode()
        schema = extract_schema(content, DetectedFormat.yaml)
        assert "answer" in schema.fields
        assert "question" in schema.fields
        assert schema.total_rows == 2
        assert len(schema.sample_rows) == 2

    def test_yaml_nested_structure(self):
        data = [{"question": "Q1", "context": {"paragraph": "text", "source": "wiki"}}]
        content = yaml.dump(data).encode()
        schema = extract_schema(content, DetectedFormat.yaml)
        assert "context.paragraph" in schema.fields
        assert "context.source" in schema.fields
        assert len(schema.nested_paths) > 0

    def test_yaml_dict_with_data_key(self):
        data = {"version": "1.0", "data": [{"q": "Q1"}, {"q": "Q2"}]}
        content = yaml.dump(data).encode()
        schema = extract_schema(content, DetectedFormat.yaml)
        assert schema.total_rows == 2
        assert "q" in schema.fields

    def test_jsonl_uniform(self):
        lines = [json.dumps({"input": "I1", "output": "O1"}), json.dumps({"input": "I2", "output": "O2"})]
        content = "\n".join(lines).encode()
        schema = extract_schema(content, DetectedFormat.jsonl)
        assert "input" in schema.fields
        assert "output" in schema.fields
        assert schema.total_rows == 2

    def test_jsonl_mixed_fields(self):
        lines = [json.dumps({"a": 1, "b": 2}), json.dumps({"a": 3, "c": 4})]
        content = "\n".join(lines).encode()
        schema = extract_schema(content, DetectedFormat.jsonl)
        assert "a" in schema.fields
        assert "b" in schema.fields
        assert "c" in schema.fields

    def test_json_array(self):
        data = [{"prompt": "P1", "response": "R1"}]
        content = json.dumps(data).encode()
        schema = extract_schema(content, DetectedFormat.json)
        assert "prompt" in schema.fields
        assert "response" in schema.fields
        assert schema.total_rows == 1

    def test_json_nested_squad_like(self):
        data = {
            "data": [
                {"question": "Q1", "answers": {"text": ["A1"]}},
                {"question": "Q2", "answers": {"text": ["A2"]}},
            ]
        }
        content = json.dumps(data).encode()
        schema = extract_schema(content, DetectedFormat.json)
        assert "answers.text[0]" in schema.fields
        assert "question" in schema.fields
        assert schema.total_rows == 2

    def test_csv_with_header(self):
        content = b"question,answer,category\nQ1,A1,math\nQ2,A2,science\n"
        schema = extract_schema(content, DetectedFormat.csv)
        assert "question" in schema.fields
        assert "answer" in schema.fields
        assert "category" in schema.fields
        assert schema.total_rows == 2
        assert schema.has_header

    def test_tsv_format(self):
        content = b"question\tanswer\nQ1\tA1\n"
        schema = extract_schema(content, DetectedFormat.tsv)
        assert "question" in schema.fields
        assert "answer" in schema.fields
        assert schema.total_rows == 1

    def test_sample_size_limit(self):
        data = [{"q": f"Q{i}"} for i in range(50)]
        content = json.dumps(data).encode()
        schema = extract_schema(content, DetectedFormat.json, sample_size=5)
        assert len(schema.sample_rows) == 5
        assert schema.total_rows == 50

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Cannot extract schema"):
            extract_schema(b"data", DetectedFormat.unknown)


# -----------------------------------------------------------------------
# all_rows preservation tests — import must not truncate to sample_size
# -----------------------------------------------------------------------


class TestAllRowsPreservation:
    """Tests that FileSchema.all_rows stores every row, not just the sample."""

    def test_yaml_all_rows_exceeds_sample(self):
        """YAML file with 30 items: all_rows has 30, sample_rows has sample_size."""
        data = [{"question": f"Q{i}", "answer": f"A{i}"} for i in range(30)]
        content = yaml.dump(data).encode()
        schema = extract_schema(content, DetectedFormat.yaml, sample_size=20)
        assert len(schema.all_rows) == 30
        assert len(schema.sample_rows) == 20
        assert schema.total_rows == 30

    def test_jsonl_all_rows_exceeds_sample(self):
        """JSONL file with 25 items: all_rows has 25, sample_rows has sample_size."""
        lines = [json.dumps({"input": f"I{i}", "output": f"O{i}"}) for i in range(25)]
        content = "\n".join(lines).encode()
        schema = extract_schema(content, DetectedFormat.jsonl, sample_size=20)
        assert len(schema.all_rows) == 25
        assert len(schema.sample_rows) == 20
        assert schema.total_rows == 25

    def test_json_all_rows_exceeds_sample(self):
        """JSON array with 50 items: all_rows has 50, sample_rows has sample_size."""
        data = [{"prompt": f"P{i}", "response": f"R{i}"} for i in range(50)]
        content = json.dumps(data).encode()
        schema = extract_schema(content, DetectedFormat.json, sample_size=20)
        assert len(schema.all_rows) == 50
        assert len(schema.sample_rows) == 20
        assert schema.total_rows == 50

    def test_csv_all_rows_exceeds_sample(self):
        """CSV file with 50 items: all_rows has 50, sample_rows has sample_size."""
        header = "question,answer"
        rows = [f"Q{i},A{i}" for i in range(50)]
        content = (header + "\n" + "\n".join(rows) + "\n").encode()
        schema = extract_schema(content, DetectedFormat.csv, sample_size=20)
        assert len(schema.all_rows) == 50
        assert len(schema.sample_rows) == 20
        assert schema.total_rows == 50

    def test_all_rows_matches_sample_when_under_limit(self):
        """When row count is under sample_size, all_rows == sample_rows."""
        data = [{"q": f"Q{i}"} for i in range(5)]
        content = json.dumps(data).encode()
        schema = extract_schema(content, DetectedFormat.json, sample_size=20)
        assert len(schema.all_rows) == 5
        assert len(schema.sample_rows) == 5
        assert schema.all_rows == schema.sample_rows

    def test_tsv_all_rows_exceeds_sample(self):
        """TSV file with 25 items: all_rows has 25, sample_rows has sample_size."""
        header = "question\tanswer"
        rows = [f"Q{i}\tA{i}" for i in range(25)]
        content = (header + "\n" + "\n".join(rows) + "\n").encode()
        schema = extract_schema(content, DetectedFormat.tsv, sample_size=20)
        assert len(schema.all_rows) == 25
        assert len(schema.sample_rows) == 20
        assert schema.total_rows == 25


# -----------------------------------------------------------------------
# suggest_mapping tests
# -----------------------------------------------------------------------


class TestSuggestMapping:
    """Tests for field mapping suggestion."""

    def test_question_and_answer(self):
        mapping = suggest_mapping(["question", "answer", "category"])
        assert mapping.question_field == "question"
        assert mapping.answer_field == "answer"
        assert "category" in mapping.metadata_fields
        assert mapping.confidence > 0.5

    def test_input_and_output(self):
        mapping = suggest_mapping(["input", "output", "id"])
        assert mapping.question_field == "input"
        assert mapping.answer_field == "output"

    def test_prompt_and_response(self):
        mapping = suggest_mapping(["prompt", "response", "score"])
        assert mapping.question_field == "prompt"
        assert mapping.answer_field == "response"

    def test_instruction_and_output(self):
        mapping = suggest_mapping(["instruction", "output"])
        assert mapping.question_field == "instruction"
        assert mapping.answer_field == "output"

    def test_question_only(self):
        mapping = suggest_mapping(["question", "source", "id"])
        assert mapping.question_field == "question"
        assert mapping.answer_field is None
        assert mapping.confidence > 0

    def test_no_match(self):
        mapping = suggest_mapping(["foo", "bar", "baz"])
        assert mapping.question_field is None
        assert mapping.answer_field is None
        assert mapping.confidence == 0.0

    def test_nested_answer_field(self):
        mapping = suggest_mapping(["question", "answers.text[0]", "context"])
        assert mapping.question_field == "question"
        assert mapping.answer_field == "answers.text[0]"

    def test_expected_answer(self):
        mapping = suggest_mapping(["question", "expected_answer"])
        assert mapping.question_field == "question"
        assert mapping.answer_field == "expected_answer"

    def test_single_field_text(self):
        mapping = suggest_mapping(["text"])
        assert mapping.question_field == "text"

    def test_query_and_target(self):
        mapping = suggest_mapping(["query", "target"])
        assert mapping.question_field == "query"
        assert mapping.answer_field == "target"


# -----------------------------------------------------------------------
# apply_mapping tests
# -----------------------------------------------------------------------


class TestApplyMapping:
    """Tests for mapping application to transform rows."""

    def test_basic_mapping(self):
        rows = [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}]
        result = apply_mapping(rows, question_field="question", answer_field="answer")
        assert len(result) == 2
        assert result[0]["question"] == "Q1"
        assert result[0]["expected_answer"] == "A1"

    def test_nested_field(self):
        rows = [{"question": "Q1", "answers": {"text": ["A1"]}}]
        result = apply_mapping(rows, question_field="question", answer_field="answers.text[0]")
        assert result[0]["expected_answer"] == "A1"

    def test_remaining_to_metadata(self):
        rows = [{"question": "Q1", "answer": "A1", "source": "wiki", "id": 42}]
        result = apply_mapping(rows, question_field="question", answer_field="answer")
        assert result[0]["metadata"]["source"] == "wiki"
        assert result[0]["metadata"]["id"] == 42

    def test_explicit_metadata_fields(self):
        rows = [{"question": "Q1", "answer": "A1", "source": "wiki", "id": 42}]
        result = apply_mapping(rows, question_field="question", answer_field="answer", metadata_fields=["source"])
        assert result[0]["metadata"]["source"] == "wiki"
        assert "id" not in result[0].get("metadata", {})

    def test_skip_missing_question(self):
        rows = [{"question": "Q1", "answer": "A1"}, {"answer": "A2"}]
        result = apply_mapping(rows, question_field="question", answer_field="answer")
        assert len(result) == 1

    def test_coercion_to_string(self):
        rows = [{"question": 42, "answer": True}]
        result = apply_mapping(rows, question_field="question", answer_field="answer")
        assert result[0]["question"] == "42"
        assert result[0]["expected_answer"] == "True"

    def test_no_answer_field(self):
        rows = [{"question": "Q1", "extra": "E1"}]
        result = apply_mapping(rows, question_field="question")
        assert result[0]["expected_answer"] is None
        assert result[0]["metadata"]["extra"] == "E1"


# -----------------------------------------------------------------------
# Session management tests
# -----------------------------------------------------------------------


class TestSessionManagement:
    """Tests for in-memory session store."""

    def setup_method(self):
        _analysis_sessions.clear()

    def test_create_and_get_session(self):
        af = AnalyzedFile(filename="test.yaml", format=DetectedFormat.yaml)
        session = create_session([af])
        assert session.id
        retrieved = get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id
        assert len(retrieved.files) == 1

    def test_delete_session(self):
        af = AnalyzedFile(filename="test.yaml", format=DetectedFormat.yaml)
        session = create_session([af])
        assert delete_session(session.id) is True
        assert get_session(session.id) is None

    def test_delete_nonexistent(self):
        assert delete_session("nonexistent-id") is False

    def test_get_nonexistent(self):
        assert get_session("nonexistent-id") is None

    def test_expired_session_cleanup(self):
        af = AnalyzedFile(filename="test.yaml", format=DetectedFormat.yaml)
        session = create_session([af])
        # Manually expire the session
        _analysis_sessions[session.id].created_at = time.time() - 20 * 60
        assert get_session(session.id) is None


# -----------------------------------------------------------------------
# Schema validation tests
# -----------------------------------------------------------------------


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_import_request_requires_name(self):
        from pydantic import ValidationError

        from app.schemas.dataset_import import ImportRequest

        with pytest.raises(ValidationError):
            ImportRequest(
                analysis_id="abc",
                name="",
                mapping={"question_field": "q"},
            )

    def test_import_request_valid(self):
        from app.schemas.dataset_import import FieldMapping, ImportRequest

        req = ImportRequest(
            analysis_id="abc-123",
            name="My Dataset",
            mapping=FieldMapping(question_field="question", answer_field="answer"),
        )
        assert req.merge_mode == "single"
        assert req.version == "1.0"

    def test_field_mapping_requires_question(self):
        from pydantic import ValidationError

        from app.schemas.dataset_import import FieldMapping

        with pytest.raises(ValidationError):
            FieldMapping()

    def test_analyze_response_structure(self):
        from app.schemas.dataset_import import AnalyzeResponse, FileAnalysisResult, SuggestedMappingResponse

        resp = AnalyzeResponse(
            analysis_id="abc",
            files=[FileAnalysisResult(filename="test.csv", format="csv", total_rows=5)],
            merged_fields=["question", "answer"],
            suggested_mapping=SuggestedMappingResponse(
                question_field="question", answer_field="answer", confidence=0.95
            ),
            total_items=5,
        )
        assert resp.analysis_id == "abc"
        assert len(resp.files) == 1
