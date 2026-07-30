from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from app.models.user import PrintMode, UserRole

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,64}$")


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    role: UserRole = UserRole.USER
    is_active: bool = True
    daily_page_quota: int = Field(default=250, ge=1, le=100000)
    weekly_page_quota: int = Field(default=1000, ge=1, le=100000)
    requires_approval: bool = True
    print_mode: PrintMode = PrintMode.BW
    must_change_password: bool = False

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip()
        if not _USERNAME_RE.fullmatch(username):
            raise ValueError(
                "Username must be 3–64 characters and use only letters, numbers, . _ -"
            )
        return username


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    daily_page_quota: int | None = Field(default=None, ge=1, le=100000)
    weekly_page_quota: int | None = Field(default=None, ge=1, le=100000)
    requires_approval: bool | None = None
    print_mode: PrintMode | None = None


class PrintModeUpdateRequest(BaseModel):
    print_mode: PrintMode
