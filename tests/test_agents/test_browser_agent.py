"""The browsing-agent loop and its code-level guardrails, driven by a scripted 'model' against the demo store."""

import re
import threading
import time

import pytest

from app.services import handoff, sessions
from app.store import catalog
from app.tools import browser_agent as ba
from app.tools.browser_agent import (
    AgentBrowser,
    BrowsingAgent,
    Refused,
    RESEARCH_TOOLS,
    SHOPPING_TOOLS,
    check_click,
    check_type,
    check_url,
    shop_with_agent,
)

ALLOWED = ["google.com", "amazon.in", "flipkart.com"]


# ---- pure guardrail tests --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label",
    ["Buy Now", "buy now", "Proceed to Buy", "Proceed to checkout", "Place your order", "Pay now", "Checkout",
     "Continue to payment", "Set up 1-Click", "Buy with Prime"],
)
def test_purchase_buttons_are_refused(label):
    with pytest.raises(Refused):
        check_click(label, "")


@pytest.mark.parametrize("label", ["Add to Cart", "Add to cart", "Next page", "Sort by: Price", "See all reviews"])
def test_harmless_clicks_pass(label):
    check_click(label, "/dp/B0XYZ")


@pytest.mark.parametrize(
    "url",
    ["https://www.amazon.in/gp/buy/spc/handlers/display.html", "https://www.amazon.in/checkout/entry/cart",
     "https://www.flipkart.com/checkout?origin=cart", "https://www.amazon.in/gp/cart/desktop/go-to-checkout.html",
     "https://www.flipkart.com/payment/process"],
)
def test_checkout_and_payment_urls_are_refused(url):
    with pytest.raises(Refused):
        check_url(url, ALLOWED)


def test_domain_allow_list():
    check_url("https://www.google.com/search?q=laptop", ALLOWED)
    check_url("https://www.amazon.in/dp/B0TEST", ALLOWED)
    check_url("https://consent.google.com/x", ALLOWED)
    for bad in ("https://evil-amazon.in.attacker.com/", "https://example.com/", "javascript:alert(1)", "file:///etc/passwd"):
        with pytest.raises(Refused):
            check_url(bad, ALLOWED)


def test_credentials_are_never_typed():
    with pytest.raises(Refused):
        check_type({"type": "password"}, "https://www.amazon.in/x")
    with pytest.raises(Refused):
        check_type({"type": "text", "name": "cardNumber"}, "https://www.amazon.in/x")
    with pytest.raises(Refused):
        check_type({"type": "text", "placeholder": "Enter OTP"}, "https://www.flipkart.com/x")
    with pytest.raises(Refused):  # a sign-in page: even an innocent-looking email field is the user's to fill
        check_type({"type": "email", "name": "email"}, "https://www.amazon.in/ap/signin")
    check_type({"type": "search", "name": "q"}, "https://www.google.com/search")


# ---- scripted model ----------------------------------------------------------------------------------


class ScriptedLLM:
    available = True

    def __init__(self, policy):
        self.policy, self.calls, self.prompts = policy, 0, []

    def decide(self, prompt, tools, system=None):
        self.calls += 1
        self.prompts.append(prompt)
        return self.policy(prompt, self.calls)


def element(prompt: str, label_part: str, tag: str | None = None) -> int:
    for m in re.finditer(r"\[(\d+)\] <(\w+)> “(.*?)”", prompt):
        if label_part.lower() in m.group(3).lower() and (tag is None or m.group(2) == tag):
            return int(m.group(1))
    raise AssertionError(f"element {label_part!r} not on page:\n{prompt[-1500:]}")


def page_price(prompt: str) -> float:
    return float(re.search(r"₹([\d,]+)", prompt.split("PAGE TEXT")[-1]).group(1).replace(",", ""))


def call(tool, /, **args):
    return {"name": tool, "args": args}


@pytest.fixture
def agent_env(live_server, monkeypatch):
    """Returns helpers; monkeypatches the model used by the agent loop."""
    events, asks = [], []

    def install(policy):
        llm = ScriptedLLM(policy)
        monkeypatch.setattr(ba, "get_llm", lambda: llm)
        return llm

    return {
        "install": install,
        "events": events,
        "asks": asks,
        "emit": lambda step, msg: events.append(msg),
        "base": f"{live_server}/store",
        "ask_yes": lambda m: asks.append(m) or True,
        "ask_no": lambda m: asks.append(m) or False,
    }


def store_product(pid: str, base: str) -> dict:
    p = catalog.get_product(pid)
    return {**p, "id": f"web-{pid}", "full_title": p["name"], "url": f"{base}/product/{pid}", "source": "127.0.0.1",
            "live": True, "via_agent": True}


# ---- research ----------------------------------------------------------------------------------------


def test_research_agent_searches_site_and_reports_products(agent_env):
    base = agent_env["base"]

    def policy(prompt, n):
        if n == 1:
            return call("Goto", url=base)
        if n == 2:
            return call("TypeText", id=element(prompt, "Search products", None) if "Search products" in prompt else 1,
                        text="headphones", submit=True)
        if n == 3:
            return call("Click", id=element(prompt, "Sony WH-CH720N"))
        if n == 4:
            url = re.search(r"URL: (\S+)", prompt).group(1)
            return call("ReportProduct", name="Sony WH-CH720N Wireless ANC", price_inr=page_price(prompt), url=url,
                        rating=4.4, review_count=8420, specs="ANC, 35 hours battery")
        return call("Finish", outcome="done", summary="found one")

    agent_env["install"](policy)
    with AgentBrowser(headless=True) as browser:
        out = BrowsingAgent(browser, "find headphones", RESEARCH_TOOLS, max_steps=8, emit=agent_env["emit"],
                            ask_user=agent_env["ask_no"]).run()
    assert out.outcome == "done" and len(out.products) == 1
    p = out.products[0]
    assert p["price"] == 4799 and p["specs"].get("anc") is True and p["via_agent"] and p["live"]
    assert any("Typing" in e for e in agent_env["events"]) and any("Found:" in e for e in agent_env["events"])


def test_research_agent_cannot_record_off_domain_products(agent_env):
    def policy(prompt, n):
        if n == 1:
            return call("ReportProduct", name="Scam Phone", price_inr=1, url="https://evil.example.com/p")
        return call("Finish", outcome="failed", summary="x")

    agent_env["install"](policy)
    with AgentBrowser(headless=True) as browser:
        out = BrowsingAgent(browser, "g", RESEARCH_TOOLS, max_steps=3, emit=agent_env["emit"],
                            ask_user=agent_env["ask_no"]).run()
    assert out.products == []


# ---- shopping ----------------------------------------------------------------------------------------


def test_shopping_agent_adds_to_cart_and_cart_is_verified(agent_env):
    product = store_product("hp-001", agent_env["base"])

    def policy(prompt, n):
        if n == 1:
            return call("Goto", url=product["url"])
        if n == 2:
            return call("ConfirmPrice", observed_price_inr=page_price(prompt))
        if n == 3:
            return call("Click", id=element(prompt, "Add to Cart"))
        return call("Finish", outcome="added", summary="in cart")

    agent_env["install"](policy)
    result = shop_with_agent("s1", product, agent_env["emit"], agent_env["ask_no"])
    assert result["ok"] and result["code"] == "added"
    assert result["cart_state"]["items"][0]["product_id"] == product["id"]
    assert any("Cart verified" in e for e in agent_env["events"])


def test_add_to_cart_is_refused_until_price_is_confirmed(agent_env):
    product = store_product("hp-001", agent_env["base"])
    llm = agent_env["install"](lambda prompt, n: (
        call("Goto", url=product["url"]) if n == 1
        else call("Click", id=element(prompt, "Add to Cart")) if n == 2
        else call("Finish", outcome="added", summary="claimed")
    ))
    result = shop_with_agent("s2", product, agent_env["emit"], agent_env["ask_no"])
    assert any("confirm_price" in e for e in agent_env["events"])  # guardrail message surfaced
    assert not result["ok"]  # ...and the false claim of success is caught by the independent cart check
    assert llm.calls == 3


def test_claimed_success_without_cart_item_is_not_believed(agent_env):
    product = store_product("hp-002", agent_env["base"])
    agent_env["install"](lambda prompt, n: call("Goto", url=product["url"]) if n == 1 else call(
        "Finish", outcome="added", summary="trust me"))
    result = shop_with_agent("s3", product, agent_env["emit"], agent_env["ask_no"])
    assert not result["ok"] and "couldn't find the item in the cart" in result["message"]


def test_price_change_stops_before_adding(agent_env):
    product = store_product("hp-001", agent_env["base"])
    catalog.set_override("hp-001", price=5299)

    def policy(prompt, n):
        if n == 1:
            return call("Goto", url=product["url"])
        return call("ConfirmPrice", observed_price_inr=page_price(prompt))

    agent_env["install"](policy)
    result = shop_with_agent("s4", product, agent_env["emit"], agent_env["ask_no"])
    assert result["code"] == "price_changed" and result["observed_price"] == 5299 and not result["ok"]

    agent_env["install"](policy)  # the user accepted the new price: now it may proceed
    accepted_policy = lambda prompt, n: (  # noqa: E731
        call("Goto", url=product["url"]) if n == 1
        else call("ConfirmPrice", observed_price_inr=page_price(prompt)) if n == 2
        else call("Click", id=element(prompt, "Add to Cart")) if n == 3
        else call("Finish", outcome="added", summary="ok")
    )
    agent_env["install"](accepted_policy)
    ok = shop_with_agent("s4b", product, agent_env["emit"], agent_env["ask_no"], accept_price_change=True)
    assert ok["ok"]


def test_unavailable_product_is_reported(agent_env):
    product = store_product("lap-009", agent_env["base"])  # out of stock
    agent_env["install"](lambda prompt, n: call("Goto", url=product["url"]) if n == 1 else call(
        "Finish", outcome="unavailable", summary="out of stock"))
    result = shop_with_agent("s5", product, agent_env["emit"], agent_env["ask_no"])
    assert result["code"] == "unavailable" and not result["ok"]


def test_buy_now_style_navigation_is_refused_in_loop(agent_env):
    base = agent_env["base"]
    llm = agent_env["install"](lambda prompt, n: (
        call("Goto", url=f"{base}/checkout/pay") if n == 1 else call("Finish", outcome="failed", summary="stop")))
    with AgentBrowser(headless=True) as browser:
        out = BrowsingAgent(browser, "g", SHOPPING_TOOLS, max_steps=3, emit=agent_env["emit"],
                            ask_user=agent_env["ask_no"]).run()
    assert any("off limits" in e for e in agent_env["events"])
    assert "checkout" not in out.final_url


def test_user_cancelling_a_handoff_ends_the_run(agent_env):
    product = store_product("hp-001", agent_env["base"])
    agent_env["install"](lambda prompt, n: call("AskUser", message="Please sign in, then continue."))
    result = shop_with_agent("s6", product, agent_env["emit"], agent_env["ask_no"])
    assert result["code"] == "cancelled"
    assert agent_env["asks"] == ["Please sign in, then continue."]


def test_step_budget_is_enforced(agent_env, monkeypatch):
    monkeypatch.setenv("AGENT_SHOPPING_STEPS", "3")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        llm = agent_env["install"](lambda prompt, n: call("Scroll", direction="down"))
        result = shop_with_agent("s7", store_product("hp-001", agent_env["base"]), agent_env["emit"], agent_env["ask_no"])
        assert llm.calls == 3 and not result["ok"]
    finally:
        monkeypatch.delenv("AGENT_SHOPPING_STEPS")
        get_settings.cache_clear()


# ---- hand-off service --------------------------------------------------------------------------------


def _session() -> str:
    return sessions.create_session("hand-off test")


def test_handoff_continue_unblocks_the_agent_thread():
    sid, out = _session(), {}
    t = threading.Thread(target=lambda: out.setdefault("ok", handoff.request_user_action(sid, "log in", 10)))
    t.start()
    deadline = time.time() + 5
    while time.time() < deadline and not (
        handoff.is_waiting(sid) and sessions.session_view(sid)["status"] == "waiting_for_user"
    ):
        time.sleep(0.05)
    assert sessions.session_view(sid)["status"] == "waiting_for_user"
    assert sessions.session_view(sid)["user_prompt"] == "log in"
    assert handoff.resume(sid)
    t.join(5)
    assert out["ok"] is True and sessions.session_view(sid)["status"] == "running"


def test_handoff_abort_and_timeout_return_false():
    sid = _session()
    out = {}
    t = threading.Thread(target=lambda: out.setdefault("ok", handoff.request_user_action(sid, "x", 10)))
    t.start()
    while not handoff.is_waiting(sid):
        time.sleep(0.05)
    assert handoff.abort(sid)
    t.join(5)
    assert out["ok"] is False
    assert handoff.request_user_action(_session(), "x", 0.2) is False  # timed out
    assert handoff.resume("nobody") is False
