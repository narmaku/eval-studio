import contextlib
import os
import re
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by stripping path components and unsafe characters.

    Args:
        filename: The original filename to sanitize.

    Returns:
        A safe filename string.

    Raises:
        ValueError: If the filename is empty or results in an empty string after sanitization.
    """
    if not filename:
        raise ValueError("Filename must not be empty")

    # Strip any path components (forward and backslash)
    name = filename.replace("\\", "/")

    # Reject path traversal attempts before stripping path components
    parts = name.split("/")
    if any(part == ".." for part in parts):
        raise ValueError("Filename must not contain '..'")

    name = parts[-1]

    # Allow only alphanumeric, hyphens, underscores, dots, and spaces
    name = re.sub(r"[^\w\-. ]", "_", name)

    # Collapse multiple dots/spaces and strip leading/trailing dots/spaces
    name = re.sub(r"\.{2,}", ".", name)
    name = name.strip(". ")

    if not name:
        raise ValueError("Filename is empty after sanitization")

    # Limit length
    if len(name) > 200:
        stem, _, ext = name.rpartition(".")
        name = stem[: 200 - len(ext) - 1] + "." + ext if ext and stem else name[:200]

    return name


def get_artifact_path(artifact: Artifact, artifacts_dir: str) -> Path:
    """Resolve the full path for an artifact and validate it is within artifacts_dir.

    Args:
        artifact: The Artifact model instance.
        artifacts_dir: The base artifacts directory.

    Returns:
        The resolved absolute Path.

    Raises:
        ValueError: If the resolved path escapes the artifacts directory.
    """
    base = Path(artifacts_dir).resolve()
    full_path = (base / artifact.storage_path).resolve()

    if not str(full_path).startswith(str(base) + os.sep) and full_path != base:
        raise ValueError("Artifact path escapes the artifacts directory")

    return full_path


async def save_artifact(
    db: AsyncSession,
    evaluation_id: str,
    filename: str,
    content: bytes,
    content_type: str,
    artifacts_dir: str,
    description: str | None = None,
) -> Artifact:
    """Save an artifact file to disk and create a DB record.

    Args:
        db: The async database session.
        evaluation_id: The evaluation this artifact belongs to.
        filename: The original filename (will be sanitized).
        content: The file content as bytes.
        content_type: The MIME type of the file.
        artifacts_dir: The base directory for artifact storage.
        description: Optional human-readable description.

    Returns:
        The created Artifact model instance.
    """
    safe_name = sanitize_filename(filename)
    unique_prefix = uuid.uuid4().hex[:8]
    relative_path = f"{evaluation_id}/{unique_prefix}_{safe_name}"

    base = Path(artifacts_dir).resolve()
    full_path = base / relative_path

    # Validate path stays within artifacts_dir
    if not str(full_path.resolve()).startswith(str(base)):
        raise ValueError("Generated storage path escapes the artifacts directory")

    # Create parent directory
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Write atomically (temp file + rename)
    fd, tmp_path = tempfile.mkstemp(dir=str(full_path.parent))
    fd_closed = False
    try:
        os.write(fd, content)
        os.close(fd)
        fd_closed = True
        os.rename(tmp_path, str(full_path))
    except Exception:
        if not fd_closed:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    artifact = Artifact(
        evaluation_id=evaluation_id,
        filename=safe_name,
        content_type=content_type,
        size_bytes=len(content),
        storage_path=relative_path,
        description=description,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


async def delete_artifact_file(artifact: Artifact, artifacts_dir: str) -> None:
    """Delete the artifact file from disk.

    Args:
        artifact: The Artifact model instance.
        artifacts_dir: The base artifacts directory.
    """
    with contextlib.suppress(ValueError):
        full_path = get_artifact_path(artifact, artifacts_dir)
        if full_path.exists():
            full_path.unlink()
            # Try to remove empty parent directories
            with contextlib.suppress(OSError):
                full_path.parent.rmdir()
