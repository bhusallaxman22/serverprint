from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    get_current_user,
    get_user_by_username,
    rate_limit_dependency,
    require_csrf,
)
from app.schemas.auth import AuthResponse, LoginRequest, UserResponse
from app.security import new_csrf_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit_dependency("login", lambda s: s.login_rate_limit_per_minute))],
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    user = get_user_by_username(db, payload.username)
    if (
        user is None
        or not verify_password(payload.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    csrf_token = new_csrf_token()
    request.session["user_id"] = user.id
    request.session["csrf_token"] = csrf_token
    return AuthResponse(
        csrf_token=csrf_token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            requires_approval=user.requires_approval,
            print_mode=user.print_mode,
        ),
    )


@router.post("/logout")
def logout(request: Request, _: object = Depends(require_csrf)) -> dict[str, str]:
    request.session.clear()
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
def me(user=Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        requires_approval=user.requires_approval,
        print_mode=user.print_mode,
    )
