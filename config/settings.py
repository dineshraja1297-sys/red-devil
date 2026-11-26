"""Central configuration, loaded from environment variables / .env."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Red Devil"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str = Field(..., min_length=16)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, gt=0, le=1440)
    JWT_ALGORITHM: str = "HS256"

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    TRADING_MODE: Literal["paper", "live"] = "paper"
    LIVE_TRADING_ENABLED: bool = False

    INITIAL_CAPITAL_INR: float = Field(10000, gt=0)
    MAX_RISK_PER_TRADE_PCT: float = Field(0.5, gt=0, le=100)
    MAX_DAILY_LOSS_PCT: float = Field(1.0, gt=0, le=100)
    MAX_LEVERAGE: float = Field(1.0, ge=1)
    MAX_OPEN_POSITIONS: int = Field(2, ge=1)

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("SECRET_KEY")
    @classmethod
    def reject_default_secret(cls, v: str) -> str:
        if v.startswith("change-me"):
            raise ValueError("SECRET_KEY is still the placeholder from .env.example; generate a real one.")
        return v

    @model_validator(mode="after")
    def lock_live_trading(self) -> "Settings":
        # Hard lock for Stage 1: live trading cannot be switched on by config.
        if self.LIVE_TRADING_ENABLED or self.TRADING_MODE == "live":
            raise ValueError(
                "Live trading is locked. It stays disabled until the human approval "
                "gateway and its integration tests are complete."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
