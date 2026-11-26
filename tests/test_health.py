from unittest.mock import patch


def test_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["trading"] == {"mode": "paper", "live_trading_enabled": False}
    assert "X-Request-ID" in r.headers


def test_readiness_db_ok_redis_down_is_degraded(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "unavailable"
    assert body["status"] == "degraded"


def test_readiness_all_ok_when_redis_up(client):
    with patch("backend.app.api.routes.health.check_redis", return_value={"status": "ok"}):
        r = client.get("/health/ready")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_readiness_returns_503_when_db_down(client):
    with patch("backend.app.api.routes.health.check_database",
               return_value={"status": "unavailable", "error": "OperationalError"}):
        r = client.get("/health/ready")
    assert r.status_code == 503
    assert r.json()["status"] == "unavailable"


def test_openapi_docs_available(client):
    assert client.get("/docs").status_code == 200
    assert "/health" in client.get("/openapi.json").json()["paths"]
