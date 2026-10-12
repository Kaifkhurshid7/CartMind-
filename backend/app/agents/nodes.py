"""LangGraph nodes. Each is a plain function: state in, partial state update out."""

from langgraph.types import interrupt

from app.agents import approval, comparison, recommendation, replanning, requirements, research, shopping
from app.agents.state import ShoppingState
from app.config import get_settings
from app.llm import prompts
from app.llm.gemini import get_llm
from app.services import sessions
from app.llm.gemini import LLMUnavailable
from app.services import handoff
from app.tools import amazon_tool
from app.tools.amazon_tool import LiveSiteError
from app.utils.helpers import format_inr


def _emit(state: ShoppingState, step: str, message: str, status: str = "done") -> None:
    sessions.emit_event(state["session_id"], step, message, status)


def _product(state: ShoppingState, product_id: str | None) -> dict | None:
    return next((p for p in state.get("shortlisted_products", []) if p["id"] == product_id), None)


# ---- understanding -------------------------------------------------------------------------------


def requirement_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    sessions.update_session(sid, status="running", current_step="requirements", error=None)
    if state.get("refinement") and state.get("requirements"):
        _emit(state, "requirements", "Updating requirements from your message")
        req = replanning.merge_requirements(state["requirements"], state["refinement"])
    else:
        _emit(state, "requirements", "Understanding your requirements")
        req = requirements.extract_requirements(state["user_query"])

    budget = req["budget"]["maximum"]
    details = [f"category: {req['category'] or '?'}"]
    if budget:
        details.append(f"budget: {format_inr(budget)}")
    details += [f"{k}: {v}" for k, v in req["requirements"].items()]
    if req["priorities"]:
        details.append("priorities: " + ", ".join(req["priorities"]))
    _emit(state, "requirements", "Extracted " + " · ".join(details))
    sessions.update_session(sid, requirements=req)
    return {"requirements": req, "current_step": "requirements", "excluded_ids": [], "error": None}


def validate_node(state: ShoppingState) -> dict:
    ok, message = requirements.validate(state["requirements"])
    if ok:
        return {"error": None}
    sid = state["session_id"]
    _emit(state, "requirements", "Need more information", "error")
    sessions.update_session(sid, status="needs_clarification", current_step="validate", error=message)
    sessions.append_message(sid, "assistant", message)
    return {"error": message}


def route_after_validate(state: ShoppingState) -> str:
    return "research" if not state.get("error") else "end"


# ---- research ------------------------------------------------------------------------------------


def research_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    sessions.update_session(sid, current_step="research")
    mode = get_settings().shopping_mode
    _emit(state, "research", {"agent": "Starting the browsing agent", "live": "Searching Amazon.in"}.get(mode, "Searching products"))

    def ask_user(message: str) -> bool:
        return handoff.request_user_action(sid, message, get_settings().user_action_timeout)

    def emit(step: str, msg: str) -> None:
        _emit(state, step, msg)

    try:
        try:
            results = research.research(state["requirements"], emit=emit, ask_user=ask_user)
        except LLMUnavailable:
            _emit(state, "research", "No AI model configured for the browsing agent, using scripted Amazon.in search", "error")
            results = amazon_tool.search_amazon(state["requirements"], emit)
    except research.AgentCancelled:
        _emit(state, "research", "Cancelled", "error")
        sessions.update_session(sid, status="cancelled", current_step="cancelled")
        return {"search_results": [], "error": "cancelled", "current_step": "research"}
    except (LiveSiteError, research.AgentFailed) as err:
        message = getattr(err, "message", None) or str(err)
        _emit(state, "research", message, "error")
        sessions.update_session(sid, status="failed", current_step="research", error=message)
        sessions.append_message(sid, "assistant", message)
        return {"search_results": [], "error": message, "current_step": "research"}
    _emit(state, "research", f"Found {len(results)} products")
    return {"search_results": results, "current_step": "research"}


def route_after_research(state: ShoppingState) -> str:
    return "end" if state.get("error") else "filter"


def filter_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    kept, rejected = research.filter_products(state["search_results"], state["requirements"])
    sessions.clear_products(sid)
    sessions.save_products(sid, state["search_results"], {p["id"] for p in kept})
    sessions.update_session(sid, current_step="filter", search_count=len(state["search_results"]))
    _emit(state, "filter", f"Filtered to {len(kept)} products that meet your mandatory requirements")
    return {"shortlisted_products": kept, "rejected_products": rejected, "current_step": "filter"}


def route_after_filter(state: ShoppingState) -> str:
    return "compare" if state["shortlisted_products"] else "replan"


def replanning_node(state: ShoppingState) -> dict:
    """Nothing satisfies every mandatory requirement: find the closest options instead of guessing."""
    sid = state["session_id"]
    near = replanning.near_misses(state["search_results"], state["requirements"])
    if near:
        lines = "; ".join(f"{n['product']['name']} ({format_inr(n['product']['price'])}) misses only: {n['fails']}" for n in near)
        message = f"No product meets every requirement. Closest options: {lines}. Want me to relax that requirement?"
    elif state.get("rejected_products"):
        rejected = state["rejected_products"]
        detail = "; ".join(f"{r['name'][:60]} ({', '.join(r['reasons'][:2])})" for r in rejected[:3])
        more = f", and {len(rejected) - 3} more" if len(rejected) > 3 else ""
        message = (
            f"I checked {len(state.get('search_results', []))} products but none passed your requirements. "
            f"Why: {detail}{more}. You can relax a requirement or raise the budget and I will search again."
        )
    else:
        message = "I couldn't find any products for that request. Try rewording it or searching for something more specific."
    _emit(state, "research", "No exact matches found", "error")
    sessions.update_session(
        sid, status="no_results", current_step="replan", near_misses=near, shortlisted_products=[],
        comparison={}, recommendation={},
    )
    sessions.append_message(sid, "assistant", message)
    return {"near_misses": near, "current_step": "replan"}


# ---- reasoning -----------------------------------------------------------------------------------


def comparison_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    _emit(state, "compare", f"Comparing {len(state['shortlisted_products'])} products")
    scored = comparison.score_products(state["shortlisted_products"], state["requirements"])[: get_settings().agent_max_products]
    table = comparison.build_comparison(scored, state["requirements"])
    sessions.update_session(sid, current_step="compare", shortlisted_products=scored, comparison=table)
    return {"shortlisted_products": scored, "comparison": table, "current_step": "compare"}


def review_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    _emit(state, "reviews", "Analyzing reviews")
    top = state["shortlisted_products"][:5]
    analysis = comparison.analyze_reviews(top, research.fetch_reviews(top))
    sessions.update_session(sid, current_step="reviews", review_analysis=analysis)
    return {"review_analysis": analysis, "current_step": "reviews"}


def select_node(state: ShoppingState) -> dict:
    excluded = set(state.get("excluded_ids", []))
    choice = next((p for p in state["shortlisted_products"] if p["id"] not in excluded), None)
    if choice is None:
        message = "None of the shortlisted products could be added to the cart. Please try a new search."
        sid = state["session_id"]
        sessions.update_session(sid, status="failed", current_step="select", error=message)
        sessions.append_message(sid, "assistant", message)
        _emit(state, "select", "No remaining options", "error")
        return {"selected_product_id": None, "error": message}
    _emit(state, "select", f"Selected best match: {choice['name']}")
    return {"selected_product_id": choice["id"], "current_step": "select"}


def route_after_select(state: ShoppingState) -> str:
    return "recommend" if state.get("selected_product_id") else "end"


def recommendation_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    selected = _product(state, state["selected_product_id"])
    rec = recommendation.build_recommendation(selected, state["shortlisted_products"], state["requirements"])
    sessions.update_session(sid, current_step="recommend", recommendation=rec, cart_state={}, error=None)
    sessions.append_message(
        sid, "assistant", f"{rec['summary']} {rec['alternative_note']}".strip(),
        meta={"type": "recommendation", "recommendation": rec, "comparison": state.get("comparison", {})},
    )
    _emit(state, "recommend", "Recommendation ready")
    return {"recommendation": rec, "current_step": "recommend"}


# ---- human in the loop ---------------------------------------------------------------------------


def approval_request_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    sessions.update_session(sid, status="waiting_for_approval", current_step="approval")
    _emit(state, "approval", "Waiting for your approval", "waiting")
    return {"current_step": "approval"}


def approval_node(state: ShoppingState) -> dict:
    product = _product(state, state["selected_product_id"])
    answer = interrupt(approval.approval_request(product))  # graph pauses here until the user decides
    approved, product_id = approval.parse_approval(answer, state["selected_product_id"])
    if not approved:
        return {"user_approval": False}
    update: dict = {"user_approval": True, "approved_product_id": product_id}
    if product_id != state["selected_product_id"] and _product(state, product_id):
        # The user picked one of the alternatives instead.
        update["selected_product_id"] = product_id
        update["recommendation"] = recommendation.build_recommendation(
            _product(state, product_id), state["shortlisted_products"], state["requirements"]
        )
        sessions.update_session(state["session_id"], recommendation=update["recommendation"])
    _emit(state, "approval", "Approval received")
    return update


def route_after_approval(state: ShoppingState) -> str:
    return "shop" if state.get("user_approval") else "cancel"


def cancel_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    sessions.update_session(sid, status="cancelled", current_step="cancelled")
    _emit(state, "approval", "Cancelled — nothing was added to your cart", "error")
    sessions.append_message(sid, "assistant", "No problem — I've cancelled and nothing was added to your cart.")
    return {"current_step": "cancelled"}


# ---- action --------------------------------------------------------------------------------------


def _explain(error: str, product: dict) -> str:
    try:
        return get_llm().invoke(
            prompts.EXPLAIN_ERROR.format(error=error, product=product["name"]), system=prompts.SYSTEM
        ).strip()
    except Exception:  # noqa: BLE001
        return error


def shopping_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    product = _product(state, state["selected_product_id"])
    sessions.update_session(sid, status="executing", current_step="shopping")
    _emit(state, "browser", "Starting shopping agent")
    result = shopping.execute_shopping(sid, product, accept_price_change=bool(state.get("price_confirmed")))
    code = result["code"]

    if result["ok"]:
        message = f"{product['name']} has been added to your cart. I stopped before payment — you can check out yourself."
        sessions.update_session(
            sid, status="completed", current_step="done", cart_state=result["cart_state"],
            browser_state=result["browser_state"], error=None,
        )
        sessions.append_message(sid, "assistant", message)
        _emit(state, "done", "Product successfully added to cart")
    elif code == "cancelled":
        _emit(state, "browser", "Cancelled", "error")
        sessions.update_session(sid, status="cancelled", current_step="cancelled")
        sessions.append_message(sid, "assistant", "Cancelled. Nothing was added to your cart.")
    else:
        _emit(state, "browser", result["message"], "error")
        sessions.update_session(sid, browser_state=result["browser_state"])
    return {"shopping_result": result, "browser_state": result["browser_state"], "cart_state": result["cart_state"],
            "current_step": "shopping"}


def route_after_shopping(state: ShoppingState) -> str:
    code = state["shopping_result"]["code"]
    if code in ("added", "cancelled"):
        return "end"
    if code == "price_changed":
        return "price_change"
    if code in ("unavailable", "not_found"):
        return "fallback"
    return "failed"


def failed_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    result = state["shopping_result"]
    message = _explain(result["message"], _product(state, state["selected_product_id"]))
    sessions.update_session(sid, status="failed", current_step="failed", error=result["message"])
    sessions.append_message(sid, "assistant", message)
    return {"error": result["message"]}


def fallback_node(state: ShoppingState) -> dict:
    """Selected product can't be bought: exclude it and pick the next best option."""
    sid = state["session_id"]
    product = _product(state, state["selected_product_id"])
    message = {
        "unavailable": "The selected product is currently unavailable. I found another matching option.",
        "not_found": "I couldn't find the exact product on the website, so I picked the next best match.",
    }[state["shopping_result"]["code"]]
    sessions.append_message(sid, "assistant", message)
    _emit(state, "select", f"{product['name']} can't be bought — choosing the next best option", "error")
    return {"excluded_ids": [*state.get("excluded_ids", []), product["id"]], "price_confirmed": False}


def price_change_request_node(state: ShoppingState) -> dict:
    sid = state["session_id"]
    product = _product(state, state["selected_product_id"])
    new_price = state["shopping_result"]["observed_price"]
    message = (
        f"The price changed from {format_inr(product['price'])} to {format_inr(new_price)}. "
        "Do you still want me to continue?"
    )
    sessions.update_session(
        sid, status="price_changed", current_step="price_change",
        price_change={"old": product["price"], "new": new_price},
    )
    sessions.append_message(sid, "assistant", message)
    _emit(state, "browser", "Price changed — waiting for your confirmation", "waiting")
    return {}


def price_confirm_node(state: ShoppingState) -> dict:
    product = _product(state, state["selected_product_id"])
    answer = interrupt(
        approval.price_confirmation_request(product, product["price"], state["shopping_result"]["observed_price"])
    )
    if approval.parse_price_confirmation(answer):
        _emit(state, "approval", "Price change accepted")
        return {"price_confirmed": True, "user_approval": True}
    return {"user_approval": False}


def route_after_price_confirm(state: ShoppingState) -> str:
    return "shop" if state.get("user_approval") else "cancel"

