from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import SessionLocal
from app.services.cleanup_service import cleanup_stale_jobs_and_files
from app.services.cups_service import CUPSService
from app.services.job_service import sync_queued_jobs_from_cups


class BackendScheduler:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._scheduler = BackgroundScheduler(timezone=settings.tz)
        self._cups = CUPSService(
            cups_server=settings.cups_server, printer_name=settings.printer_name
        )

    def start(self) -> None:
        self._scheduler.add_job(
            self._sync_cups, "interval", seconds=self._settings.print_status_poll_seconds
        )
        self._scheduler.add_job(self._cleanup_stale, "interval", hours=1)
        self._scheduler.start()

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    def _sync_cups(self) -> None:
        with SessionLocal() as db:
            assert isinstance(db, Session)
            sync_queued_jobs_from_cups(db=db, cups_service=self._cups)
            db.commit()

    def _cleanup_stale(self) -> None:
        with SessionLocal() as db:
            assert isinstance(db, Session)
            cleanup_stale_jobs_and_files(
                db=db,
                uploads_root=self._settings.uploads_root,
                failed_retention_hours=self._settings.failed_file_retention_hours,
                pending_retention_days=self._settings.pending_file_retention_days,
            )
            db.commit()
