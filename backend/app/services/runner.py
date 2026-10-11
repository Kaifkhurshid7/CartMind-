"""Runs the LangGraph workflow for a session (called from FastAPI background tasks / worker threads)."""

from langgraph.types import Command

from app.agents.graph import get_graph
from app.services import handoff, sessions
from app.utils.logging import get_logger

log = get_logger("runner")

WAITING_STATUSES = ("waiting_for_approval", "price_changed")


def _config(session_id: str) -> dict:
    run = sessions.get_state_value(session_id, "run", 1)
    return {"configurable": {"thread_id": f"{session_id}:{run}"}, "recursion_limit": 60}


def _invoke(session_id: str, graph_input, config: dict) -> None:
    try:
        get_graph().invoke(graph_input, config)
    except Exception as exc:  # noqa: BLE001
        log.exception("Agent run failed for %s", session_id)
        message = f"Something went wrong while running the agent: {exc.__class__.__name__}: {exc}"
        sessions.update_session(session_id, status="failed", current_step="failed", error=message)
        sessions.emit_event(session_id, "error", message, "error")


def start_run(session_id: str, query: str, requirements: dict | None = None, refinement: str | None = None) -> None:
    """Begin (or restart, for replanning) the workflow. A fresh checkpoint thread is used for each run."""
    run = sessions.get_state_value(session_id, "run", 0) + 1
    sessions.update_session(session_id, status="running", current_step="start", run=run, error=None, near_misses=[])
    graph_input = {"session_id": session_id, "user_query": query, "requirements": requirements or {},
                   "refinement": refinement}
    _invoke(session_id, graph_input, _config(session_id))


def resume_run(session_id: str, value: dict) -> None:
    _invoke(session_id, Command(resume=value), _config(session_id))


def cancel(session_id: str) -> None:
    """Cancel a session. If the graph is paused at a human checkpoint, resume it with a refusal."""
    if handoff.abort(session_id):  # the agent is waiting for the user; it stops and the graph ends
        return
    view = sessions.session_view(session_id)
    if view and view["status"] in WAITING_STATUSES:
        resume_run(session_id, {"approved": False})
    elif view and view["status"] not in sessions.TERMINAL_STATUSES:
        sessions.update_session(session_id, status="cancelled", current_step="cancelled")
        sessions.emit_event(session_id, "approval", "Cancelled", "error")
