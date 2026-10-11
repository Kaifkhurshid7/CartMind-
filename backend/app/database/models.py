from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ShoppingSession(Base):
    __tablename__ = "shopping_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_query: Mapped[str] = mapped_column(Text)
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="started")
    current_step: Mapped[str] = mapped_column(String(60), default="start")
    # Everything else the UI needs (comparison, recommendation, chat, cart, ...).
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Product(Base):
    __tablename__ = "products"

    pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("shopping_sessions.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    price: Mapped[float] = mapped_column(Float)
    url: Mapped[str] = mapped_column(String(500), default="")
    specifications: Mapped[dict] = mapped_column(JSON, default=dict)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(60), default="")
    shortlisted: Mapped[int] = mapped_column(Integer, default=0)


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("shopping_sessions.id"), index=True)
    step: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="done")  # done | running | waiting | error
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
