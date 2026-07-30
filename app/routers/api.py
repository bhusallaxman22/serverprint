from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.dependencies import (
    get_app_settings,
    get_current_user,
    get_user_by_username,
    require_csrf,
    require_print_api_key,
)
from app.models.print_job import PrintJob
from app.models.user import UserRole
from app.routers.jobs import upload_job
from app.schemas.auth import UserResponse
from app.schemas.jobs import JobResponse
from app.schemas.users import PrintModeUpdateRequest
from app.services.job_service import JobStateError, retry_failed_job
from app.services.printer_status_service import get_printer_status_snapshot
from app.services.quota_service import QuotaService
from app.services.cups_service import CUPSService

router = APIRouter(prefix="/api/v1", tags=["external-api"])


@router.post("/print", response_model=JobResponse, dependencies=[Depends(require_print_api_key)])
async def external_print(
    username: str = Form(...),
    file: UploadFile = File(...),
    copies: int = Form(default=1, ge=1, le=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> JobResponse:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return await upload_job(file=file, copies=copies, user=user, db=db, settings=settings)


@router.patch("/me/print-mode", response_model=UserResponse)
def update_my_print_mode(
    payload: PrintModeUpdateRequest,
    user=Depends(require_csrf),
    db: Session = Depends(get_db),
) -> UserResponse:
    user.print_mode = payload.print_mode
    db.commit()
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        requires_approval=user.requires_approval,
        print_mode=user.print_mode,
    )


@router.get("/printer/status")
def printer_status(
    _: object = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    snapshot = get_printer_status_snapshot(
        CUPSService(cups_server=settings.cups_server, printer_name=settings.printer_name)
    )
    return {
        "printer_name": snapshot.printer_name,
        "health": snapshot.health,
        "queue_depth": snapshot.queue_depth,
        "toner_percent": snapshot.toner_percent,
        "paper_percent": snapshot.paper_percent,
        "status_message": snapshot.status_message,
        "unavailable_reason": snapshot.unavailable_reason,
        "checked_at": snapshot.checked_at,
    }


@router.post("/admin/jobs/{job_uuid}/retry", response_model=JobResponse)
def retry_failed_job_endpoint(
    job_uuid: str,
    admin=Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> JobResponse:
    if admin.role != UserRole.ADMIN:
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
