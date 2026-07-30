from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timezone

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)
