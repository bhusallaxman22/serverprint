from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import ORJSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

import app.database as database
from app.config import get_settings
from app.routers import admin_jobs, admin_users, api, auth, jobs, web
from app.services.bootstrap_service import bootstrap_admin
from app.services.scheduler_service import BackendScheduler

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    database.Base.metadata.create_all(bind=database.engine)
    with database.SessionLocal() as db:
        bootstrap_admin(db, settings)

    scheduler = None
    if settings.run_scheduler:
        scheduler = BackendScheduler(settings)
        scheduler.start()
        logger.info("Scheduler started.")
    try:
        yield
    finally:
        if scheduler:
            scheduler.stop()


def _is_browser_ui_path(path: str) -> bool:
    """HTML session routes that should redirect to login instead of JSON 401."""
    return path.startswith("/ui/") or path in {"/dashboard", "/logout"}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, default_response_class=ORJSONResponse, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        max_age=settings.session_max_age_seconds,
        same_site=settings.cookie_samesite,
        https_only=settings.secure_cookies,
    )
    app.add_middleware(SecureHeadersMiddleware)

    @app.exception_handler(HTTPException)
    async def ui_aware_http_exception_handler(request: Request, exc: HTTPException):
        # Browser UI hits look like raw JSON errors when the session cookie is missing
        # (common with SECURE_COOKIES=true over plain HTTP). Send them to login instead.
        if exc.status_code == 401 and _is_browser_ui_path(request.url.path):
            return RedirectResponse("/login", status_code=303)
        return await http_exception_handler(request, exc)

    app.include_router(auth.router)
    app.include_router(web.router)
    app.include_router(jobs.router)
    app.include_router(admin_jobs.router)
    app.include_router(admin_users.router)
    app.include_router(api.router)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
