from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.print_job import PrintJob, PrintJobStatus
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.cups_service import CUPSService, CUPSServiceError
from app.services.job_service import sync_queued_jobs_from_cups


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_approve_job_queues_and_audits(
    client: TestClient,
    db: Session,
    png_bytes: bytes,
    monkeypatch,
) -> None:
    user = User(
        username="charlie",
        username_normalized="charlie",
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.USER,
        is_active=True,
        daily_page_quota=10,
        weekly_page_quota=20,
    )
    db.add(user)
    db.commit()

    user_csrf = _login(client, "charlie", "StrongPassword123")
    created = client.post(
        "/jobs/upload",
        data={"copies": 1},
        files={"file": ("sample.png", png_bytes, "image/png")},
        headers={"x-csrf-token": user_csrf},
    )
    assert created.status_code == 200
    job_uuid = created.json()["job_uuid"]

    monkeypatch.setattr(CUPSService, "submit_job", lambda self, file_path, title, copies: "321")
    admin_csrf = _login(client, "admin", "admin123456")
    approved = client.post(f"/admin/jobs/{job_uuid}/approve", headers={"x-csrf-token": admin_csrf})
    assert approved.status_code == 200
    assert approved.json()["status"] == "queued"

    audits = db.query(AuditLog).all()
    assert any(entry.action == "job_submitted" for entry in audits)
    assert any(entry.action == "job_approved" for entry in audits)


def test_failed_job_retry_requires_file_and_is_audited(
    client: TestClient, db: Session, png_bytes: bytes, monkeypatch
) -> None:
    user = User(
        username="delta",
        username_normalized="delta",
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.USER,
        is_active=True,
        daily_page_quota=10,
        weekly_page_quota=20,
    )
    db.add(user)
    db.commit()

    user_csrf = _login(client, "delta", "StrongPassword123")
    created = client.post(
        "/jobs/upload",
        data={"copies": 1},
        files={"file": ("retry.png", png_bytes, "image/png")},
        headers={"x-csrf-token": user_csrf},
    )
    assert created.status_code == 200
    job_uuid = created.json()["job_uuid"]

    def fail_submit(self, file_path, title, copies):  # type: ignore[no-untyped-def]
        raise CUPSServiceError("queue fail")

    monkeypatch.setattr(CUPSService, "submit_job", fail_submit)
    admin_csrf = _login(client, "admin", "admin123456")
    failed = client.post(f"/admin/jobs/{job_uuid}/approve", headers={"x-csrf-token": admin_csrf})
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    retried = client.post(
        f"/api/v1/admin/jobs/{job_uuid}/retry", headers={"x-csrf-token": admin_csrf}
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"

    failed_again = client.post(
        f"/admin/jobs/{job_uuid}/approve", headers={"x-csrf-token": admin_csrf}
    )
    assert failed_again.status_code == 200
    assert failed_again.json()["status"] == "failed"

    job = db.query(PrintJob).filter_by(job_uuid=job_uuid).one()
    # Remove stored file and confirm retry is rejected by backend policy.
    from app.config import get_settings

    settings = get_settings()
    (settings.uploads_root / job.stored_filename).unlink(missing_ok=True)
    blocked = client.post(
        f"/api/v1/admin/jobs/{job_uuid}/retry", headers={"x-csrf-token": admin_csrf}
    )
    assert blocked.status_code == 409

    audits = db.query(AuditLog).all()
    assert any(entry.action == "job_retried" for entry in audits)


def test_sync_skips_completion_when_cups_unavailable(db: Session) -> None:
    user = User(
        username="echo",
        username_normalized="echo",
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.USER,
        is_active=True,
        daily_page_quota=10,
        weekly_page_quota=20,
    )
    db.add(user)
    db.flush()
    job = PrintJob(
        user_id=user.id,
        original_filename="doc.pdf",
        stored_filename="stored.pdf",
        mime_type="application/pdf",
        extension=".pdf",
        page_count=1,
        copies=1,
        status=PrintJobStatus.QUEUED,
        cups_job_id="123",
    )
    db.add(job)
    db.commit()

    class FailingCups:
        def fetch_job_states(self):  # type: ignore[no-untyped-def]
            return None

    updated = sync_queued_jobs_from_cups(db=db, cups_service=FailingCups())  # type: ignore[arg-type]
    db.refresh(job)
    assert updated == 0
    assert job.status == PrintJobStatus.QUEUED
