from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.print_job import PrintJob, PrintJobStatus
from app.models.user import User

ACTIVE_QUOTA_STATUSES = {
    PrintJobStatus.PENDING,
    PrintJobStatus.APPROVED,
    PrintJobStatus.QUEUED,
    PrintJobStatus.PRINTING,
    PrintJobStatus.COMPLETED,
}


@dataclass
class QuotaCheckResult:
    daily_used: int
    weekly_used: int


class QuotaExceededError(Exception):
    pass


class QuotaService:
    def __init__(self, timezone_name: str) -> None:
        self._tz = ZoneInfo(timezone_name)

    def ensure_quota_for_new_job(
        self, db: Session, user: User, pages_requested: int, now_utc: datetime
    ) -> None:
        self._lock_user_row(db, user.id)
        daily_start_utc, weekly_start_utc = self._period_starts_utc(now_utc)
        usage = self._get_usage(db, user.id, daily_start_utc, weekly_start_utc)

        if usage.daily_used + pages_requested > user.daily_page_quota:
            raise QuotaExceededError("Daily page quota exceeded.")
        if usage.weekly_used + pages_requested > user.weekly_page_quota:
            raise QuotaExceededError("Weekly page quota exceeded.")

    def _lock_user_row(self, db: Session, user_id: int) -> None:
        stmt: Select[tuple[int]] = select(User.id).where(User.id == user_id).with_for_update()
        try:
            db.execute(stmt).scalar_one()
        except Exception:
            # SQLite does not support FOR UPDATE; transaction boundary still serializes writes.
            db.execute(select(User.id).where(User.id == user_id)).scalar_one()

    def _period_starts_utc(self, now_utc: datetime) -> tuple[datetime, datetime]:
        local_now = now_utc.astimezone(self._tz)
        daily_local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        weekly_local_start = daily_local_start - timedelta(days=daily_local_start.weekday())
        return daily_local_start.astimezone(ZoneInfo("UTC")), weekly_local_start.astimezone(
            ZoneInfo("UTC")
        )

    def _get_usage(
        self, db: Session, user_id: int, daily_start_utc: datetime, weekly_start_utc: datetime
    ) -> QuotaCheckResult:
        pages_expr = PrintJob.page_count * PrintJob.copies

        daily_stmt = (
            select(func.coalesce(func.sum(pages_expr), 0))
            .where(PrintJob.user_id == user_id)
            .where(PrintJob.status.in_(ACTIVE_QUOTA_STATUSES))
            .where(PrintJob.submitted_at >= daily_start_utc)
        )
        weekly_stmt = (
            select(func.coalesce(func.sum(pages_expr), 0))
            .where(PrintJob.user_id == user_id)
            .where(PrintJob.status.in_(ACTIVE_QUOTA_STATUSES))
            .where(PrintJob.submitted_at >= weekly_start_utc)
        )
        daily_used = int(db.execute(daily_stmt).scalar_one())
        weekly_used = int(db.execute(weekly_stmt).scalar_one())
        return QuotaCheckResult(daily_used=daily_used, weekly_used=weekly_used)
