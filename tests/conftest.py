from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

import app.database as database
from app.config import get_settings
from app.database import reset_engine
from app.dependencies import _rate_limiter


@pytest.fixture(autouse=True)
def test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    uploads_path = tmp_path / "uploads"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("UPLOADS_ROOT", str(uploads_path))
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("PRINT_API_KEY", "test-api-key")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123456")
    monkeypatch.setenv("TZ", "UTC")
    get_settings.cache_clear()
    settings = get_settings()
    reset_engine(settings.database_url)
    _rate_limiter.clear()
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    yield


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def db() -> Session:
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def png_bytes() -> bytes:
    image = Image.new("RGB", (10, 10), color="black")
    data = BytesIO()
    image.save(data, format="PNG")
    return data.getvalue()
