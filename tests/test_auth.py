from sqlalchemy import select

from database.models import AuditLog

PW = "a-strong-password-123"


def _register(client, email="trader@example.com"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": PW})


def _login(client, email="trader@example.com", password=PW):
    return client.post("/api/v1/auth/token", data={"username": email, "password": password})


def test_register_login_me(client):
    assert _register(client).status_code == 201
    token = _login(client).json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["email"] == "trader@example.com"


def test_password_not_returned(client):
    assert "password_hash" not in _register(client).json()


def test_duplicate_email_rejected(client):
    _register(client)
    r = _register(client, "TRADER@example.com")
    assert r.status_code == 409


def test_wrong_password_rejected_and_audited(client, db):
    _register(client)
    assert _login(client, password="wrong-password-xx").status_code == 401
    events = db.scalars(select(AuditLog.event)).all()
    assert "auth.login_failed" in events and "user.registered" in events


def test_me_requires_valid_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_weak_password_gives_structured_validation_error(client):
    r = client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
