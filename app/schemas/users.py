from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.user import PrintMode, UserRole


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    daily_page_quota: int | None = Field(default=None, ge=1, le=100000)
    weekly_page_quota: int | None = Field(default=None, ge=1, le=100000)
    requires_approval: bool | None = None
    print_mode: PrintMode | None = None


class PrintModeUpdateRequest(BaseModel):
    print_mode: PrintMode
