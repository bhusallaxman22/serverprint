from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.security import hash_password
from app.services.cups_service import CUPSService


def test_external_api_requires_key(client: TestClient, db: Session, png_bytes: bytes) -> None:
    user = User(
        username="alice",
        username_normalized="alice",
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.USER,
        is_active=True,
        daily_page_quota=5,
        weekly_page_quota=10,
    )
    db.add(user)
    db.commit()

    files = {"file": ("sample.png", png_bytes, "image/png")}
    data = {"username": "alice", "copies": 1}

    denied = client.post(
        "/api/v1/print", data=data, files=files, headers={"x-print-api-key": "bad"}
    )
    assert denied.status_code == 401

    ok = client.post(
        "/api/v1/print",
        data=data,
        files=files,
        headers={"x-print-api-key": "test-api-key"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "pending"


def test_external_api_automatic_user_prints_immediately(
    client: TestClient, db: Session, png_bytes: bytes, monkeypatch
) -> None:
    user = User(
        username="autouser",
        username_normalized="autouser",
        password_hash=hash_password("StrongPassword123"),
        role=UserRole.USER,
        is_active=True,
        requires_approval=False,
        daily_page_quota=5,
        weekly_page_quota=10,
    )
    db.add(user)
    db.commit()

    monkeypatch.setattr(CUPSService, "submit_job", lambda self, file_path, title, copies: "901")
    response = client.post(
        "/api/v1/print",
        data={"username": "autouser", "copies": 1},
        files={"file": ("auto.png", png_bytes, "image/png")},
        headers={"x-print-api-key": "test-api-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
