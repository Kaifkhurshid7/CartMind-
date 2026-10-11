"""Full agent runs (LangGraph + tools + Playwright) with no LLM configured, so rule-based fallbacks are used."""

import pytest

from app.services import runner, sessions
from app.store import catalog

pytestmark = pytest.mark.usefixtures("live_server")

QUERY = "I need wireless headphones under ₹5,000 with ANC and at least 30 hours battery life"


def _start(query=QUERY) -> str:
    sid = sessions.create_session(query)
    runner.start_run(sid, query)
    return sid


def test_runs_to_approval_and_stops(live_server):
    sid = _start()
    view = sessions.session_view(sid)
    assert view["status"] == "waiting_for_approval"
    product = view["recommendation"]["product"]
    assert product["price"] <= 5000 and product["specs"]["anc"] and product["specs"]["battery_hours"] >= 30
    assert view["cart_state"] == {}  # nothing is bought before approval
    steps = [e["step"] for e in sessions.list_events(sid)]
    assert steps[:2] == ["requirements", "requirements"] and "approval" in steps and "browser" not in steps


def test_approval_adds_to_cart(live_server):
    sid = _start()
    expected = sessions.session_view(sid)["recommendation"]["product"]["id"]
    runner.resume_run(sid, {"approved": True, "product_id": expected})
    view = sessions.session_view(sid)
    assert view["status"] == "completed"
    assert [i["product_id"] for i in view["cart_state"]["items"]] == [expected]


def test_decline_cancels_without_browser(live_server):
    sid = _start()
    runner.resume_run(sid, {"approved": False})
    view = sessions.session_view(sid)
    assert view["status"] == "cancelled" and view["cart_state"] == {}
    assert "browser" not in [e["step"] for e in sessions.list_events(sid)]


def test_only_explicit_true_counts_as_approval(live_server):
    sid = _start()
    runner.resume_run(sid, {"approved": "yes"})
    assert sessions.session_view(sid)["status"] == "cancelled"


def test_user_can_pick_an_alternative(live_server):
    sid = _start()
    view = sessions.session_view(sid)
    alt = view["recommendation"]["alternatives"][0]["id"]
    runner.resume_run(sid, {"approved": True, "product_id": alt})
    view = sessions.session_view(sid)
    assert view["status"] == "completed"
    assert view["cart_state"]["items"][0]["product_id"] == alt


def test_unavailable_product_falls_back_to_next_best(live_server):
    sid = _start()
    first = sessions.session_view(sid)["recommendation"]["product"]["id"]
    catalog.set_override(first, available=False)
    runner.resume_run(sid, {"approved": True, "product_id": first})
    view = sessions.session_view(sid)
    assert view["status"] == "waiting_for_approval"  # asks again before buying the replacement
    second = view["recommendation"]["product"]["id"]
    assert second != first
    assert any("unavailable" in m["content"] for m in view["messages"] if m["role"] == "assistant")
    runner.resume_run(sid, {"approved": True, "product_id": second})
    assert sessions.session_view(sid)["status"] == "completed"


def test_price_change_asks_user_then_continues(live_server):
    sid = _start()
    pid = sessions.session_view(sid)["recommendation"]["product"]["id"]
    old = catalog.get_product(pid)["price"]
    catalog.set_override(pid, price=old + 150)
    runner.resume_run(sid, {"approved": True, "product_id": pid})
    view = sessions.session_view(sid)
    assert view["status"] == "price_changed"
    assert view["cart_state"] == {}
    assert view["price_change"] == {"old": old, "new": old + 150}
    runner.resume_run(sid, {"approved": True, "accept_price_change": True})
    assert sessions.session_view(sid)["status"] == "completed"


def test_price_change_declined_cancels(live_server):
    sid = _start()
    pid = sessions.session_view(sid)["recommendation"]["product"]["id"]
    catalog.set_override(pid, price=catalog.get_product(pid)["price"] + 100)
    runner.resume_run(sid, {"approved": True, "product_id": pid})
    runner.resume_run(sid, {"approved": False})
    assert sessions.session_view(sid)["status"] == "cancelled"


def test_no_matches_returns_near_misses(live_server):
    sid = _start("laptop under 20000 with 16GB RAM")
    view = sessions.session_view(sid)
    assert view["status"] == "no_results"
    assert view["recommendation"] == {}


def test_missing_category_asks_for_clarification(live_server):
    sid = _start("I want something nice")
    view = sessions.session_view(sid)
    assert view["status"] == "needs_clarification" and view["error"]


def test_replanning_updates_requirements_and_results(live_server):
    sid = _start("laptop under 50k for coding with 16GB RAM")
    before = sessions.session_view(sid)
    runner.start_run(sid, before["query"], before["requirements"], "increase budget to 60k and prioritize performance")
    after = sessions.session_view(sid)
    assert after["status"] == "waiting_for_approval"
    assert after["requirements"]["budget"]["maximum"] == 60000
    assert "performance" in after["requirements"]["priorities"]
    assert len(after["shortlisted_products"]) > len(before["shortlisted_products"])
