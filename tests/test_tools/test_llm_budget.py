"""Behaviour that keeps a task inside a free-tier LLM quota."""

from app.agents.comparison import analyze_reviews
from app.llm import gemini
from app.llm.gemini import LLMClient
from app.llm.key_manager import KeyManager, cooldown_seconds
from app.tools import browser_agent as ba


class Reply:
    def __init__(self, content="ok", tool_calls=None):
        self.content, self.tool_calls = content, tool_calls or []


def _client(monkeypatch, gemini_calls, groq_calls, fail_gemini_with=None, groq_key="g"):
    client = LLMClient()
    client.keys = KeyManager(["k1"])
    client.settings = type("S", (), {"groq_api_key": groq_key, "gemini_model": "m", "groq_model": "m"})()

    class Gem:
        def invoke(self, _m):
            gemini_calls.append(1)
            raise fail_gemini_with

    class Groq:
        def invoke(self, _m):
            groq_calls.append(1)
            return Reply("from-groq")

    client._gemini = lambda key, temperature: Gem()
    client._groq_model = lambda temperature: Groq()
    return client


def test_daily_quota_parks_the_key_so_later_calls_skip_straight_to_groq(monkeypatch):
    gem, groq = [], []
    client = _client(monkeypatch, gem, groq, RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded per day"))
    assert client.invoke("a") == "from-groq"   # first call discovers the quota problem
    assert client.invoke("b") == "from-groq"   # later calls never touch Gemini again
    assert client.invoke("c") == "from-groq"
    assert len(gem) == 1 and len(groq) == 3
    assert client.keys.current() is None and client.keys.usable is False


def test_per_minute_limit_only_parks_briefly():
    assert cooldown_seconds(RuntimeError("429 quota exceeded per minute")) < 120
    assert cooldown_seconds(RuntimeError("429 RESOURCE_EXHAUSTED per day limit")) >= 3600


def test_parked_key_returns_after_cooldown(monkeypatch):
    km = KeyManager(["k1", "k2"])
    km.cool_down("k1", 60)
    assert km.current() == "k2"
    km.cool_down("k2", 0.0)  # expires immediately
    assert km.current() in ("k1", "k2")
    km._cooling["k1"] = 0.0  # force expiry
    assert km.usable


def test_all_keys_parked_and_no_fallback_raises_clearly(monkeypatch):
    gem = []
    client = _client(monkeypatch, gem, [], RuntimeError("429 quota"), groq_key="")
    try:
        client.invoke("x")
    except gemini.LLMUnavailable as exc:
        assert "429" in str(exc)
    else:
        raise AssertionError("expected LLMUnavailable")


def test_review_summary_makes_no_model_call_without_review_text(monkeypatch):
    def boom():
        raise AssertionError("the model must not be called")

    monkeypatch.setattr("app.agents.comparison.get_llm", boom)
    products = [{"id": "a", "name": "A", "rating": 4.2}]
    out = analyze_reviews(products, {"a": {"reviews": []}})
    assert "4.2" in out["a"]


def test_amazon_fast_path_uses_zero_model_calls(monkeypatch):
    seen = {}

    def fake_amazon(session_id, product, emit, accept_price_change=False, persistent=False):
        seen.update(asin=product["asin"], persistent=persistent)
        return {"ok": True, "code": "added", "message": "added", "observed_price": 100.0,
                "browser_state": {}, "cart_state": {"items": [], "total": 100.0, "url": "x"}}

    def no_agent(*a, **k):
        raise AssertionError("the AI agent must not start when the fast path succeeds")

    monkeypatch.setattr(ba, "run_amazon_shopping", fake_amazon)
    monkeypatch.setattr(ba, "AgentBrowser", no_agent)
    product = {"id": "web-1", "name": "Book", "price": 100.0, "url": "https://www.amazon.in/Some-Title/dp/B0ABCDE123/ref=x"}
    result = ba.shop_with_agent("s", product, lambda *_: None, lambda _m: True)
    assert result["ok"] and seen == {"asin": "B0ABCDE123", "persistent": True}


def test_fast_path_is_skipped_for_other_sites_and_when_disabled(monkeypatch):
    def fake_amazon(*a, **k):
        raise AssertionError("fast path should not run")

    monkeypatch.setattr(ba, "run_amazon_shopping", fake_amazon)

    class StopHere(Exception):
        pass

    def agent_started(*a, **k):
        raise StopHere

    monkeypatch.setattr(ba, "AgentBrowser", agent_started)
    for url in ("https://www.flipkart.com/p/itm123", "https://www.amazon.in/gp/help/customer"):
        try:
            ba.shop_with_agent("s", {"id": "w", "name": "x", "price": 1.0, "url": url}, lambda *_: None, lambda _m: True)
        except StopHere:
            pass
        else:
            raise AssertionError("expected the AI agent path")


def test_asin_extraction():
    assert ba._amazon_asin("https://www.amazon.in/x-y/dp/B0DKK15M2P/ref=sr_1_1") == "B0DKK15M2P"
    assert ba._amazon_asin("https://www.amazon.in/gp/product/B07XJ8C8F5") == "B07XJ8C8F5"
    assert ba._amazon_asin("https://www.flipkart.com/p/itm") is None
