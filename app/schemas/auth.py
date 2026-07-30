from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.user import PrintMode, UserRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    requires_approval: bool
    print_mode: PrintMode


class AuthResponse(BaseModel):
    csrf_token: str
    user: UserResponse
