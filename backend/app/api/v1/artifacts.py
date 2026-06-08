import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException, NotFoundException
from app.core.security import require_auth
from app.models.artifact import Artifact
from app.schemas.artifact import ArtifactResponse
from app.services.artifact_service import delete_artifact_file, get_artifact_path

logger = structlog.get_logger()

router = APIRouter(prefix="/artifacts", tags=["artifacts"], dependencies=[Depends(require_auth)])

# Maximum size for inline preview (1 MB)
PREVIEW_MAX_SIZE = 1_048_576

# MIME types eligible for inline preview.
# text/html and text/xml are intentionally excluded to prevent stored XSS
# (serving HTML inline would execute embedded scripts in the user's browser).
PREVIEWABLE_TYPES = {"text/plain", "text/csv", "text/markdown", "application/json"}


def _is_previewable(content_type: str) -> bool:
    """Check if a content type is eligible for inline preview."""
    return content_type in PREVIEWABLE_TYPES


@router.get("", response_model=list[ArtifactResponse])
async def list_artifacts(
    evaluation_id: str = Query(..., description="Evaluation ID to list artifacts for"),
    db: AsyncSession = Depends(get_db),
) -> list[ArtifactResponse]:
    """List all artifacts for a given evaluation."""
    query = select(Artifact).where(Artifact.evaluation_id == evaluation_id).order_by(Artifact.created_at.desc())
    result = await db.execute(query)
    artifacts = result.scalars().all()
    logger.info("artifacts.listed", evaluation_id=evaluation_id, count=len(artifacts))
    return [ArtifactResponse.model_validate(a) for a in artifacts]


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """Get artifact metadata by ID."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise NotFoundException("Artifact", artifact_id)
    return ArtifactResponse.model_validate(artifact)


@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Download an artifact file."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise NotFoundException("Artifact", artifact_id)

    try:
        file_path = get_artifact_path(artifact, settings.artifacts_dir)
    except ValueError as e:
        raise AppException(500, "Internal Error", str(e)) from e

    if not file_path.exists():
        raise NotFoundException("Artifact file", artifact_id)

    def iter_file():
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    logger.info("artifact.download", id=artifact_id, filename=artifact.filename)
    return StreamingResponse(
        iter_file(),
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{artifact_id}/preview")
async def preview_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Preview an artifact's content inline (text/JSON only)."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise NotFoundException("Artifact", artifact_id)

    if not _is_previewable(artifact.content_type):
        raise AppException(
            415,
            "Unsupported Media Type",
            f"Preview not available for content type '{artifact.content_type}'",
        )

    if artifact.size_bytes > PREVIEW_MAX_SIZE:
        raise AppException(
            413,
            "Content Too Large",
            f"Artifact is too large for preview ({artifact.size_bytes} bytes, max {PREVIEW_MAX_SIZE})",
        )

    try:
        file_path = get_artifact_path(artifact, settings.artifacts_dir)
    except ValueError as e:
        raise AppException(500, "Internal Error", str(e)) from e

    if not file_path.exists():
        raise NotFoundException("Artifact file", artifact_id)

    content = file_path.read_text(encoding="utf-8", errors="replace")
    logger.info("artifact.preview", id=artifact_id, filename=artifact.filename)
    # Always serve previews as text/plain to prevent stored XSS via HTML/XML content
    return StreamingResponse(
        iter([content]),
        media_type="text/plain",
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an artifact (file + DB record)."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise NotFoundException("Artifact", artifact_id)

    await delete_artifact_file(artifact, settings.artifacts_dir)
    await db.delete(artifact)
    await db.commit()
    logger.info("artifact.deleted", id=artifact_id, filename=artifact.filename)
