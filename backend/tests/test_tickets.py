from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(monkeypatch, email: str) -> dict[str, str]:
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "localhost")
    request = client.post("/api/auth/request-otp", json={"email": email})
    assert request.status_code == 200, request.text
    code = request.json()["otp"]
    verify = client.post("/api/auth/verify-otp", json={"email": email, "code": code})
    assert verify.status_code == 200, verify.text
    return {"Authorization": f"Bearer {verify.json()['token']}"}


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_ticket_and_list(monkeypatch) -> None:
    headers = auth_headers(monkeypatch, "tickets-list@example.com")
    payload = {
        "customer_name": "Rahul Sharma",
        "customer_email": "rahul@example.com",
        "subject": "Order delayed",
        "description": "Tracking has not updated for five days.",
    }
    create_response = client.post("/api/tickets", json=payload, headers=headers)
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert "ticket_id" in created

    list_response = client.get("/api/tickets", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1


def test_ticket_not_found(monkeypatch) -> None:
    headers = auth_headers(monkeypatch, "ticket-not-found@example.com")
    response = client.get("/api/tickets/TKT-99999", headers=headers)
    assert response.status_code == 404


def test_invalid_ticket_request(monkeypatch) -> None:
    headers = auth_headers(monkeypatch, "invalid-ticket@example.com")
    response = client.post(
        "/api/tickets",
        json={
            "customer_name": "",
            "customer_email": "bad-email",
            "subject": "",
            "description": "",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_status_filter_and_search(monkeypatch) -> None:
    headers = auth_headers(monkeypatch, "status-filter@example.com")
    create = client.post(
        "/api/tickets",
        json={
            "customer_name": "Alice Patient",
            "customer_email": "alice@example.com",
            "subject": "Refund issue",
            "description": "Need a refund update after purchase.",
        },
        headers=headers,
    )
    ticket_id = create.json()["ticket_id"]

    list_all = client.get("/api/tickets", headers=headers)
    assert list_all.status_code == 200

    filtered = client.get(f"/api/tickets?search=alice&status=Open", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1

    detail = client.get(f"/api/tickets/{ticket_id}", headers=headers)
    assert detail.status_code == 200

    update = client.put(
        f"/api/tickets/{ticket_id}",
        json={"status": "In Progress", "notes": "Customer contacted, investigating."},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["success"] is True


def test_request_otp_returns_dev_code_when_email_delivery_is_disabled(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "localhost")
    response = client.post("/api/auth/request-otp", json={"email": "kanoujiyadeepak19@gmail.com"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "otp" in body
    assert len(str(body["otp"])) == 6


def test_request_otp_reuses_cooldown_message(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "localhost")
    email = "cooldown@example.com"
    first = client.post("/api/auth/request-otp", json={"email": email})
    assert first.status_code == 200, first.text

    second = client.post("/api/auth/request-otp", json={"email": email})
    assert second.status_code == 429, second.text
    assert "Please wait" in second.json()["detail"]


def test_logout_invalidates_session(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "localhost")
    email = "logout@example.com"
    code = "123456"

    request = client.post("/api/auth/request-otp", json={"email": email})
    assert request.status_code == 200, request.text
    body = request.json()
    if "otp" in body:
        code = str(body["otp"])

    verify = client.post("/api/auth/verify-otp", json={"email": email, "code": code})
    assert verify.status_code == 200, verify.text
    token = verify.json()["token"]

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200, logout.text

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401
