from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from config.settings import Settings
from database.models import AssetClass, Instrument, Order, OrderType, Side, User
from database.session import Base

BASE = dict(SECRET_KEY="x" * 32, DATABASE_URL="sqlite://")


def test_live_trading_cannot_be_enabled():
    with pytest.raises(ValidationError, match="Live trading is locked"):
        Settings(**BASE, LIVE_TRADING_ENABLED=True)
    with pytest.raises(ValidationError, match="Live trading is locked"):
        Settings(**BASE, TRADING_MODE="live")


def test_placeholder_secret_rejected():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="change-me-to-a-long-random-string", DATABASE_URL="sqlite://")


def test_risk_defaults_match_spec():
    s = Settings(**BASE)
    assert (s.MAX_RISK_PER_TRADE_PCT, s.MAX_DAILY_LOSS_PCT, s.MAX_LEVERAGE, s.MAX_OPEN_POSITIONS) == (0.5, 1.0, 1.0, 2)


def test_all_spec_tables_exist():
    expected = {"users", "broker_accounts", "instruments", "market_data", "agent_analyses",
                "trading_signals", "strategies", "risk_checks", "approval_requests", "orders",
                "positions", "completed_trades", "performance_reports", "audit_logs"}
    assert expected <= set(Base.metadata.tables)


def _seed(db):
    user = User(email="u@example.com", password_hash="x")
    inst = Instrument(symbol="INFY", exchange="NSE", asset_class=AssetClass.EQUITY)
    db.add_all([user, inst]); db.commit()
    return user, inst


def test_order_defaults_to_simulated_and_decimal_preserved(db):
    user, inst = _seed(db)
    o = Order(user_id=user.id, instrument_id=inst.id, idempotency_key="k1", side=Side.BUY,
              order_type=OrderType.LIMIT, quantity=Decimal("3"), price=Decimal("1520.45"))
    db.add(o); db.commit(); db.refresh(o)
    assert o.is_simulated is True and o.mode.value == "paper"
    assert o.price == Decimal("1520.4500")


def test_duplicate_idempotency_key_rejected(db):
    user, inst = _seed(db)
    kw = dict(user_id=user.id, instrument_id=inst.id, idempotency_key="dup",
              side=Side.BUY, order_type=OrderType.MARKET, quantity=Decimal("1"))
    db.add(Order(**kw)); db.commit()
    db.add(Order(**kw))
    with pytest.raises(IntegrityError):
        db.commit()
