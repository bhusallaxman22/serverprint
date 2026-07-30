from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.print_job import PrintJobStatus
from app.models.user import User, UserRole
from app.security import hash_password


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_quota_blocks_and_releases_on_rejected(
    client: TestClient, db: Session, png_bytes: bytes
) -> None:
    user = User(
        username="bob",
        username_normalized="bob",
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.USER,
        is_active=True,
        daily_page_quota=1,
        weekly_page_quota=2,
    )
    db.add(user)
    db.commit()
    csrf = _login(client, "bob", "StrongPassword123")

    files = {"file": ("job1.png", png_bytes, "image/png")}
    first = client.post(
        "/jobs/upload", data={"copies": 1}, files=files, headers={"x-csrf-token": csrf}
    )
    assert first.status_code == 200

    second = client.post(
        "/jobs/upload", data={"copies": 1}, files=files, headers={"x-csrf-token": csrf}
    )
    assert second.status_code == 409

    job_uuid = first.json()["job_uuid"]
    admin_csrf = _login(client, "admin", "admin123456")
    rejected = client.post(
        f"/admin/jobs/{job_uuid}/reject",
        json={"reason": "Invalid document"},
        headers={"x-csrf-token": admin_csrf},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == PrintJobStatus.REJECTED.value

    csrf = _login(client, "bob", "StrongPassword123")
    third = client.post(
        "/jobs/upload", data={"copies": 1}, files=files, headers={"x-csrf-token": csrf}
    )
    assert third.status_code == 200
