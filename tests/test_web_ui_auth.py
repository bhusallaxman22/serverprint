from __future__ import annotations

from fastapi.testclient import TestClient


def test_unauthenticated_admin_dashboard_redirects_to_login(client: TestClient) -> None:
    response = client.get("/ui/admin/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login"


def test_admin_dashboard_renders_after_login(client: TestClient) -> None:
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123456"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    assert login.headers.get("location") == "/ui/admin/dashboard"

    dashboard = client.get("/ui/admin/dashboard")
    assert dashboard.status_code == 200
    assert "Pending approvals" in dashboard.text


def test_related_admin_pages_render_after_login(client: TestClient) -> None:
    client.post("/login", data={"username": "admin", "password": "admin123456"})
    for path in ("/ui/admin/users", "/ui/admin/jobs", "/ui/admin/audit"):
        response = client.get(path)
        assert response.status_code == 200, path
