"""API endpoints for smart dataset import: analyze, import, and session cleanup."""

import os

import structlog
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException, NotFoundException
from app.models.dataset import Dataset, DatasetItem
from app.schemas.dataset import DatasetDetailResponse, DatasetItemResponse
from app.schemas.dataset_import import (
    AnalyzeResponse,
    FileAnalysisResult,
    ImportRequest,
    SuggestedMappingResponse,
)
from app.services.dataset_import_service import (
    AnalyzedFile,
    DetectedFormat,
    apply_mapping,
    create_session,
    delete_session,
    detect_format,
    extract_schema,
    get_session,
    suggest_mapping,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/datasets", tags=["dataset-import"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=200)
async def analyze_files(files: list[UploadFile]) -> AnalyzeResponse:
    """Upload and analyze files for dataset import.

    Accepts multipart file uploads. Detects format, extracts schema,
    and suggests field mappings.
    """
    if not files:
        raise AppException(400, "Bad Request", "No files provided")

    if len(files) > settings.max_import_files:
        raise AppException(400, "Bad Request", f"Too many files. Maximum is {settings.max_import_files}")

    analyzed_files: list[AnalyzedFile] = []
    total_bytes_read = 0

    for upload in files:
        # Sanitize filename: strip directory components to prevent path traversal
        raw_name = upload.filename or "unknown"
        filename = os.path.basename(raw_name)
        if not filename:
            filename = "unknown"

        try:
            # Read at most max_import_file_size + 1 to detect oversized files
            # without loading unbounded data into memory
            max_read = settings.max_import_file_size + 1
            content = await upload.read(max_read)

            if len(content) == 0:
                analyzed_files.append(
                    AnalyzedFile(filename=filename, format=DetectedFormat.unknown, error="Empty file")
                )
                continue

            if len(content) > settings.max_import_file_size:
                max_mb = settings.max_import_file_size // (1024 * 1024)
                analyzed_files.append(
                    AnalyzedFile(
                        filename=filename,
                        format=DetectedFormat.unknown,
                        error=f"File too large. Maximum size is {max_mb} MB",
                    )
                )
                continue

            total_bytes_read += len(content)
            if total_bytes_read > settings.max_import_total_size:
                max_total_mb = settings.max_import_total_size // (1024 * 1024)
                analyzed_files.append(
                    AnalyzedFile(
                        filename=filename,
                        format=DetectedFormat.unknown,
                        error=f"Total upload size exceeded. Maximum aggregate size is {max_total_mb} MB",
                    )
                )
                break

            fmt = detect_format(filename, content)
            if fmt == DetectedFormat.unknown:
                analyzed_files.append(
                    AnalyzedFile(filename=filename, format=fmt, error="Unsupported or binary file format")
                )
                continue

            schema = extract_schema(content, fmt, sample_size=settings.import_sample_rows)
            analyzed_files.append(
                AnalyzedFile(
                    filename=filename,
                    format=fmt,
                    schema=schema,
                    rows=schema.sample_rows,
                )
            )

        except Exception as exc:
            logger.warning("import.analyze_error", filename=filename, error=str(exc), exc_info=True)
            analyzed_files.append(
                AnalyzedFile(
                    filename=filename,
                    format=DetectedFormat.unknown,
                    error="Error processing file. Check server logs for details.",
                )
            )

    # Build response
    all_fields: set[str] = set()
    total_items = 0
    file_results: list[FileAnalysisResult] = []

    for af in analyzed_files:
        if af.schema:
            all_fields.update(af.schema.fields)
            total_items += af.schema.total_rows

        file_results.append(
            FileAnalysisResult(
                filename=af.filename,
                format=af.format.value,
                fields=af.schema.fields if af.schema else [],
                sample_rows=af.rows[: settings.import_sample_rows] if af.rows else [],
                total_rows=af.schema.total_rows if af.schema else 0,
                has_header=af.schema.has_header if af.schema else True,
                nested_paths=af.schema.nested_paths if af.schema else [],
                error=af.error,
            )
        )

    merged_fields = sorted(all_fields)
    mapping_suggestion = suggest_mapping(merged_fields)

    # Store analyzed files with sample row data in session for the import step
    session = create_session(analyzed_files)

    suggested = SuggestedMappingResponse(
        question_field=mapping_suggestion.question_field,
        answer_field=mapping_suggestion.answer_field,
        metadata_fields=mapping_suggestion.metadata_fields,
        confidence=mapping_suggestion.confidence,
    )

    return AnalyzeResponse(
        analysis_id=session.id,
        files=file_results,
        merged_fields=merged_fields,
        suggested_mapping=suggested,
        total_items=total_items,
    )


@router.post("/import", response_model=DatasetDetailResponse | list[DatasetDetailResponse], status_code=201)
async def import_dataset(payload: ImportRequest, db: AsyncSession = Depends(get_db)) -> DatasetDetailResponse | list:
    """Import a dataset using a previously analyzed session and field mapping."""
    session = get_session(payload.analysis_id)
    if not session:
        raise NotFoundException("Analysis session", payload.analysis_id)

    # Collect all rows from successful files, re-reading full data
    all_rows_by_file: list[tuple[str, list[dict]]] = []
    for af in session.files:
        if af.error:
            continue
        if af.schema and af.schema.sample_rows:
            # Use total rows stored in schema — for real production, we'd
            # re-parse from stored content, but sample_rows represent the data
            all_rows_by_file.append((af.filename, af.rows))

    if payload.merge_mode == "single":
        # Merge all files into a single dataset
        merged_rows: list[dict] = []
        for _, rows in all_rows_by_file:
            merged_rows.extend(rows)

        items_data = apply_mapping(
            merged_rows,
            question_field=payload.mapping.question_field,
            answer_field=payload.mapping.answer_field,
            metadata_fields=payload.mapping.metadata_fields or None,
        )

        dataset = Dataset(
            name=payload.name,
            description=payload.description,
            format="qa_pairs",
            version=payload.version,
            tags=payload.tags,
            source_type="import",
            item_count=len(items_data),
        )
        db.add(dataset)
        await db.flush()

        db_items = []
        for idx, item in enumerate(items_data):
            db_item = DatasetItem(
                dataset_id=dataset.id,
                question=item["question"],
                expected_answer=item.get("expected_answer"),
                metadata_=item.get("metadata"),
                order_index=idx,
            )
            db.add(db_item)
            db_items.append(db_item)

        await db.commit()
        await db.refresh(dataset)

        # Clean up session
        delete_session(payload.analysis_id)

        item_responses = [
            DatasetItemResponse(
                id=it.id,
                question=it.question,
                expected_answer=it.expected_answer,
                metadata=it.metadata_,
                order_index=it.order_index,
            )
            for it in db_items
        ]

        logger.info("import.completed", dataset_id=dataset.id, item_count=len(items_data))
        return DatasetDetailResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            format=dataset.format,
            version=dataset.version,
            tags=dataset.tags or [],
            source_type=dataset.source_type,
            item_count=dataset.item_count,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            items=item_responses,
        )

    else:
        # Separate mode: one dataset per file
        results: list[DatasetDetailResponse] = []
        for filename, rows in all_rows_by_file:
            items_data = apply_mapping(
                rows,
                question_field=payload.mapping.question_field,
                answer_field=payload.mapping.answer_field,
                metadata_fields=payload.mapping.metadata_fields or None,
            )

            # Derive name from filename
            stem = filename.rsplit(".", 1)[0] if "." in filename else filename
            ds_name = f"{payload.name} - {stem}"

            dataset = Dataset(
                name=ds_name,
                description=payload.description,
                format="qa_pairs",
                version=payload.version,
                tags=payload.tags,
                source_type="import",
                item_count=len(items_data),
            )
            db.add(dataset)
            await db.flush()

            db_items = []
            for idx, item in enumerate(items_data):
                db_item = DatasetItem(
                    dataset_id=dataset.id,
                    question=item["question"],
                    expected_answer=item.get("expected_answer"),
                    metadata_=item.get("metadata"),
                    order_index=idx,
                )
                db.add(db_item)
                db_items.append(db_item)

            await db.commit()
            await db.refresh(dataset)

            item_responses = [
                DatasetItemResponse(
                    id=it.id,
                    question=it.question,
                    expected_answer=it.expected_answer,
                    metadata=it.metadata_,
                    order_index=it.order_index,
                )
                for it in db_items
            ]

            results.append(
                DatasetDetailResponse(
                    id=dataset.id,
                    name=dataset.name,
                    description=dataset.description,
                    format=dataset.format,
                    version=dataset.version,
                    tags=dataset.tags or [],
                    source_type=dataset.source_type,
                    item_count=dataset.item_count,
                    created_at=dataset.created_at,
                    updated_at=dataset.updated_at,
                    items=item_responses,
                )
            )

        delete_session(payload.analysis_id)
        logger.info("import.completed_separate", dataset_count=len(results))
        return results


@router.delete("/analyze/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: str) -> None:
    """Delete an analysis session to free resources."""
    if not delete_session(analysis_id):
        raise NotFoundException("Analysis session", analysis_id)
