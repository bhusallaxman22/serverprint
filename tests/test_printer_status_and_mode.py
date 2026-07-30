from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.cups_service import CUPSService


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_print_mode_persists_on_update(client: TestClient) -> None:
    csrf = _login(client, "admin", "admin123456")
    update = client.patch(
        "/api/v1/me/print-mode",
        json={"print_mode": "color"},
        headers={"x-csrf-token": csrf},
    )
    assert update.status_code == 200
    assert update.json()["print_mode"] == "color"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["print_mode"] == "color"


def test_printer_status_contract_has_explicit_nullables(client: TestClient, monkeypatch) -> None:
    csrf = _login(client, "admin", "admin123456")

    monkeypatch.setattr(CUPSService, "check_printer_reachability", lambda self: (False, "offline"))
    response = client.get("/api/v1/printer/status", headers={"x-csrf-token": csrf})
    assert response.status_code == 200
    payload = response.json()
    assert payload["health"] == "offline"
    assert payload["queue_depth"] is None
    assert payload["toner_percent"] is None
    assert payload["paper_percent"] is None
    assert payload["unavailable_reason"] == "offline"
