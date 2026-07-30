from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.dependencies import (
    get_app_settings,
    get_current_user,
    rate_limit_dependency,
    require_csrf,
)
from app.models.print_job import PrintJob
from app.schemas.jobs import JobResponse
from app.services.cups_service import CUPSService
from app.services.document_service import DocumentValidationError, validate_document
from app.services.job_service import JobStateError, approve_job, cancel_job, create_pending_job
from app.services.quota_service import QuotaExceededError, QuotaService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/upload",
    response_model=JobResponse,
    dependencies=[
        Depends(rate_limit_dependency("upload", lambda s: s.upload_rate_limit_per_minute))
    ],
)
async def upload_job(
    file: UploadFile = File(...),
    copies: int = Form(default=1, ge=1, le=100),
    user=Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> JobResponse:
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large."
        )
    try:
        metadata = validate_document(
            filename=file.filename or "document", provided_mime=file.content_type, content=content
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    stored_filename = f"{uuid4()}{Path(file.filename or 'document').suffix.lower()}"
    settings.uploads_root.mkdir(parents=True, exist_ok=True)
    (settings.uploads_root / stored_filename).write_bytes(content)

    quota_service = QuotaService(settings.tz)
    try:
        job = create_pending_job(
            db=db,
            user=user,
            original_filename=file.filename or "document",
            stored_filename=stored_filename,
            metadata=metadata,
            copies=copies,
            quota_service=quota_service,
        )
        if not user.requires_approval:
            cups = CUPSService(cups_server=settings.cups_server, printer_name=settings.printer_name)
            approve_job(
                db=db,
                actor=user,
                job=job,
                cups_service=cups,
                file_path=settings.uploads_root / stored_filename,
            )
        db.commit()
        db.refresh(job)
    except QuotaExceededError as exc:
        db.rollback()
        (settings.uploads_root / stored_filename).unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return JobResponse(
        job_uuid=job.job_uuid,
        status=job.status,
        original_filename=job.original_filename,
        mime_type=job.mime_type,
        page_count=job.page_count,
        copies=job.copies,
        submitted_at=job.submitted_at,
        failure_reason=job.failure_reason,
    )


@router.get("", response_model=list[JobResponse])
def my_jobs(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[JobResponse]:
    stmt = (
        select(PrintJob).where(PrintJob.user_id == user.id).order_by(PrintJob.submitted_at.desc())
    )
    jobs = list(db.execute(stmt).scalars())
    return [
        JobResponse(
            job_uuid=job.job_uuid,
            status=job.status,
            original_filename=job.original_filename,
            mime_type=job.mime_type,
            page_count=job.page_count,
            copies=job.copies,
            submitted_at=job.submitted_at,
            failure_reason=job.failure_reason,
        )
        for job in jobs
    ]


@router.post("/{job_uuid}/cancel", response_model=JobResponse)
def cancel_job_route(
    job_uuid: str,
    user=Depends(require_csrf),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = db.execute(
        select(PrintJob).where(PrintJob.job_uuid == job_uuid, PrintJob.user_id == user.id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    try:
        cancel_job(db=db, actor=user, job=job)
        db.commit()
    except JobStateError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return JobResponse(
        job_uuid=job.job_uuid,
        status=job.status,
        original_filename=job.original_filename,
        mime_type=job.mime_type,
        page_count=job.page_count,
        copies=job.copies,
        submitted_at=job.submitted_at,
        failure_reason=job.failure_reason,
    )
