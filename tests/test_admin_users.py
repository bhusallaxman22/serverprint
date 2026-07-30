from __future__ import annotations

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_last_admin_cannot_be_disabled(client: TestClient) -> None:
    csrf = _login(client, "admin", "admin123456")
    me = client.get("/auth/me")
    user_id = me.json()["id"]
    response = client.patch(
        f"/admin/users/{user_id}",
        json={"is_active": False},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 409


def test_last_admin_cannot_be_disabled_from_web_form(client: TestClient) -> None:
    csrf = _login(client, "admin", "admin123456")
    me = client.get("/auth/me")
    user_id = me.json()["id"]
    response = client.post(
        f"/ui/admin/users/{user_id}/update",
        data={
            "search": "",
            "role_filter": "all",
            "show_inactive": "true",
            "role": "user",
            "daily_page_quota": "250",
            "weekly_page_quota": "1000",
        },
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 200
    me_after = client.get("/auth/me")
    assert me_after.json()["role"] == "admin"
