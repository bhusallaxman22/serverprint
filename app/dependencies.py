from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models.user import User, UserRole
from app.security import constant_time_equals
from app.services.rate_limit_service import InMemoryRateLimiter, RateLimitRule

_rate_limiter = InMemoryRateLimiter()


def get_app_settings() -> Settings:
    return get_settings()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required."
        )
    return user


def require_csrf(
    request: Request,
    x_csrf_token: str = Header(default=""),
    user: User = Depends(get_current_user),
) -> User:
    expected = request.session.get("csrf_token", "")
    if not expected or not constant_time_equals(expected, x_csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")
    return user


def require_print_api_key(
    x_print_api_key: str = Header(default=""),
    settings: Settings = Depends(get_app_settings),
) -> None:
    if not constant_time_equals(settings.print_api_key, x_print_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")


def rate_limit_dependency(key_prefix: str, limit_getter: Callable[[Settings], int]):
    def _dep(request: Request, settings: Settings = Depends(get_app_settings)) -> None:
        source_ip = request.client.host if request.client else "unknown"
        key = f"{key_prefix}:{source_ip}"
        rule = RateLimitRule(
            limit=limit_getter(settings),
            window_seconds=settings.rate_limit_window_seconds,
        )
        if not _rate_limiter.allow(key, rule):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests."
            )

    return _dep


def get_user_by_username(db: Session, username: str) -> User | None:
    normalized = username.casefold()
    stmt = select(User).where(User.username_normalized == normalized)
    return db.execute(stmt).scalar_one_or_none()
