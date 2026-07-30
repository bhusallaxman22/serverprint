from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.dependencies import get_app_settings, get_current_user, require_admin
from app.models.audit_log import AuditLog
from app.models.print_job import PrintJob, PrintJobStatus
from app.models.user import User, UserRole
from app.security import hash_password, new_csrf_token, verify_password
from app.services.audit_service import write_audit_log
from app.services.cups_service import CUPSService
from app.services.document_service import DocumentValidationError, validate_document
from app.services.job_service import (
    JobStateError,
    approve_job,
    cancel_job,
    create_pending_job,
    reject_job,
    retry_failed_job,
)
from app.services.printer_status_service import get_printer_status_snapshot
from app.services.quota_service import QuotaExceededError, QuotaService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _flash(request: Request, level: str, message: str) -> None:
    flashes = request.session.setdefault("flashes", [])
    flashes.append({"level": level, "message": message})


def _pop_flashes(request: Request) -> list[dict[str, str]]:
    flashes = request.session.get("flashes", [])
    request.session["flashes"] = []
    return flashes


def _printer_payload(settings: Settings) -> dict[str, Any]:
    cups = CUPSService(cups_server=settings.cups_server, printer_name=settings.printer_name)
    snapshot = get_printer_status_snapshot(cups)
    return {
        "name": snapshot.printer_name,
        "health": snapshot.health,
        "toner": snapshot.toner_percent,
        "paper": snapshot.paper_percent,
        "queue_depth": snapshot.queue_depth,
        "status_message": snapshot.status_message,
        "unavailable_reason": snapshot.unavailable_reason,
        "last_updated": snapshot.checked_at,
    }


def _user_nav(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.username,
        "role": user.role.value,
    }


def _base_context(request: Request, settings: Settings, user: User | None) -> dict[str, Any]:
    return {
        "request": request,
        "app_name": settings.app_name,
        "user": _user_nav(user) if user else None,
        "printer": _printer_payload(settings),
        "flashes": _pop_flashes(request),
        "ui_settings": {
            "max_upload_mb": settings.max_upload_mb,
            "print_status_poll_seconds": settings.print_status_poll_seconds,
        },
        "now": datetime.now(UTC),
    }


def _map_job(job: PrintJob, owner: str | None = None) -> dict[str, Any]:
    return {
        "id": job.id,
        "job_uuid": job.job_uuid,
        "document_name": job.original_filename,
        "pages": job.page_count,
        "copies": job.copies,
        "status": job.status,
        "requested_at": job.submitted_at,
        "owner_username": owner or "unknown",
        "reason": job.failure_reason,
    }


@router.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    try:
        user = get_current_user(request, db)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    if user.role == UserRole.ADMIN:
        return RedirectResponse("/ui/admin/dashboard", status_code=303)
    return RedirectResponse("/ui/dashboard", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request, settings: Settings = Depends(get_app_settings), db: Session = Depends(get_db)
) -> Response:
    try:
        user = get_current_user(request, db)
        if user.role == UserRole.ADMIN:
            return RedirectResponse("/ui/admin/dashboard", status_code=303)
        return RedirectResponse("/ui/dashboard", status_code=303)
    except HTTPException:
        context = _base_context(request, settings, user=None)
        return templates.TemplateResponse("login.html", context)


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    normalized = username.strip().casefold()
    user = db.execute(
        select(User).where(User.username_normalized == normalized)
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash) or not user.is_active:
        _flash(request, "error", "Invalid credentials. Please try again.")
        return RedirectResponse("/login", status_code=303)

    request.session["user_id"] = user.id
    request.session["csrf_token"] = new_csrf_token()
    _flash(request, "success", f"Welcome back, {user.username}.")
    return RedirectResponse(
        "/ui/admin/dashboard" if user.role == UserRole.ADMIN else "/ui/dashboard", status_code=303
    )


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    request.session["flashes"] = [{"level": "info", "message": "You have been signed out."}]
    return RedirectResponse("/login", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_redirect(_: User = Depends(get_current_user)) -> RedirectResponse:
    return RedirectResponse("/ui/dashboard", status_code=303)


@router.get("/ui/dashboard", response_class=HTMLResponse)
def user_dashboard(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    if current_user.role == UserRole.ADMIN:
        return RedirectResponse("/ui/admin/dashboard", status_code=303)

    jobs = list(
        db.execute(
            select(PrintJob)
            .where(PrintJob.user_id == current_user.id)
            .order_by(PrintJob.submitted_at.desc())
        ).scalars()
    )
    summary = {
        "queued": len(
            [
                job
                for job in jobs
                if job.status
                in {
                    PrintJobStatus.PENDING,
                    PrintJobStatus.QUEUED,
                    PrintJobStatus.APPROVED,
                    PrintJobStatus.PRINTING,
                }
            ]
        ),
        "printed": len([job for job in jobs if job.status == PrintJobStatus.COMPLETED]),
        "failed": len(
            [job for job in jobs if job.status in {PrintJobStatus.FAILED, PrintJobStatus.REJECTED}]
        ),
    }

    quota_service = QuotaService(settings.tz)
    daily_start, weekly_start = quota_service._period_starts_utc(datetime.now(UTC))
    usage = quota_service._get_usage(db, current_user.id, daily_start, weekly_start)

    context = _base_context(request, settings, current_user)
    context.update(
        {
            "nav_key": "dashboard",
            "summary": summary,
            "jobs": [_map_job(job, current_user.username) for job in jobs[:20]],
            "quota": {
                "used": usage.daily_used,
                "total": current_user.daily_page_quota,
            },
        }
    )
    return templates.TemplateResponse("dashboard_user.html", context)


@router.get("/ui/dashboard/jobs", response_class=HTMLResponse)
def user_jobs_partial(
    request: Request,
    status: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="User-only endpoint")

    stmt = select(PrintJob).where(PrintJob.user_id == current_user.id)
    if status != "all":
        stmt = stmt.where(PrintJob.status == PrintJobStatus(status))
    jobs = list(db.execute(stmt.order_by(PrintJob.submitted_at.desc())).scalars())
    return templates.TemplateResponse(
        "partials/user_job_rows.html",
        {"request": request, "jobs": [_map_job(job, current_user.username) for job in jobs]},
    )


@router.post("/ui/dashboard/upload", response_class=HTMLResponse)
async def upload_job(
    request: Request,
    file: UploadFile = File(...),
    copies: int = Form(1),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="User-only endpoint")

    content = await file.read()
    errors: list[str] = []
    if not file.filename:
        errors.append("Select a document before uploading.")
    if copies < 1 or copies > 15:
        errors.append("Copies must be between 1 and 15.")
    if len(content) > settings.max_upload_bytes:
        errors.append(f"File exceeds {settings.max_upload_mb}MB upload limit.")

    metadata = None
    if not errors:
        try:
            metadata = validate_document(file.filename or "document", file.content_type, content)
        except DocumentValidationError as exc:
            errors.append(str(exc))

    if errors:
        for message in errors:
            _flash(request, "error", message)
        jobs = list(
            db.execute(
                select(PrintJob)
                .where(PrintJob.user_id == current_user.id)
                .order_by(PrintJob.submitted_at.desc())
            ).scalars()
        )
        return templates.TemplateResponse(
            "partials/user_job_rows.html",
            {"request": request, "jobs": [_map_job(job, current_user.username) for job in jobs]},
        )

    assert metadata is not None
    stored_filename = f"{uuid4()}{Path(file.filename or 'document').suffix.lower()}"
    settings.uploads_root.mkdir(parents=True, exist_ok=True)
    (settings.uploads_root / stored_filename).write_bytes(content)

    try:
        job = create_pending_job(
            db=db,
            user=current_user,
            original_filename=file.filename or "document",
            stored_filename=stored_filename,
            metadata=metadata,
            copies=copies,
            quota_service=QuotaService(settings.tz),
        )
        if not current_user.requires_approval:
            approve_job(
                db=db,
                actor=current_user,
                job=job,
                cups_service=CUPSService(
                    cups_server=settings.cups_server, printer_name=settings.printer_name
                ),
                file_path=settings.uploads_root / stored_filename,
            )
        db.commit()
    except QuotaExceededError as exc:
        db.rollback()
        (settings.uploads_root / stored_filename).unlink(missing_ok=True)
        _flash(request, "error", str(exc))
    else:
        if current_user.requires_approval:
            _flash(request, "success", f"Queued {file.filename} for approval.")
        else:
            _flash(request, "success", f"Queued {file.filename} for printing.")

    jobs = list(
        db.execute(
            select(PrintJob)
            .where(PrintJob.user_id == current_user.id)
            .order_by(PrintJob.submitted_at.desc())
        ).scalars()
    )
    return templates.TemplateResponse(
        "partials/user_job_rows.html",
        {"request": request, "jobs": [_map_job(job, current_user.username) for job in jobs]},
    )


@router.get("/ui/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    jobs = list(db.execute(select(PrintJob).order_by(PrintJob.submitted_at.desc())).scalars())
    pending_jobs = [job for job in jobs if job.status == PrintJobStatus.PENDING]
    failed_jobs = [job for job in jobs if job.status == PrintJobStatus.FAILED]

    username_rows = db.execute(select(User.id, User.username)).all()
    username_map: dict[int, str] = {user_id: username for user_id, username in username_rows}
    recent_audits = list(
        db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(8)).scalars()
    )

    summary = {
        "pending_approval": len(pending_jobs),
        "active_users": int(
            db.execute(
                select(func.count()).select_from(User).where(User.is_active.is_(True))
            ).scalar_one()
        ),
        "failed_today": len(
            [
                job
                for job in failed_jobs
                if job.updated_at and job.updated_at.date() == datetime.now(UTC).date()
            ]
        ),
        "jobs_today": len(
            [
                job
                for job in jobs
                if job.submitted_at and job.submitted_at.date() == datetime.now(UTC).date()
            ]
        ),
    }

    context = _base_context(request, settings, current_user)
    context.update(
        {
            "nav_key": "admin-dashboard",
            "summary": summary,
            "pending_jobs": [
                _map_job(job, username_map.get(job.user_id, "unknown")) for job in pending_jobs[:8]
            ],
            "recent_audits": [
                {
                    "action": row.action,
                    "actor": (
                        username_map.get(row.actor_user_id, "system")
                        if row.actor_user_id
                        else "system"
                    ),
                    "target": f"{row.target_type}:{row.target_id or '-'}",
                    "detail": row.details,
                    "created_at": row.created_at,
                }
                for row in recent_audits
            ],
        }
    )
    return templates.TemplateResponse("dashboard_admin.html", context)


@router.get("/ui/admin/users", response_class=HTMLResponse)
def users_admin_page(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    users = list(db.execute(select(User).order_by(User.created_at.asc())).scalars())
    context = _base_context(request, settings, current_user)
    context.update(
        {
            "nav_key": "users",
            "users": users,
            "role_filter": "all",
            "show_inactive": True,
            "search_query": "",
        }
    )
    return templates.TemplateResponse("admin_users.html", context)


@router.get("/ui/admin/users/list", response_class=HTMLResponse)
def users_partial(
    request: Request,
    search: str = "",
    role: str = "all",
    show_inactive: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> HTMLResponse:
    stmt = select(User)
    if search.strip():
        query = f"%{search.strip()}%"
        stmt = stmt.where(or_(User.username.ilike(query), User.username_normalized.ilike(query)))
    if role in {"admin", "user"}:
        stmt = stmt.where(User.role == UserRole(role))
    if not show_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    users = list(db.execute(stmt.order_by(User.created_at.asc())).scalars())
    return templates.TemplateResponse(
        "partials/admin_user_rows.html",
        {
            "request": request,
            "users": users,
            "role_filter": role,
            "show_inactive": show_inactive,
            "search_query": search,
        },
    )


@router.post("/ui/admin/users/{user_id}/update", response_class=HTMLResponse)
def users_update(
    user_id: int,
    request: Request,
    search: str = Form(""),
    role_filter: str = Form("all"),
    show_inactive: bool = Form(True),
    role: str = Form("user"),
    is_active: bool = Form(False),
    requires_approval: bool = Form(False),
    daily_page_quota: int = Form(250),
    weekly_page_quota: int = Form(1000),
    reset_password: bool = Form(False),
    temp_password: str = Form(""),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    user = db.get(User, user_id)
    if user is not None:
        target_role = UserRole(role)
        target_active = is_active
        if user.role == UserRole.ADMIN and (target_role != UserRole.ADMIN or not target_active):
            active_admin_count = int(
                db.execute(
                    select(func.count())
                    .select_from(User)
                    .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
                ).scalar_one()
            )
            if active_admin_count <= 1:
                _flash(request, "error", "Cannot disable or demote the last active admin.")
                return users_partial(
                    request=request,
                    search=search,
                    role=role_filter,
                    show_inactive=show_inactive,
                    db=db,
                    _=admin,
                )
        user.role = target_role
        user.is_active = target_active
        user.requires_approval = requires_approval
        user.daily_page_quota = max(1, daily_page_quota)
        user.weekly_page_quota = max(1, weekly_page_quota)
        if reset_password and temp_password.strip():
            user.password_hash = hash_password(temp_password.strip())
            user.must_change_password = True
        db.commit()
        write_audit_log(
            db=db,
            action="user_updated",
            target_type="user",
            target_id=str(user.id),
            actor_user_id=admin.id,
            details={"role": user.role.value, "is_active": user.is_active},
        )
        db.commit()

    return users_partial(
        request=request,
        search=search,
        role=role_filter,
        show_inactive=show_inactive,
        db=db,
        _=admin,
    )


@router.get("/ui/admin/jobs", response_class=HTMLResponse)
def jobs_admin_page(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    user_rows = db.execute(select(User.id, User.username)).all()
    users: dict[int, str] = {user_id: username for user_id, username in user_rows}
    jobs = list(db.execute(select(PrintJob).order_by(PrintJob.submitted_at.desc())).scalars())
    context = _base_context(request, settings, current_user)
    context.update(
        {
            "nav_key": "jobs",
            "jobs": [_map_job(job, users.get(job.user_id, "unknown")) for job in jobs],
            "status_filter": "all",
            "owner_filter": "",
            "search_query": "",
            "status_options": ["all"] + [state.value for state in PrintJobStatus],
        }
    )
    return templates.TemplateResponse("admin_jobs.html", context)


@router.get("/ui/admin/jobs/list", response_class=HTMLResponse)
def jobs_partial(
    request: Request,
    status: str = "all",
    owner: str = "",
    search: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> HTMLResponse:
    stmt = select(PrintJob, User.username).join(User, User.id == PrintJob.user_id)
    if status != "all":
        stmt = stmt.where(PrintJob.status == PrintJobStatus(status))
    if owner.strip():
        stmt = stmt.where(User.username.ilike(f"%{owner.strip()}%"))
    if search.strip():
        q = f"%{search.strip()}%"
        stmt = stmt.where(or_(PrintJob.original_filename.ilike(q), PrintJob.job_uuid.ilike(q)))

    rows = db.execute(stmt.order_by(PrintJob.submitted_at.desc())).all()
    jobs = [_map_job(job, username) for job, username in rows]
    return templates.TemplateResponse(
        "partials/admin_job_rows.html",
        {
            "request": request,
            "jobs": jobs,
            "status_filter": status,
            "owner_filter": owner,
            "search_query": search,
        },
    )


@router.post("/ui/admin/jobs/{job_uuid}/action", response_class=HTMLResponse)
def jobs_update_status(
    job_uuid: str,
    request: Request,
    action: str = Form(...),
    reason: str = Form(""),
    status: str = Form("all"),
    owner: str = Form(""),
    search: str = Form(""),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    admin: User = Depends(require_admin),
) -> HTMLResponse:
    job = db.execute(select(PrintJob).where(PrintJob.job_uuid == job_uuid)).scalar_one_or_none()
    if job is None:
        _flash(request, "error", "Job not found.")
        return jobs_partial(
            request=request, status=status, owner=owner, search=search, db=db, _=admin
        )

    cups = CUPSService(cups_server=settings.cups_server, printer_name=settings.printer_name)
    file_path = settings.uploads_root / job.stored_filename
    try:
        if action == "approve":
            approve_job(db=db, actor=admin, job=job, cups_service=cups, file_path=file_path)
        elif action == "reject":
            reject_job(db=db, actor=admin, job=job, reason=reason or "Rejected by administrator.")
        elif action == "cancel":
            cancel_job(db=db, actor=admin, job=job)
        elif action == "retry":
            retry_failed_job(
                db=db,
                actor=admin,
                job=job,
                file_path=file_path,
                quota_service=QuotaService(settings.tz),
                allow_retry=settings.allow_failed_job_retry,
                max_retries=settings.max_job_retries,
            )
        db.commit()
    except (JobStateError, ValueError) as exc:
        db.rollback()
        _flash(request, "error", str(exc))

    return jobs_partial(request=request, status=status, owner=owner, search=search, db=db, _=admin)


@router.get("/ui/admin/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> HTMLResponse:
    actor_rows = db.execute(select(User.id, User.username)).all()
    actor_map: dict[int, str] = {user_id: username for user_id, username in actor_rows}
    rows = list(db.execute(select(AuditLog).order_by(AuditLog.created_at.desc())).scalars())
    context = _base_context(request, settings, current_user)
    context.update(
        {
            "nav_key": "audit",
            "rows": [
                {
                    "created_at": row.created_at,
                    "actor": (
                        actor_map.get(row.actor_user_id, "system")
                        if row.actor_user_id
                        else "system"
                    ),
                    "action": row.action,
                    "target": f"{row.target_type}:{row.target_id or '-'}",
                    "detail": row.details,
                }
                for row in rows
            ],
            "actor_filter": "",
            "action_filter": "",
            "search_query": "",
        }
    )
    return templates.TemplateResponse("audit_log.html", context)


@router.get("/ui/admin/audit/list", response_class=HTMLResponse)
def audit_partial(
    request: Request,
    actor: str = "",
    action: str = "",
    query: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> HTMLResponse:
    stmt = select(AuditLog, User.username).outerjoin(User, User.id == AuditLog.actor_user_id)
    if actor.strip():
        stmt = stmt.where(User.username.ilike(f"%{actor.strip()}%"))
    if action.strip():
        stmt = stmt.where(AuditLog.action.ilike(f"%{action.strip()}%"))
    if query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(or_(AuditLog.target_type.ilike(q), AuditLog.target_id.ilike(q)))

    rows = db.execute(stmt.order_by(AuditLog.created_at.desc())).all()
    payload = [
        {
            "created_at": audit.created_at,
            "actor": username or "system",
            "action": audit.action,
            "target": f"{audit.target_type}:{audit.target_id or '-'}",
            "detail": audit.details,
        }
        for audit, username in rows
    ]
    return templates.TemplateResponse(
        "partials/audit_rows.html",
        {
            "request": request,
            "rows": payload,
            "actor_filter": actor,
            "action_filter": action,
            "search_query": query,
        },
    )


@router.get("/ui/printer/status", response_class=HTMLResponse)
def printer_status_partial(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    _: User = Depends(get_current_user),
) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/printer_status_card.html",
        {"request": request, "printer": _printer_payload(settings)},
    )
