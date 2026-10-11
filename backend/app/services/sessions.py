"""Persistence helpers shared by the API and the agent nodes (sessions, products, events)."""

from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.database.database import SessionLocal
from app.database.models import AgentEvent, Product, ShoppingSession
from app.utils.helpers import new_session_id

# Statuses that mean the agent is not going to do anything further without the user.
TERMINAL_STATUSES = {"completed", "cancelled", "failed", "no_results", "needs_clarification"}


def create_session(query: str) -> str:
    session_id = new_session_id()
    with SessionLocal() as db:
        db.add(ShoppingSession(id=session_id, user_query=query, state={"run": 0, "messages": []}))
        db.commit()
    return session_id


def session_exists(session_id: str) -> bool:
    with SessionLocal() as db:
        return db.get(ShoppingSession, session_id) is not None


def update_session(
    session_id: str,
    *,
    status: str | None = None,
    current_step: str | None = None,
    requirements: dict | None = None,
    **state_fields: Any,
) -> None:
    with SessionLocal() as db:
        row = db.get(ShoppingSession, session_id)
        if row is None:
            return
        if status is not None:
            row.status = status
        if current_step is not None:
            row.current_step = current_step
        if requirements is not None:
            row.requirements = requirements
        if state_fields:
            row.state = {**(row.state or {}), **state_fields}
        db.commit()


def get_state_value(session_id: str, key: str, default: Any = None) -> Any:
    with SessionLocal() as db:
        row = db.get(ShoppingSession, session_id)
        return (row.state or {}).get(key, default) if row else default


def append_message(session_id: str, role: str, content: str) -> None:
    with SessionLocal() as db:
        row = db.get(ShoppingSession, session_id)
        if row is None:
            return
        messages = list((row.state or {}).get("messages", []))
        messages.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat() + "Z"})
        row.state = {**(row.state or {}), "messages": messages}
        db.commit()


def emit_event(session_id: str, step: str, message: str, status: str = "done") -> None:
    with SessionLocal() as db:
        db.add(AgentEvent(session_id=session_id, step=step, message=message, status=status))
        db.commit()


def list_events(session_id: str, after_id: int = 0) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(AgentEvent).where(AgentEvent.session_id == session_id, AgentEvent.id > after_id).order_by(AgentEvent.id)
        ).all()
        return [
            {
                "id": r.id,
                "session_id": r.session_id,
                "step": r.step,
                "message": r.message,
                "status": r.status,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ]


def save_products(session_id: str, products: list[dict], shortlisted_ids: set[str] | None = None) -> None:
    shortlisted_ids = shortlisted_ids or set()
    with SessionLocal() as db:
        for p in products:
            db.add(
                Product(
                    id=p["id"],
                    session_id=session_id,
                    name=p["name"],
                    price=p["price"],
                    url=p.get("url", ""),
                    specifications=p.get("specs", {}),
                    rating=p.get("rating", 0.0),
                    review_count=p.get("review_count", 0),
                    source=p.get("source", ""),
                    shortlisted=1 if p["id"] in shortlisted_ids else 0,
                )
            )
        db.commit()


def clear_products(session_id: str) -> None:
    with SessionLocal() as db:
        for row in db.scalars(select(Product).where(Product.session_id == session_id)).all():
            db.delete(row)
        db.commit()


def session_view(session_id: str) -> dict | None:
    with SessionLocal() as db:
        row = db.get(ShoppingSession, session_id)
        if row is None:
            return None
        s = row.state or {}
        return {
            "id": row.id,
            "query": row.user_query,
            "status": row.status,
            "current_step": row.current_step,
            "requirements": row.requirements or {},
            "search_count": s.get("search_count", 0),
            "shortlisted_products": s.get("shortlisted_products", []),
            "comparison": s.get("comparison", {}),
            "review_analysis": s.get("review_analysis", {}),
            "recommendation": s.get("recommendation", {}),
            "cart_state": s.get("cart_state", {}),
            "browser_state": s.get("browser_state", {}),
            "near_misses": s.get("near_misses", []),
            "messages": s.get("messages", []),
            "error": s.get("error"),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


def list_sessions(limit: int = 50) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(select(ShoppingSession).order_by(ShoppingSession.created_at.desc()).limit(limit)).all()
        out = []
        for r in rows:
            rec = (r.state or {}).get("recommendation", {}) or {}
            product = rec.get("product") or {}
            out.append(
                {
                    "id": r.id,
                    "query": r.user_query,
                    "status": r.status,
                    "current_step": r.current_step,
                    "product_name": product.get("name"),
                    "price": product.get("price"),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return out
