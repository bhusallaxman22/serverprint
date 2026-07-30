from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.print_job import PrintJobStatus


class JobResponse(BaseModel):
    job_uuid: str
    status: PrintJobStatus
    original_filename: str
    mime_type: str
    page_count: int
    copies: int
    submitted_at: datetime
    failure_reason: str | None


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
