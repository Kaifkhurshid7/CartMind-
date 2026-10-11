from types import SimpleNamespace

from app.store import catalog
from app.tools import playwright_tool
from app.tools.playwright_tool import run_shopping


def _run(product_id: str, **kw):
    product = catalog.get_product(product_id)
    steps: list[str] = []
    result = run_shopping(f"t-{product_id}", product, lambda step, msg: steps.append(msg), **kw)
    return result, steps


def test_adds_product_to_cart(live_server):
    result, steps = _run("hp-001")
    assert result["ok"] and result["code"] == "added"
    assert [i["product_id"] for i in result["cart_state"]["items"]] == ["hp-001"]
    assert result["cart_state"]["total"] == 4799
    assert any("stopping before payment" in s for s in steps)


def test_product_unavailable(live_server):
    result, _ = _run("lap-009")  # out of stock in the catalog
    assert not result["ok"] and result["code"] == "unavailable"
    assert result["cart_state"] == {}


def test_unavailable_after_recommendation(live_server):
    product = catalog.get_product("hp-001")
    catalog.set_override("hp-001", available=False)
    result = run_shopping("t-late", product, lambda *_: None)
    assert result["code"] == "unavailable"


def test_price_changed_requires_confirmation(live_server):
    product = catalog.get_product("hp-001")  # agent recommended at ₹4,799
    catalog.set_override("hp-001", price=5299)
    blocked = run_shopping("t-price", product, lambda *_: None)
    assert blocked["code"] == "price_changed" and blocked["observed_price"] == 5299
    assert blocked["cart_state"] == {}

    accepted = run_shopping("t-price2", product, lambda *_: None, accept_price_change=True)
    assert accepted["ok"] and accepted["cart_state"]["total"] == 5299


def test_product_not_found(live_server):
    product = {**catalog.get_product("hp-001"), "name": "Totally Different Gadget 9000"}
    result = run_shopping("t-nf", product, lambda *_: None)
    assert result["code"] == "not_found"


def test_website_unreachable(live_server, monkeypatch):
    dead = SimpleNamespace(store_url="http://127.0.0.1:1/store", playwright_headless=True)
    monkeypatch.setattr(playwright_tool, "get_settings", lambda: dead)
    result, _ = _run("hp-001")
    assert result["code"] == "site_unreachable"
    assert "could not be reached" in result["message"]


def test_playwright_timeout_is_reported_not_hidden(live_server, monkeypatch):
    monkeypatch.setattr(playwright_tool, "TIMEOUT_MS", 300)
    original = playwright_tool.ShoppingBrowser.open_product

    def broken(self, product_id):
        self.page.click("[data-testid=does-not-exist]")  # never appears -> timeout
        return original(self, product_id)

    monkeypatch.setattr(playwright_tool.ShoppingBrowser, "open_product", broken)
    result, _ = _run("hp-001")
    assert not result["ok"] and result["code"] == "playwright_error"
