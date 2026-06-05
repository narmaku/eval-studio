import pytest

from app.models.artifact import Artifact
from app.services.artifact_service import get_artifact_path, sanitize_filename


class TestSanitizeFilename:
    """Tests for the sanitize_filename function."""

    def test_simple_filename(self):
        assert sanitize_filename("report.json") == "report.json"

    def test_filename_with_spaces(self):
        assert sanitize_filename("my report.txt") == "my report.txt"

    def test_strips_path_components_forward_slash(self):
        assert sanitize_filename("/etc/passwd") == "passwd"

    def test_strips_path_components_backslash(self):
        assert sanitize_filename("C:\\Users\\file.txt") == "file.txt"

    def test_rejects_dotdot(self):
        with pytest.raises(ValueError, match="must not contain"):
            sanitize_filename("../../../etc/passwd")

    def test_collapses_dotdot_in_name(self):
        """Consecutive dots in a filename (not path traversal) are collapsed."""
        result = sanitize_filename("foo..bar..baz")
        assert result == "foo.bar.baz"

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="must not be empty"):
            sanitize_filename("")

    def test_replaces_special_characters(self):
        result = sanitize_filename("file<name>:with|special?chars.txt")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "|" not in result
        assert "?" not in result
        assert result.endswith(".txt")

    def test_strips_leading_trailing_dots(self):
        result = sanitize_filename("...hidden_file...")
        assert result == "hidden_file"

    def test_long_filename_truncated(self):
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_long_filename_preserves_extension(self):
        long_name = "a" * 300 + ".json"
        result = sanitize_filename(long_name)
        assert result.endswith(".json")
        assert len(result) <= 200

    def test_rejects_only_dots_and_spaces(self):
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_filename("... ...")

    def test_mixed_path_separators(self):
        assert sanitize_filename("foo/bar\\baz.txt") == "baz.txt"

    def test_preserves_underscores_and_hyphens(self):
        assert sanitize_filename("my-file_v2.txt") == "my-file_v2.txt"


class TestGetArtifactPath:
    """Tests for the get_artifact_path function."""

    def test_valid_path(self, tmp_path):
        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=100,
            storage_path="eval-1/abc_report.json",
        )
        result = get_artifact_path(artifact, str(tmp_path))
        assert str(result).startswith(str(tmp_path.resolve()))
        assert result.name == "abc_report.json"

    def test_path_traversal_rejected(self, tmp_path):
        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=100,
            storage_path="../../etc/passwd",
        )
        with pytest.raises(ValueError, match="escapes"):
            get_artifact_path(artifact, str(tmp_path))

    def test_absolute_storage_path_rejected(self, tmp_path):
        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=100,
            storage_path="/etc/passwd",
        )
        # On Linux, /etc/passwd resolved won't start with tmp_path
        with pytest.raises(ValueError, match="escapes"):
            get_artifact_path(artifact, str(tmp_path))
