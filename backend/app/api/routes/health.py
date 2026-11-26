"""Health endpoints.

/health        liveness: the process is up (no dependencies checked).
/health/ready  readiness: checks PostgreSQL (required) and Redis (reported).
"""
import logging
import time

import redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from config.settings import get_settings
from database.session import engine

router = APIRouter(tags=["health"])
log = logging.getLogger("app.health")


def _trading_info() -> dict:
    s = get_settings()
    return {"mode": s.TRADING_MODE, "live_trading_enabled": s.LIVE_TRADING_ENABLED}


@router.get("/health", summary="Liveness check")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "app": s.APP_NAME, "version": s.APP_VERSION,
            "environment": s.ENVIRONMENT, "trading": _trading_info()}


def check_database() -> dict:
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.perf_counter() - start) * 1000, 2)}
    except Exception as exc:  # report, don't crash
        log.warning("Database health check failed: %s", exc)
        return {"status": "unavailable", "error": type(exc).__name__}


def check_redis() -> dict:
    start = time.perf_counter()
    try:
        client = redis.Redis.from_url(get_settings().REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        client.close()
        return {"status": "ok", "latency_ms": round((time.perf_counter() - start) * 1000, 2)}
    except Exception as exc:
        log.warning("Redis health check failed: %s", exc)
        return {"status": "unavailable", "error": type(exc).__name__}


@router.get("/health/ready", summary="Readiness check (database + Redis)")
def readiness(response: Response) -> dict:
    db, cache = check_database(), check_redis()
    if db["status"] != "ok":
        overall = "unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif cache["status"] != "ok":
        overall = "degraded"   # app can run; caching features will be limited
    else:
        overall = "ok"
    return {"status": overall, "checks": {"database": db, "redis": cache}, "trading": _trading_info()}
