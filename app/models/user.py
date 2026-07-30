from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class PrintMode(str, Enum):
    COLOR = "color"
    BW = "bw"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username_normalized: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.USER, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_page_quota: Mapped[int] = mapped_column(Integer, default=250)
    weekly_page_quota: Mapped[int] = mapped_column(Integer, default=1000)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    print_mode: Mapped[PrintMode] = mapped_column(
        SqlEnum(PrintMode), default=PrintMode.BW, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    print_jobs = relationship("PrintJob", foreign_keys="PrintJob.user_id", back_populates="user")
