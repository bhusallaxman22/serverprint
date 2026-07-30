from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PrintJobStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PrintJob(Base):
    __tablename__ = "print_jobs"
    __table_args__ = (
        Index("ix_print_jobs_status_submitted_at", "status", "submitted_at"),
        Index("ix_print_jobs_user_id_submitted_at", "user_id", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[PrintJobStatus] = mapped_column(
        Enum(PrintJobStatus, name="print_job_status"),
        default=PrintJobStatus.PENDING,
        nullable=False,
        index=True,
    )
    cups_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retried_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retried_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="print_jobs")


JobStatus = PrintJobStatus
