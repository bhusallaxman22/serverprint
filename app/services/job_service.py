from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.print_job import PrintJob, PrintJobStatus
from app.models.user import User
from app.security import now_utc
from app.services.audit_service import write_audit_log
from app.services.cups_service import CUPSService, CUPSServiceError
from app.services.document_service import DocumentMetadata
from app.services.quota_service import QuotaService


class JobStateError(Exception):
    pass


def create_pending_job(
    db: Session,
    user: User,
    original_filename: str,
    stored_filename: str,
    metadata: DocumentMetadata,
    copies: int,
    quota_service: QuotaService,
) -> PrintJob:
    timestamp = now_utc()
    quota_service.ensure_quota_for_new_job(
        db=db, user=user, pages_requested=metadata.page_count * copies, now_utc=timestamp
    )
    job = PrintJob(
        user_id=user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        mime_type=metadata.mime_type,
        extension=metadata.extension,
        page_count=metadata.page_count,
        copies=copies,
        status=PrintJobStatus.PENDING,
        submitted_at=timestamp,
    )
    db.add(job)
    db.flush()
    write_audit_log(
        db,
        action="job_submitted",
        target_type="print_job",
        target_id=job.job_uuid,
        actor_user_id=user.id,
    )
    return job


def approve_job(
    db: Session, actor: User, job: PrintJob, cups_service: CUPSService, file_path: Path
) -> PrintJob:
    if job.status != PrintJobStatus.PENDING:
        raise JobStateError("Only pending jobs can be approved.")
    now = now_utc()
    job.status = PrintJobStatus.APPROVED
    job.approved_at = now
    job.approved_by_user_id = actor.id
    try:
        cups_id = cups_service.submit_job(
            file_path=file_path, title=job.original_filename, copies=job.copies
        )
    except CUPSServiceError:
        job.status = PrintJobStatus.FAILED
        job.failure_reason = "Failed to queue print job."
        write_audit_log(
            db,
            action="job_failed_to_queue",
            target_type="print_job",
            target_id=job.job_uuid,
            actor_user_id=actor.id,
        )
        return job
    job.cups_job_id = cups_id
    job.status = PrintJobStatus.QUEUED
    write_audit_log(
        db,
        action="job_approved",
        target_type="print_job",
        target_id=job.job_uuid,
        actor_user_id=actor.id,
    )
    return job


def reject_job(db: Session, actor: User, job: PrintJob, reason: str) -> PrintJob:
    if job.status != PrintJobStatus.PENDING:
        raise JobStateError("Only pending jobs can be rejected.")
    job.status = PrintJobStatus.REJECTED
    job.rejected_at = now_utc()
    job.rejected_by_user_id = actor.id
    job.failure_reason = reason
    write_audit_log(
        db,
        action="job_rejected",
        target_type="print_job",
        target_id=job.job_uuid,
        actor_user_id=actor.id,
        details={"reason": reason},
    )
    return job


def cancel_job(db: Session, actor: User, job: PrintJob) -> PrintJob:
    if job.status in {PrintJobStatus.COMPLETED, PrintJobStatus.CANCELLED}:
        raise JobStateError("Job cannot be cancelled.")
    job.status = PrintJobStatus.CANCELLED
    write_audit_log(
        db,
        action="job_cancelled",
        target_type="print_job",
        target_id=job.job_uuid,
        actor_user_id=actor.id,
    )
    return job


def sync_queued_jobs_from_cups(
    db: Session, cups_service: CUPSService, as_of: datetime | None = None
) -> int:
    current = as_of or now_utc()
    active_states = cups_service.fetch_job_states()
    if active_states is None:
        # Do not mutate statuses when CUPS telemetry cannot be fetched.
        return 0
    active_ids = {state.cups_job_id for state in active_states}
    stmt = select(PrintJob).where(
        PrintJob.status.in_([PrintJobStatus.QUEUED, PrintJobStatus.PRINTING])
    )
    jobs = list(db.execute(stmt).scalars())
    updated = 0
    for job in jobs:
        if not job.cups_job_id:
            continue
        if job.cups_job_id in active_ids:
            if job.status != PrintJobStatus.PRINTING:
                job.status = PrintJobStatus.PRINTING
                job.updated_at = current
                updated += 1
            continue
        job.status = PrintJobStatus.COMPLETED
        job.updated_at = current
        updated += 1
    return updated


def retry_failed_job(
    db: Session,
    actor: User,
    job: PrintJob,
    file_path: Path,
    quota_service: QuotaService,
    allow_retry: bool,
    max_retries: int,
) -> PrintJob:
    if not allow_retry:
        raise JobStateError("Retry policy is disabled.")
    if job.status != PrintJobStatus.FAILED:
        raise JobStateError("Only failed jobs can be retried.")
    if job.retry_count >= max_retries:
        raise JobStateError("Maximum retries reached for this job.")
    if not file_path.exists():
        raise JobStateError("Original document is unavailable for retry.")

    quota_service.ensure_quota_for_new_job(
        db=db,
        user=job.user,
        pages_requested=job.page_count * job.copies,
        now_utc=now_utc(),
    )

    previous_status = job.status.value
    job.status = PrintJobStatus.PENDING
    job.failure_reason = None
    job.cups_job_id = None
    job.approved_at = None
    job.approved_by_user_id = None
    job.rejected_at = None
    job.rejected_by_user_id = None
    job.retry_count += 1
    job.retried_at = now_utc()
    job.retried_by_user_id = actor.id
    write_audit_log(
        db=db,
        action="job_retried",
        target_type="print_job",
        target_id=job.job_uuid,
        actor_user_id=actor.id,
        details={
            "from_status": previous_status,
            "to_status": job.status.value,
            "retry_count": job.retry_count,
        },
    )
    return job
