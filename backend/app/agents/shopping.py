"""Shopping execution: runs the Playwright flow for an approved product."""

from app.services import sessions
from app.tools.playwright_tool import run_shopping


def execute_shopping(session_id: str, product: dict, accept_price_change: bool = False) -> dict:
    def emit(step: str, message: str) -> None:
        sessions.emit_event(session_id, step, message, "done")

    return run_shopping(session_id, product, emit, accept_price_change=accept_price_change)
