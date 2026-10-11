"""Shopping execution: runs the Playwright flow for an approved product."""

from app.config import get_settings
from app.services import handoff, sessions
from app.tools.browser_agent import shop_with_agent
from app.tools.amazon_tool import SOURCE as AMAZON, run_amazon_shopping
from app.tools.playwright_tool import run_shopping


def execute_shopping(session_id: str, product: dict, accept_price_change: bool = False) -> dict:
    def emit(step: str, message: str) -> None:
        sessions.emit_event(session_id, step, message, "done")

    if product.get("via_agent"):

        def ask_user(message: str) -> bool:
            return handoff.request_user_action(session_id, message, get_settings().user_action_timeout)

        return shop_with_agent(session_id, product, emit, ask_user, accept_price_change=accept_price_change)
    runner = run_amazon_shopping if product.get("source") == AMAZON else run_shopping
    return runner(session_id, product, emit, accept_price_change=accept_price_change)
