from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.print_job import PrintJob, PrintJobStatus
from app.security import now_utc


def cleanup_stale_jobs_and_files(
    db: Session,
    uploads_root: Path,
    failed_retention_hours: int,
    pending_retention_days: int,
) -> int:
    current = now_utc()
    failed_cutoff = current - timedelta(hours=failed_retention_hours)
    pending_cutoff = current - timedelta(days=pending_retention_days)

    stmt = select(PrintJob).where(
        ((PrintJob.status == PrintJobStatus.FAILED) & (PrintJob.updated_at < failed_cutoff))
        | ((PrintJob.status == PrintJobStatus.PENDING) & (PrintJob.submitted_at < pending_cutoff))
    )
    jobs = list(db.execute(stmt).scalars())
    for job in jobs:
        safe_path = uploads_root / job.stored_filename
        if safe_path.exists():
            safe_path.unlink(missing_ok=True)
    if not jobs:
        return 0
    delete_stmt = delete(PrintJob).where(PrintJob.id.in_([job.id for job in jobs]))
    db.execute(delete_stmt)
    return len(jobs)
