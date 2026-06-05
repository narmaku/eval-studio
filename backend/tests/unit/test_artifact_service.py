import os

import pytest

from app.models.artifact import Artifact
from app.services.artifact_service import (
    delete_artifact_file,
    get_artifact_path,
    sanitize_filename,
    save_artifact,
)


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

    def test_null_bytes_replaced(self):
        """Null bytes in filenames are replaced with underscores."""
        result = sanitize_filename("file\x00name.txt")
        assert "\x00" not in result
        assert result.endswith(".txt")

    def test_only_special_characters_replaced(self):
        """A filename of only special characters gets all chars replaced with underscores."""
        result = sanitize_filename("@#$%^&*()")
        # All special chars are replaced with _ by the regex, resulting in a valid name
        assert all(c == "_" for c in result)
        assert len(result) > 0

    def test_dotdot_in_middle_of_path(self):
        """Path traversal via embedded .. between normal components is rejected."""
        with pytest.raises(ValueError, match="must not contain"):
            sanitize_filename("valid/../../../etc/passwd")

    def test_whitespace_only_filename(self):
        """A filename of only whitespace is rejected."""
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_filename("   ")

    def test_filename_exactly_200_chars(self):
        """Filename at the length limit should not be truncated."""
        name = "a" * 196 + ".txt"
        assert len(name) == 200
        result = sanitize_filename(name)
        assert result == name

    def test_filename_201_chars_truncated(self):
        """Filename at 201 chars should be truncated to at most 200."""
        name = "a" * 197 + ".txt"
        assert len(name) == 201
        result = sanitize_filename(name)
        assert len(result) <= 200
        assert result.endswith(".txt")

    def test_long_filename_without_extension(self):
        """Long filename without extension is truncated to 200 chars."""
        name = "a" * 250
        result = sanitize_filename(name)
        assert len(result) <= 200

    def test_encoded_path_traversal(self):
        """Percent-encoded characters are replaced, not interpreted as path traversal."""
        result = sanitize_filename("%2e%2e/%2e%2e/etc/passwd")
        # The % chars get replaced with _, slashes strip to last component
        assert ".." not in result
        assert "/" not in result

    def test_tab_and_newline_in_filename(self):
        """Control characters like tab and newline are replaced."""
        result = sanitize_filename("file\tname\n.txt")
        assert "\t" not in result
        assert "\n" not in result


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

    def test_symlink_escape_rejected(self, tmp_path):
        """A storage_path pointing through a symlink that escapes artifacts_dir is rejected."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        # Create a symlink inside artifacts_dir that points outside
        escape_link = artifacts_dir / "escape"
        escape_link.symlink_to("/tmp")

        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=100,
            storage_path="escape/secret.txt",
        )
        with pytest.raises(ValueError, match="escapes"):
            get_artifact_path(artifact, str(artifacts_dir))

    def test_nested_valid_path(self, tmp_path):
        """Deeply nested but valid paths should resolve correctly."""
        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=100,
            storage_path="eval-1/sub/dir/abc_report.json",
        )
        result = get_artifact_path(artifact, str(tmp_path))
        assert str(result).startswith(str(tmp_path.resolve()))
        assert result.name == "abc_report.json"


class TestSaveArtifact:
    """Tests for the save_artifact function."""

    @pytest.mark.asyncio
    async def test_saves_file_to_disk(self, db_session, tmp_path):
        """save_artifact writes file content to the artifacts directory."""
        from pathlib import Path

        from app.models.evaluation import Evaluation

        evaluation = Evaluation(name="test", mode="qa", status="completed", config={})
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        artifacts_dir = str(tmp_path / "artifacts")
        content = b"hello world"
        artifact = await save_artifact(
            db=db_session,
            evaluation_id=evaluation.id,
            filename="output.txt",
            content=content,
            content_type="text/plain",
            artifacts_dir=artifacts_dir,
        )

        full_path = Path(artifacts_dir) / artifact.storage_path
        assert full_path.exists()
        assert full_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_creates_db_record(self, db_session, tmp_path):
        """save_artifact creates an Artifact record in the database."""
        from sqlalchemy import select

        from app.models.evaluation import Evaluation

        evaluation = Evaluation(name="test", mode="qa", status="completed", config={})
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        artifacts_dir = str(tmp_path / "artifacts")
        artifact = await save_artifact(
            db=db_session,
            evaluation_id=evaluation.id,
            filename="data.json",
            content=b'{"key": "value"}',
            content_type="application/json",
            artifacts_dir=artifacts_dir,
            description="Test data file",
        )

        result = await db_session.execute(select(Artifact).where(Artifact.id == artifact.id))
        record = result.scalar_one()
        assert record.filename == "data.json"
        assert record.content_type == "application/json"
        assert record.size_bytes == len(b'{"key": "value"}')
        assert record.description == "Test data file"
        assert record.evaluation_id == evaluation.id

    @pytest.mark.asyncio
    async def test_rejects_traversal_filename(self, db_session, tmp_path):
        """save_artifact rejects filenames with path traversal."""
        from app.models.evaluation import Evaluation

        evaluation = Evaluation(name="test", mode="qa", status="completed", config={})
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        artifacts_dir = str(tmp_path / "artifacts")
        with pytest.raises(ValueError, match="must not contain"):
            await save_artifact(
                db=db_session,
                evaluation_id=evaluation.id,
                filename="../../../etc/passwd",
                content=b"malicious",
                content_type="text/plain",
                artifacts_dir=artifacts_dir,
            )

    @pytest.mark.asyncio
    async def test_zero_byte_file(self, db_session, tmp_path):
        """save_artifact handles zero-byte files correctly."""
        from pathlib import Path

        from app.models.evaluation import Evaluation

        evaluation = Evaluation(name="test", mode="qa", status="completed", config={})
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        artifacts_dir = str(tmp_path / "artifacts")
        artifact = await save_artifact(
            db=db_session,
            evaluation_id=evaluation.id,
            filename="empty.txt",
            content=b"",
            content_type="text/plain",
            artifacts_dir=artifacts_dir,
        )

        assert artifact.size_bytes == 0
        full_path = Path(artifacts_dir) / artifact.storage_path
        assert full_path.exists()
        assert full_path.read_bytes() == b""

    @pytest.mark.asyncio
    async def test_unique_prefix_prevents_collisions(self, db_session, tmp_path):
        """Saving two artifacts with the same filename creates different storage paths."""
        from app.models.evaluation import Evaluation

        evaluation = Evaluation(name="test", mode="qa", status="completed", config={})
        db_session.add(evaluation)
        await db_session.commit()
        await db_session.refresh(evaluation)

        artifacts_dir = str(tmp_path / "artifacts")
        a1 = await save_artifact(
            db=db_session,
            evaluation_id=evaluation.id,
            filename="report.json",
            content=b'{"v": 1}',
            content_type="application/json",
            artifacts_dir=artifacts_dir,
        )
        a2 = await save_artifact(
            db=db_session,
            evaluation_id=evaluation.id,
            filename="report.json",
            content=b'{"v": 2}',
            content_type="application/json",
            artifacts_dir=artifacts_dir,
        )

        assert a1.storage_path != a2.storage_path
        assert a1.id != a2.id


class TestDeleteArtifactFile:
    """Tests for the delete_artifact_file function."""

    @pytest.mark.asyncio
    async def test_deletes_existing_file(self, tmp_path):
        """delete_artifact_file removes the file from disk."""
        artifacts_dir = tmp_path / "artifacts"
        eval_dir = artifacts_dir / "eval-1"
        eval_dir.mkdir(parents=True)
        file_path = eval_dir / "abc_report.json"
        file_path.write_text("content")

        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=7,
            storage_path="eval-1/abc_report.json",
        )

        await delete_artifact_file(artifact, str(artifacts_dir))
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_removes_empty_parent_directory(self, tmp_path):
        """delete_artifact_file removes the empty parent directory."""
        artifacts_dir = tmp_path / "artifacts"
        eval_dir = artifacts_dir / "eval-1"
        eval_dir.mkdir(parents=True)
        file_path = eval_dir / "abc_report.json"
        file_path.write_text("content")

        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=7,
            storage_path="eval-1/abc_report.json",
        )

        await delete_artifact_file(artifact, str(artifacts_dir))
        assert not eval_dir.exists()

    @pytest.mark.asyncio
    async def test_keeps_non_empty_parent_directory(self, tmp_path):
        """delete_artifact_file keeps the parent dir if it contains other files."""
        artifacts_dir = tmp_path / "artifacts"
        eval_dir = artifacts_dir / "eval-1"
        eval_dir.mkdir(parents=True)
        file_to_delete = eval_dir / "abc_report.json"
        file_to_delete.write_text("content")
        other_file = eval_dir / "other.txt"
        other_file.write_text("keep me")

        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=7,
            storage_path="eval-1/abc_report.json",
        )

        await delete_artifact_file(artifact, str(artifacts_dir))
        assert not file_to_delete.exists()
        assert other_file.exists()
        assert eval_dir.exists()

    @pytest.mark.asyncio
    async def test_missing_file_does_not_raise(self, tmp_path):
        """delete_artifact_file does not raise if the file does not exist."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=7,
            storage_path="eval-1/missing_report.json",
        )

        # Should not raise
        await delete_artifact_file(artifact, str(artifacts_dir))

    @pytest.mark.asyncio
    async def test_traversal_storage_path_silently_ignored(self, tmp_path):
        """delete_artifact_file suppresses ValueError from path traversal."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        artifact = Artifact(
            evaluation_id="eval-1",
            filename="report.json",
            content_type="application/json",
            size_bytes=7,
            storage_path="../../etc/passwd",
        )

        # Should not raise -- ValueError is suppressed
        await delete_artifact_file(artifact, str(artifacts_dir))
        # Verify /etc/passwd was not touched
        assert os.path.exists("/etc/passwd")
