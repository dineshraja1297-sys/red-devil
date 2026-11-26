"""Test setup: a throwaway SQLite database so tests run without Docker.
Redis is pointed at a closed port so the 'redis down' path is exercised."""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6399/0"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-use"
os.environ["ENVIRONMENT"] = "test"
os.environ["TRADING_MODE"] = "paper"
os.environ["LIVE_TRADING_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from database import models  # noqa: E402,F401
from database.session import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from backend.app.main import app
    with TestClient(app) as c:
        yield c
