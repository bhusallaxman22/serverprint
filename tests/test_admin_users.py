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
            "print_mode": "bw",
        },
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 200
    me_after = client.get("/auth/me")
    assert me_after.json()["role"] == "admin"


def test_admin_can_create_user_via_api(client: TestClient) -> None:
    csrf = _login(client, "admin", "admin123456")
    response = client.post(
        "/admin/users",
        json={
            "username": "printer.user",
            "password": "password123",
            "role": "user",
            "requires_approval": True,
            "print_mode": "bw",
            "daily_page_quota": 100,
            "weekly_page_quota": 400,
        },
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "printer.user"
    assert body["requires_approval"] is True


def test_admin_can_create_user_via_web_form(client: TestClient) -> None:
    _login(client, "admin", "admin123456")
    response = client.post(
        "/ui/admin/users/create",
        data={
            "username": "carol",
            "password": "password123",
            "role": "user",
            "is_active": "true",
            "requires_approval": "true",
            "print_mode": "color",
            "daily_page_quota": "80",
            "weekly_page_quota": "300",
            "search": "",
            "role_filter": "all",
            "show_inactive": "true",
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "carol" in response.text
    assert "Created user carol" in response.headers.get("HX-Trigger", "")


def test_duplicate_username_rejected(client: TestClient) -> None:
    csrf = _login(client, "admin", "admin123456")
    first = client.post(
        "/admin/users",
        json={"username": "dupuser", "password": "password123"},
        headers={"x-csrf-token": csrf},
    )
    assert first.status_code == 201
    second = client.post(
        "/admin/users",
        json={"username": "DupUser", "password": "password123"},
        headers={"x-csrf-token": csrf},
    )
    assert second.status_code == 409
