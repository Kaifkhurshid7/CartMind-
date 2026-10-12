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
    client.min_interval, client.max_wait = 0.0, 0.0
    client.settings = type("S", (), {"groq_api_key": groq_key, "gemini_model": "m", "groq_model": "m"})()

    class Gem:
        def invoke(self, _m):
            gemini_calls.append(1)
            raise fail_gemini_with

    class Groq:
        def invoke(self, _m):
            groq_calls.append(1)
            return Reply("from-groq")

    client._gemini = lambda key, temperature, model=None: Gem()
    client._groq_model = lambda temperature: Groq()
    return client


def test_daily_quota_parks_the_key_so_later_calls_skip_straight_to_groq(monkeypatch):
    gem, groq = [], []
    client = _client(monkeypatch, gem, groq, RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded per day"))
    assert client.invoke("a") == "from-groq"   # first call discovers the quota problem
    assert client.invoke("b") == "from-groq"   # later calls never touch Gemini again
    assert client.invoke("c") == "from-groq"
    assert len(gem) == 1 and len(groq) == 3
    assert client._soonest_recovery() > 3600     # the daily-limited model stays parked for hours


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

    def fake_amazon(session_id, product, emit, accept_price_change=False, persistent=False, ask_user=None):
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


def test_denied_project_is_parked_and_reported(monkeypatch):
    gem, groq = [], []
    denied = RuntimeError("403 Your project has been denied access. Please contact support.")
    client = _client(monkeypatch, gem, groq, denied, groq_key="")
    for _ in range(3):
        try:
            client.invoke("x")
        except gemini.LLMUnavailable:
            pass
    assert len(gem) == 1                      # parked after the first refusal, not retried every call
    assert "denied access" in (client.last_error or "")


def test_last_error_clears_after_a_success(monkeypatch):
    gem, groq = [], []
    client = _client(monkeypatch, gem, groq, RuntimeError("403 denied access"), groq_key="g")
    assert client.invoke("x") == "from-groq"  # Gemini refused, Groq answered
    assert client.last_error is None


# ---- model fallback chain and waiting --------------------------------------------------------------


class FakeClock:
    """Replaces time.monotonic/sleep inside the client so waits are instant but accounted for."""

    def __init__(self):
        self.now, self.slept = 1000.0, []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(round(seconds, 1))
        self.now += seconds


def _multi_model_client(monkeypatch, behaviour, models=("m-primary", "m-backup"), groq_key=""):
    """behaviour(model_name, call_number) -> raise an error or return text."""
    client = LLMClient()
    client.keys = KeyManager(["k1"])
    client.min_interval, client.max_wait = 0.0, 90.0
    client.settings = type("S", (), {"groq_api_key": groq_key, "gemini_model": models[0],
                                     "gemini_fallback_models": ",".join(models[1:]), "groq_model": "m"})()
    clock = FakeClock()
    monkeypatch.setattr(gemini.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(gemini.time, "sleep", clock.sleep)
    calls = []

    def build(key, temperature, model=None):
        class M:
            def invoke(self, _m):
                calls.append(model)
                out = behaviour(model, len(calls))
                return Reply(out)

        return M()

    client._gemini = build
    return client, calls, clock


def test_busy_primary_model_falls_back_to_the_next_model(monkeypatch):
    def behaviour(model, n):
        if model == "m-primary":
            raise RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand.")
        return "from-backup"

    client, calls, clock = _multi_model_client(monkeypatch, behaviour)
    assert client.invoke("x") == "from-backup"
    assert calls == ["m-primary", "m-backup"] and clock.slept == []
    assert client.invoke("y") == "from-backup"       # primary stays parked briefly: no wasted retry
    assert calls[2:] == ["m-backup"]


def test_per_minute_limit_waits_instead_of_failing(monkeypatch):
    def behaviour(model, n):
        if n == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded for requests per minute")
        return "recovered"

    client, calls, clock = _multi_model_client(monkeypatch, behaviour, models=("m-only",))
    assert client.invoke("x") == "recovered"
    assert len(clock.slept) == 1 and 60 <= clock.slept[0] <= 75   # waited out the ~70s limit
    assert calls == ["m-only", "m-only"]


def test_wait_is_capped_so_a_daily_limit_fails_fast(monkeypatch):
    def behaviour(model, n):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded per day")

    client, calls, clock = _multi_model_client(monkeypatch, behaviour, models=("m-only",))
    try:
        client.invoke("x")
    except gemini.LLMUnavailable:
        pass
    else:
        raise AssertionError("expected LLMUnavailable")
    assert clock.slept == [] and len(calls) == 1      # a 6h limit is not waited out


def test_retired_model_is_skipped_for_the_key(monkeypatch):
    def behaviour(model, n):
        if model == "gone":
            raise RuntimeError("404 NOT_FOUND. This model models/gone is no longer available to new users.")
        return "ok-from-" + model

    client, calls, _ = _multi_model_client(monkeypatch, behaviour, models=("gone", "alive"))
    assert client.invoke("x") == "ok-from-alive"
    assert client.invoke("x") == "ok-from-alive"
    assert calls.count("gone") == 1                    # never retried after the first 404
