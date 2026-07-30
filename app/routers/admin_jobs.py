from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.dependencies import get_app_settings, require_admin, require_csrf
from app.models.print_job import PrintJob
from app.schemas.jobs import JobResponse, RejectRequest
from app.services.cups_service import CUPSService
from app.services.job_service import JobStateError, approve_job, reject_job, retry_failed_job
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs(
    _: object = Depends(require_admin), db: Session = Depends(get_db)
) -> list[JobResponse]:
    jobs = list(db.execute(select(PrintJob).order_by(PrintJob.submitted_at.desc())).scalars())
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


@router.post("/{job_uuid}/approve", response_model=JobResponse)
def approve_job_route(
    job_uuid: str,
    admin=Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> JobResponse:
    if admin.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required."
        )
    job = db.execute(select(PrintJob).where(PrintJob.job_uuid == job_uuid)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    cups = CUPSService(cups_server=settings.cups_server, printer_name=settings.printer_name)
    try:
        approve_job(
            db=db,
            actor=admin,
            job=job,
            cups_service=cups,
            file_path=settings.uploads_root / job.stored_filename,
        )
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


@router.post("/{job_uuid}/reject", response_model=JobResponse)
def reject_job_route(
    job_uuid: str,
    payload: RejectRequest,
    admin=Depends(require_csrf),
    db: Session = Depends(get_db),
) -> JobResponse:
    if admin.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required."
        )
    job = db.execute(select(PrintJob).where(PrintJob.job_uuid == job_uuid)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    try:
        reject_job(db=db, actor=admin, job=job, reason=payload.reason)
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


@router.post("/{job_uuid}/retry", response_model=JobResponse)
def retry_job_route(
    job_uuid: str,
    admin=Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> JobResponse:
    if admin.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required."
        )
    job = db.execute(select(PrintJob).where(PrintJob.job_uuid == job_uuid)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    try:
        retry_failed_job(
            db=db,
            actor=admin,
            job=job,
            file_path=settings.uploads_root / job.stored_filename,
            quota_service=QuotaService(settings.tz),
            allow_retry=settings.allow_failed_job_retry,
            max_retries=settings.max_job_retries,
        )
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
