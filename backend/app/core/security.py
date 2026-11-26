"""Password hashing and JWT access tokens (authentication foundation)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config.settings import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": now,
               "exp": now + timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES), "type": "access"}
    return jwt.encode(payload, s.SECRET_KEY, algorithm=s.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    payload = jwt.decode(token, s.SECRET_KEY, algorithms=[s.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return payload
