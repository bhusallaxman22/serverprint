from __future__ import annotations

from fastapi.testclient import TestClient


def test_login_sets_session_and_csrf(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin123456"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["csrf_token"]
    assert payload["user"]["username"] == "admin"
    assert payload["user"]["print_mode"] in {"bw", "color"}

    me = client.get("/auth/me")
    assert me.status_code == 200


def test_logout_requires_csrf(client: TestClient) -> None:
    login = client.post("/auth/login", json={"username": "admin", "password": "admin123456"})
    csrf = login.json()["csrf_token"]
    denied = client.post("/auth/logout")
    assert denied.status_code == 403

    ok = client.post("/auth/logout", headers={"x-csrf-token": csrf})
    assert ok.status_code == 200
