from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin, require_csrf
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse
from app.schemas.users import UserCreateRequest, UserUpdateRequest
from app.security import hash_password
from app.services.audit_service import write_audit_log

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        requires_approval=user.requires_approval,
        print_mode=user.print_mode,
    )


@router.get("", response_model=list[UserResponse])
def list_users(
    _: object = Depends(require_admin), db: Session = Depends(get_db)
) -> list[UserResponse]:
    users = list(db.execute(select(User).order_by(User.created_at.asc())).scalars())
    return [_to_response(user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    admin=Depends(require_csrf),
    db: Session = Depends(get_db),
) -> UserResponse:
    if admin.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required."
        )

    normalized = payload.username.casefold()
    existing = db.execute(
        select(User).where(User.username_normalized == normalized)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists."
        )

    user = User(
        username=payload.username,
        username_normalized=normalized,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        must_change_password=payload.must_change_password,
        daily_page_quota=payload.daily_page_quota,
        weekly_page_quota=payload.weekly_page_quota,
        requires_approval=payload.requires_approval,
        print_mode=payload.print_mode,
    )
    db.add(user)
    db.flush()
    write_audit_log(
        db=db,
        action="user_created",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=admin.id,
        details={
            "username": user.username,
            "role": user.role.value,
            "is_active": user.is_active,
            "requires_approval": user.requires_approval,
            "print_mode": user.print_mode.value,
            "daily_page_quota": user.daily_page_quota,
            "weekly_page_quota": user.weekly_page_quota,
        },
    )
    db.commit()
    db.refresh(user)
    return _to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    admin=Depends(require_csrf),
    db: Session = Depends(get_db),
) -> UserResponse:
    if admin.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required."
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target_role = payload.role if payload.role is not None else user.role
    target_active = payload.is_active if payload.is_active is not None else user.is_active
    if user.role == UserRole.ADMIN and (target_role != UserRole.ADMIN or not target_active):
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        active_admin_count = int(db.execute(stmt).scalar_one())
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot disable or demote the last active admin.",
            )

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.daily_page_quota is not None:
        user.daily_page_quota = payload.daily_page_quota
    if payload.weekly_page_quota is not None:
        user.weekly_page_quota = payload.weekly_page_quota
    if payload.requires_approval is not None:
        user.requires_approval = payload.requires_approval
    if payload.print_mode is not None:
        user.print_mode = payload.print_mode

    write_audit_log(
        db=db,
        action="user_updated",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=admin.id,
        details=payload.model_dump(exclude_none=True),
    )
    db.commit()
    return _to_response(user)
