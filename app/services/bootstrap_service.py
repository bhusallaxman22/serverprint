from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.user import User, UserRole
from app.security import hash_password

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_PASSWORD = "admin123456"


def bootstrap_admin(db: Session, settings: Settings) -> None:
    count_stmt = select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
    admin_count = int(db.execute(count_stmt).scalar_one())
    if admin_count > 0:
        return

    if settings.admin_password == DEFAULT_ADMIN_PASSWORD:
        logger.warning("Bootstrap admin password matches default value. Rotate immediately.")

    admin = User(
        username=settings.admin_username,
        username_normalized=settings.admin_username.casefold(),
        password_hash=hash_password(settings.admin_password),
        role=UserRole.ADMIN,
        is_active=True,
        must_change_password=settings.force_password_change_default,
    )
    db.add(admin)
    db.commit()
