"""Database models for every entity in the platform spec (Step 8).

Money/price columns use Numeric (never float) to avoid rounding errors.
Every table that can hold trading data has an `is_simulated` flag so
paper-trading records can never be confused with real ones.
"""
import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (JSON, Boolean, DateTime, Enum, ForeignKey, Index, Integer,
                        Numeric, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.session import Base

MONEY = Numeric(18, 4)
QTY = Numeric(20, 8)  # crypto needs fractional quantities


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow,
                                                 onupdate=utcnow, nullable=False)


# ---------- Enums ----------
class AssetClass(str, enum.Enum):
    EQUITY = "equity"; FUTURE = "future"; OPTION = "option"; CRYPTO = "crypto"; FOREX = "forex"

class Side(str, enum.Enum):
    BUY = "BUY"; SELL = "SELL"

class OrderType(str, enum.Enum):
    MARKET = "MARKET"; LIMIT = "LIMIT"; SL = "SL"; SL_M = "SL-M"

class OrderAction(str, enum.Enum):
    PLACE = "place"; MODIFY = "modify"; CANCEL = "cancel"; CLOSE = "close"

class OrderStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"; APPROVED = "approved"; SUBMITTED = "submitted"
    FILLED = "filled"; PARTIALLY_FILLED = "partially_filled"; CANCELLED = "cancelled"; REJECTED = "rejected"

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"; APPROVED = "approved"; REJECTED = "rejected"
    EXPIRED = "expired"; USED = "used"; INVALIDATED = "invalidated"

class TradingMode(str, enum.Enum):
    PAPER = "paper"; LIVE = "live"

class SignalStatus(str, enum.Enum):
    NEW = "new"; VALIDATED = "validated"; REJECTED = "rejected"; EXPIRED = "expired"; ACTED_ON = "acted_on"


def _enum(e):  # store enum values as plain strings, portable across databases
    return Enum(e, native_enum=False, length=32, values_callable=lambda x: [m.value for m in x])


# ---------- Models ----------
class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    broker_accounts: Mapped[list["BrokerAccount"]] = relationship(back_populates="user")


class BrokerAccount(TimestampMixin, Base):
    """Broker credentials are NOT stored here in plain text; only a reference
    to an encrypted secret (implemented in the broker-integration stage)."""
    __tablename__ = "broker_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    broker: Mapped[str] = mapped_column(String(32), nullable=False)  # paper, zerodha, upstox, angelone
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[TradingMode] = mapped_column(_enum(TradingMode), default=TradingMode.PAPER, nullable=False)
    credentials_ref: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user: Mapped[User] = relationship(back_populates="broker_accounts")


class Instrument(TimestampMixin, Base):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("exchange", "symbol", name="uq_instrument_exchange_symbol"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(_enum(AssetClass), nullable=False)
    lot_size: Mapped[Decimal] = mapped_column(QTY, default=1, nullable=False)
    tick_size: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.05"), nullable=False)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    strike: Mapped[Decimal | None] = mapped_column(MONEY)
    option_type: Mapped[str | None] = mapped_column(String(2))  # CE / PE
    is_tradable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MarketData(Base):
    __tablename__ = "market_data"
    __table_args__ = (UniqueConstraint("instrument_id", "timeframe", "ts", name="uq_candle"),
                      Index("ix_market_data_lookup", "instrument_id", "timeframe", "ts"))
    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)  # 1m, 5m, 1d...
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    high: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    low: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    close: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    volume: Mapped[Decimal] = mapped_column(QTY, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # where the data came from
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Strategy(TimestampMixin, Base):
    __tablename__ = "strategies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AgentAnalysis(Base):
    __tablename__ = "agent_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"))
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, nullable=False)  # validated structured output
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TradingSignal(TimestampMixin, Base):
    __tablename__ = "trading_signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id"))
    side: Mapped[Side] = mapped_column(_enum(Side), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    target_price: Mapped[Decimal | None] = mapped_column(MONEY)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    rationale: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[SignalStatus] = mapped_column(_enum(SignalStatus), default=SignalStatus.NEW, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RiskCheck(Base):
    __tablename__ = "risk_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("trading_signals.id"))
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(QTY)
    max_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    estimated_costs: Mapped[Decimal | None] = mapped_column(MONEY)
    checks: Mapped[dict] = mapped_column(JSON, nullable=False)  # each rule and its result
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ApprovalRequest(TimestampMixin, Base):
    """Approval is bound to a hash of the exact order payload. Only a hash of the
    single-use token is stored; the raw token is shown to the user once."""
    __tablename__ = "approval_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    action: Mapped[OrderAction] = mapped_column(_enum(OrderAction), nullable=False)
    order_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    max_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    status: Mapped[ApprovalStatus] = mapped_column(_enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    broker_account_id: Mapped[int | None] = mapped_column(ForeignKey("broker_accounts.id"))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    approval_request_id: Mapped[int | None] = mapped_column(ForeignKey("approval_requests.id"), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # duplicate prevention
    mode: Mapped[TradingMode] = mapped_column(_enum(TradingMode), default=TradingMode.PAPER, nullable=False)
    side: Mapped[Side] = mapped_column(_enum(Side), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(_enum(OrderType), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(MONEY)
    stop_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus), default=OrderStatus.PENDING_APPROVAL, nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(QTY, default=0, nullable=False)
    avg_fill_price: Mapped[Decimal | None] = mapped_column(MONEY)
    fees: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String(64))
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Position(TimestampMixin, Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    side: Mapped[Side] = mapped_column(_enum(Side), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CompletedTrade(Base):
    __tablename__ = "completed_trades"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    side: Mapped[Side] = mapped_column(_enum(Side), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    exit_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    gross_pnl: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    fees: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    net_pnl: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PerformanceReport(Base):
    __tablename__ = "performance_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id"))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    """Append-only. Application code should only ever INSERT into this table."""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)  # user / agent / system
    actor_id: Mapped[str | None] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
