"""The CartMind LangGraph workflow."""

import sqlite3
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.state import ShoppingState
from app.config import get_settings
from app.utils.logging import get_logger

log = get_logger("graph")


def build_graph(checkpointer=None):
    g = StateGraph(ShoppingState)
    for name, fn in {
        "requirements": nodes.requirement_node,
        "validate": nodes.validate_node,
        "research": nodes.research_node,
        "filter": nodes.filter_node,
        "replan": nodes.replanning_node,
        "compare": nodes.comparison_node,
        "reviews": nodes.review_node,
        "select": nodes.select_node,
        "recommend": nodes.recommendation_node,
        "approval_request": nodes.approval_request_node,
        "approval": nodes.approval_node,
        "cancel": nodes.cancel_node,
        "shop": nodes.shopping_node,
        "fallback": nodes.fallback_node,
        "failed": nodes.failed_node,
        "price_request": nodes.price_change_request_node,
        "price_confirm": nodes.price_confirm_node,
    }.items():
        g.add_node(name, fn)

    g.add_edge(START, "requirements")
    g.add_edge("requirements", "validate")
    g.add_conditional_edges("validate", nodes.route_after_validate, {"research": "research", "end": END})
    g.add_edge("research", "filter")
    g.add_conditional_edges("filter", nodes.route_after_filter, {"compare": "compare", "replan": "replan"})
    g.add_edge("replan", END)
    g.add_edge("compare", "reviews")
    g.add_edge("reviews", "select")
    g.add_conditional_edges("select", nodes.route_after_select, {"recommend": "recommend", "end": END})
    g.add_edge("recommend", "approval_request")
    g.add_edge("approval_request", "approval")
    g.add_conditional_edges("approval", nodes.route_after_approval, {"shop": "shop", "cancel": "cancel"})
    g.add_edge("cancel", END)
    g.add_conditional_edges(
        "shop",
        nodes.route_after_shopping,
        {"end": END, "price_change": "price_request", "fallback": "fallback", "failed": "failed"},
    )
    g.add_edge("fallback", "select")
    g.add_edge("failed", END)
    g.add_edge("price_request", "price_confirm")
    g.add_conditional_edges("price_confirm", nodes.route_after_price_confirm, {"shop": "shop", "cancel": "cancel"})
    return g.compile(checkpointer=checkpointer)


def _checkpointer():
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        conn = sqlite3.connect(get_settings().checkpoint_db, check_same_thread=False)
        return SqliteSaver(conn)
    except Exception as exc:  # noqa: BLE001
        from langgraph.checkpoint.memory import MemorySaver

        log.warning("SQLite checkpointer unavailable (%s); using in-memory checkpoints", exc)
        return MemorySaver()


@lru_cache
def get_graph():
    return build_graph(_checkpointer())
