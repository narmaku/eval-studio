"""Smart dataset import service with format detection, schema extraction, and field mapping."""

import csv
import io
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

# Session TTL in seconds (15 minutes)
SESSION_TTL = 15 * 60


class DetectedFormat(StrEnum):
    """Detected file format for import."""

    yaml = "yaml"
    jsonl = "jsonl"
    json = "json"
    csv = "csv"
    tsv = "tsv"
    unknown = "unknown"


@dataclass
class FileSchema:
    """Extracted schema from a parsed file."""

    fields: list[str]
    sample_rows: list[dict[str, Any]]
    total_rows: int
    has_header: bool = True
    nested_paths: list[str] = field(default_factory=list)


@dataclass
class SuggestedMapping:
    """A suggested mapping of source fields to DatasetItemCreate fields."""

    question_field: str | None
    answer_field: str | None
    metadata_fields: list[str]
    confidence: float


@dataclass
class AnalyzedFile:
    """Result of analyzing a single file."""

    filename: str
    format: DetectedFormat
    schema: FileSchema | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class AnalysisSession:
    """In-memory session for a dataset import analysis."""

    id: str
    files: list[AnalyzedFile]
    created_at: float


# Module-level session store
_analysis_sessions: dict[str, AnalysisSession] = {}

# Patterns for field mapping — ordered by priority
_QUESTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^question$", re.IGNORECASE),
    re.compile(r"^input$", re.IGNORECASE),
    re.compile(r"^prompt$", re.IGNORECASE),
    re.compile(r"^instruction$", re.IGNORECASE),
    re.compile(r"^query$", re.IGNORECASE),
    re.compile(r"^context$", re.IGNORECASE),
    re.compile(r"^text$", re.IGNORECASE),
]

_ANSWER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(expected_?)?answer$", re.IGNORECASE),
    re.compile(r"^(expected_?)?response$", re.IGNORECASE),
    re.compile(r"^output$", re.IGNORECASE),
    re.compile(r"^response$", re.IGNORECASE),
    re.compile(r"^target$", re.IGNORECASE),
    re.compile(r"^completion$", re.IGNORECASE),
    re.compile(r"^answers\.text\[0\]$", re.IGNORECASE),
    re.compile(r"^expected$", re.IGNORECASE),
]

# Binary content detection bytes
_BINARY_CHECK_SIZE = 8192


def _is_binary(content: bytes) -> bool:
    """Check if content appears to be binary (non-text)."""
    check = content[:_BINARY_CHECK_SIZE]
    # Check for null bytes — strong indicator of binary
    if b"\x00" in check:
        return True
    # Check for high ratio of non-text bytes
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
    non_text = sum(1 for byte in check if byte not in text_chars)
    return non_text / max(len(check), 1) > 0.3


def detect_format(filename: str, content: bytes) -> DetectedFormat:
    """Detect file format from extension and content sniffing.

    Args:
        filename: Original filename with extension.
        content: Raw file content bytes.

    Returns:
        Detected format enum value.
    """
    if _is_binary(content):
        return DetectedFormat.unknown

    # Extension-based detection
    lower = filename.lower()
    if lower.endswith((".yaml", ".yml")):
        return DetectedFormat.yaml
    if lower.endswith(".jsonl"):
        return DetectedFormat.jsonl
    if lower.endswith(".json"):
        return DetectedFormat.json
    if lower.endswith(".csv"):
        return DetectedFormat.csv
    if lower.endswith(".tsv"):
        return DetectedFormat.tsv

    # Content sniffing fallback
    text = content.decode("utf-8", errors="replace").strip()
    if not text:
        return DetectedFormat.unknown

    # Try JSON array
    if text.startswith("["):
        try:
            json.loads(text)
            return DetectedFormat.json
        except json.JSONDecodeError:
            pass

    # Try JSON object
    if text.startswith("{"):
        # Could be JSONL (multiple lines of JSON objects)
        lines = text.split("\n")
        valid_json_lines = 0
        for line in lines[:5]:
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                valid_json_lines += 1
            except json.JSONDecodeError:
                break
        if valid_json_lines > 1:
            return DetectedFormat.jsonl
        if valid_json_lines == 1 and len(lines) <= 2:
            return DetectedFormat.json

    # Try YAML
    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, (list, dict)):
            return DetectedFormat.yaml
    except yaml.YAMLError:
        pass

    # Try TSV (tabs in first line)
    first_line = text.split("\n")[0]
    if "\t" in first_line:
        return DetectedFormat.tsv

    # Try CSV (commas in first line, at least 2 fields)
    if "," in first_line:
        return DetectedFormat.csv

    return DetectedFormat.unknown


_MAX_FLATTEN_DEPTH = 20


def _flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = ".", _depth: int = 0) -> dict[str, Any]:
    """Flatten a nested dictionary into dot-notation keys.

    Args:
        d: Dictionary to flatten.
        parent_key: Prefix for keys (used in recursion).
        sep: Separator between nested key segments.
        _depth: Current recursion depth (internal).

    Returns:
        Flattened dictionary with dot-notation keys.
    """
    if _depth >= _MAX_FLATTEN_DEPTH:
        # Stop recursion at max depth to prevent stack overflow on malicious input
        return {parent_key: d} if parent_key else {"_truncated": d}

    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep, _depth + 1).items())
        elif isinstance(v, list) and v:
            if isinstance(v[0], dict):
                items.extend(_flatten_dict(v[0], f"{new_key}[0]", sep, _depth + 1).items())
            elif isinstance(v[0], str):
                items.append((f"{new_key}[0]", v[0]))
            else:
                items.append((new_key, v))
        else:
            items.append((new_key, v))
    return dict(items)


def _collect_fields(rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Collect all fields from rows, identifying nested paths.

    Returns:
        Tuple of (all_fields, nested_paths).
    """
    all_fields: set[str] = set()
    nested_paths: set[str] = set()
    for row in rows:
        flat = _flatten_dict(row)
        for key in flat:
            all_fields.add(key)
            if "." in key or "[" in key:
                nested_paths.add(key)
    return sorted(all_fields), sorted(nested_paths)


def extract_schema(content: bytes, fmt: DetectedFormat, sample_size: int = 20) -> FileSchema:
    """Extract schema information from file content.

    Args:
        content: Raw file content bytes.
        fmt: Detected format of the file.
        sample_size: Maximum number of sample rows to include.

    Returns:
        FileSchema with field info and sample data.

    Raises:
        ValueError: If content cannot be parsed in the given format.
    """
    text = content.decode("utf-8", errors="replace")

    if fmt == DetectedFormat.yaml:
        return _extract_yaml_schema(text, sample_size)
    elif fmt == DetectedFormat.jsonl:
        return _extract_jsonl_schema(text, sample_size)
    elif fmt == DetectedFormat.json:
        return _extract_json_schema(text, sample_size)
    elif fmt == DetectedFormat.csv:
        return _extract_csv_schema(text, sample_size, delimiter=",")
    elif fmt == DetectedFormat.tsv:
        return _extract_csv_schema(text, sample_size, delimiter="\t")
    else:
        raise ValueError(f"Cannot extract schema for format: {fmt}")


def _extract_yaml_schema(text: str, sample_size: int) -> FileSchema:
    """Extract schema from YAML content."""
    parsed = yaml.safe_load(text)
    if isinstance(parsed, list):
        rows = [_flatten_dict(item) if isinstance(item, dict) else {"value": item} for item in parsed]
    elif isinstance(parsed, dict):
        # Could be a nested structure like SQuAD with a data key
        # Look for the first list-valued key
        list_key = None
        for k, v in parsed.items():
            if isinstance(v, list) and v:
                list_key = k
                break
        if list_key:
            rows = [_flatten_dict(item) if isinstance(item, dict) else {"value": item} for item in parsed[list_key]]
        else:
            rows = [_flatten_dict(parsed)]
    else:
        rows = [{"value": parsed}]

    fields, nested_paths = _collect_fields(rows[:sample_size] if len(rows) > sample_size else rows)
    return FileSchema(
        fields=fields,
        sample_rows=rows[:sample_size],
        total_rows=len(rows),
        has_header=True,
        nested_paths=nested_paths,
    )


def _extract_jsonl_schema(text: str, sample_size: int) -> FileSchema:
    """Extract schema from JSONL (JSON Lines) content."""
    rows: list[dict[str, Any]] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                rows.append(_flatten_dict(parsed))
            else:
                rows.append({"value": parsed})
        except json.JSONDecodeError:
            continue

    fields, nested_paths = _collect_fields(rows[:sample_size] if len(rows) > sample_size else rows)
    return FileSchema(
        fields=fields,
        sample_rows=rows[:sample_size],
        total_rows=len(rows),
        has_header=True,
        nested_paths=nested_paths,
    )


def _extract_json_schema(text: str, sample_size: int) -> FileSchema:
    """Extract schema from JSON content."""
    parsed = json.loads(text)
    if isinstance(parsed, list):
        rows = [_flatten_dict(item) if isinstance(item, dict) else {"value": item} for item in parsed]
    elif isinstance(parsed, dict):
        # Look for nested arrays (like SQuAD format)
        list_key = None
        for k, v in parsed.items():
            if isinstance(v, list) and v:
                list_key = k
                break
        if list_key:
            rows = [_flatten_dict(item) if isinstance(item, dict) else {"value": item} for item in parsed[list_key]]
        else:
            rows = [_flatten_dict(parsed)]
    else:
        rows = [{"value": parsed}]

    fields, nested_paths = _collect_fields(rows[:sample_size] if len(rows) > sample_size else rows)
    return FileSchema(
        fields=fields,
        sample_rows=rows[:sample_size],
        total_rows=len(rows),
        has_header=True,
        nested_paths=nested_paths,
    )


def _extract_csv_schema(text: str, sample_size: int, delimiter: str = ",") -> FileSchema:
    """Extract schema from CSV/TSV content."""
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows: list[dict[str, Any]] = []
    for row in reader:
        rows.append(dict(row))

    has_header = bool(reader.fieldnames)
    fields = list(reader.fieldnames) if reader.fieldnames else []

    return FileSchema(
        fields=sorted(fields),
        sample_rows=rows[:sample_size],
        total_rows=len(rows),
        has_header=has_header,
        nested_paths=[],
    )


def _leaf_name(field_path: str) -> str:
    """Extract the leaf field name from a nested path like 'turns[0].query' → 'query'."""
    parts = re.split(r"\.|\[", field_path)
    for part in reversed(parts):
        cleaned = part.rstrip("]")
        if cleaned and not cleaned.isdigit():
            return cleaned
    return field_path


def suggest_mapping(fields: list[str]) -> SuggestedMapping:
    """Suggest field mappings based on pattern matching.

    Args:
        fields: List of field names from the source data.

    Returns:
        SuggestedMapping with best-guess question/answer fields and confidence.
    """
    question_field: str | None = None
    answer_field: str | None = None
    question_confidence = 0.0
    answer_confidence = 0.0

    for f in fields:
        leaf = _leaf_name(f)
        for i, pattern in enumerate(_QUESTION_PATTERNS):
            if pattern.match(f) or pattern.match(leaf):
                score = 1.0 - (i * 0.1)
                if f != leaf:
                    score *= 0.95
                if score > question_confidence:
                    question_field = f
                    question_confidence = score
                break

        for i, pattern in enumerate(_ANSWER_PATTERNS):
            if pattern.match(f) or pattern.match(leaf):
                score = 1.0 - (i * 0.1)
                if f != leaf:
                    score *= 0.95
                if score > answer_confidence:
                    answer_field = f
                    answer_confidence = score
                break

    # Metadata = everything that's not question or answer
    metadata_fields = [f for f in fields if f != question_field and f != answer_field]

    # Overall confidence is the average of question and answer confidence
    if question_field and answer_field:
        confidence = (question_confidence + answer_confidence) / 2.0
    elif question_field:
        confidence = question_confidence * 0.5  # Half confidence without answer
    else:
        confidence = 0.0

    return SuggestedMapping(
        question_field=question_field,
        answer_field=answer_field,
        metadata_fields=metadata_fields,
        confidence=round(confidence, 2),
    )


def _resolve_nested(row: dict[str, Any], field_path: str) -> Any:
    """Resolve a potentially nested field path from a flattened or nested row.

    Supports dot notation ('a.b') and array indexing ('a.b[0]').
    First checks if the flattened key exists directly, then traverses.
    """
    # Direct lookup first (already flattened)
    if field_path in row:
        return row[field_path]

    # Traverse nested structure
    parts = re.split(r"\.|(?=\[)", field_path)
    current: Any = row
    for part in parts:
        if not part:
            continue
        # Handle array index like [0]
        idx_match = re.match(r"\[(\d+)\]", part)
        if idx_match:
            idx = int(idx_match.group(1))
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return None
        else:
            return None
    return current


def apply_mapping(
    rows: list[dict[str, Any]],
    question_field: str,
    answer_field: str | None = None,
    metadata_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Apply field mapping to transform rows into DatasetItemCreate-compatible dicts.

    Args:
        rows: Source data rows.
        question_field: Field to use as 'question'.
        answer_field: Field to use as 'expected_answer' (optional).
        metadata_fields: Fields to include in metadata (optional; if None, all unmapped fields).

    Returns:
        List of dicts with 'question', 'expected_answer', and 'metadata' keys.
    """
    result: list[dict[str, Any]] = []
    mapped_fields = {question_field}
    if answer_field:
        mapped_fields.add(answer_field)

    for row in rows:
        question = _resolve_nested(row, question_field)
        if question is None:
            continue  # Skip rows without a question field

        # Coerce to string
        question = str(question)

        expected_answer: str | None = None
        if answer_field:
            answer_val = _resolve_nested(row, answer_field)
            if answer_val is not None:
                expected_answer = str(answer_val)

        # Build metadata from unmapped fields
        if metadata_fields is not None:
            metadata = {}
            for f in metadata_fields:
                val = _resolve_nested(row, f)
                if val is not None:
                    metadata[f] = val
        else:
            metadata = {k: v for k, v in row.items() if k not in mapped_fields}

        item: dict[str, Any] = {
            "question": question,
            "expected_answer": expected_answer,
        }
        if metadata:
            item["metadata"] = metadata

        result.append(item)

    return result


def _cleanup_expired_sessions() -> None:
    """Remove expired sessions from the in-memory store."""
    now = time.time()
    expired = [sid for sid, session in _analysis_sessions.items() if now - session.created_at > SESSION_TTL]
    for sid in expired:
        del _analysis_sessions[sid]


def create_session(files: list[AnalyzedFile]) -> AnalysisSession:
    """Create a new analysis session and store it.

    Args:
        files: List of analyzed file results.

    Returns:
        The created AnalysisSession.
    """
    _cleanup_expired_sessions()
    session_id = str(uuid.uuid4())
    session = AnalysisSession(id=session_id, files=files, created_at=time.time())
    _analysis_sessions[session_id] = session
    logger.info("import_session.created", session_id=session_id, file_count=len(files))
    return session


def get_session(session_id: str) -> AnalysisSession | None:
    """Retrieve an analysis session by ID, or None if not found/expired.

    Args:
        session_id: The session UUID.

    Returns:
        The AnalysisSession, or None.
    """
    _cleanup_expired_sessions()
    return _analysis_sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    """Delete an analysis session.

    Args:
        session_id: The session UUID.

    Returns:
        True if the session was deleted, False if not found.
    """
    if session_id in _analysis_sessions:
        del _analysis_sessions[session_id]
        logger.info("import_session.deleted", session_id=session_id)
        return True
    return False
