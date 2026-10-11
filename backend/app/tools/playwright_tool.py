"""Playwright browser automation exposed as LangChain tools.

Sync Playwright objects are bound to the thread that created them, so one shopping run
(open -> search -> verify -> add to cart) executes entirely inside one thread via `run_shopping`.
Each shopping task gets its own isolated browser context (no shared cookies/cart).
"""

import difflib
import re
from typing import Callable

from langchain_core.tools import tool
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from app.config import get_settings
from app.utils.logging import get_logger

log = get_logger("playwright")
TIMEOUT_MS = 15000


class ShoppingError(Exception):
    def __init__(self, code: str, message: str, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


class ShoppingBrowser:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base = self.settings.store_url.rstrip("/")
        self._pw = self._browser = self._context = self.page = None

    def start(self) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.settings.playwright_headless)
        self._context = self._browser.new_context()
        self.page = self._context.new_page()
        self.page.set_default_timeout(TIMEOUT_MS)

    def close(self) -> None:
        for obj in (self._context, self._browser):
            try:
                if obj:
                    obj.close()
            except Exception:  # noqa: BLE001
                pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:  # noqa: BLE001
            pass
        self._pw = self._browser = self._context = self.page = None

    def open_site(self) -> str:
        try:
            resp = self.page.goto(self.base, wait_until="domcontentloaded")
        except (PlaywrightError, PlaywrightTimeout) as exc:
            raise ShoppingError("site_unreachable", f"The shopping website could not be reached ({exc.__class__.__name__}).")
        if resp is None or resp.status >= 400:
            raise ShoppingError("site_unreachable", "The shopping website returned an error.")
        return self.page.title()

    def search(self, query: str) -> list[dict]:
        self.page.fill("[data-testid=search-input]", query)
        self.page.click("[data-testid=search-button]")
        self.page.wait_for_load_state("domcontentloaded")
        results = []
        for card in self.page.query_selector_all("[data-testid=result]"):
            results.append(
                {
                    "product_id": card.get_attribute("data-product-id"),
                    "name": card.query_selector("h3").inner_text().strip(),
                }
            )
        return results

    @staticmethod
    def match(name: str, results: list[dict]) -> dict | None:
        def norm(s: str) -> str:
            return re.sub(r"\s+", " ", s.lower()).strip()

        target = norm(name)
        best, best_ratio = None, 0.0
        for r in results:
            ratio = 1.0 if norm(r["name"]) == target else difflib.SequenceMatcher(None, norm(r["name"]), target).ratio()
            if ratio > best_ratio:
                best, best_ratio = r, ratio
        return best if best_ratio >= 0.8 else None

    def open_product(self, product_id: str) -> dict:
        self.page.click(f"[data-testid=result][data-product-id='{product_id}'] [data-testid=result-link]")
        self.page.wait_for_selector("[data-testid=product]")
        return {
            "name": self.page.inner_text("[data-testid=product-name]").strip(),
            "price": float(self.page.get_attribute("[data-testid=price]", "data-price")),
            "available": self.page.get_attribute("[data-testid=add-to-cart]", "disabled") is None,
            "url": self.page.url,
        }

    def add_to_cart(self) -> dict:
        self.page.click("[data-testid=add-to-cart]")
        self.page.wait_for_selector("[data-testid=cart-item], [data-testid=cart-empty]")
        items = [
            {
                "product_id": el.get_attribute("data-product-id"),
                "name": el.query_selector("[data-testid=cart-item-name]").inner_text().strip(),
                "price": float(el.query_selector("[data-testid=cart-item-price]").get_attribute("data-price")),
            }
            for el in self.page.query_selector_all("[data-testid=cart-item]")
        ]
        total = self.page.get_attribute("[data-testid=cart-total]", "data-total") if items else "0"
        return {"items": items, "total": float(total), "url": self.page.url}


_registry: dict[str, ShoppingBrowser] = {}


def _browser(session_id: str) -> ShoppingBrowser:
    return _registry[session_id]


@tool
def search_website(session_id: str, query: str) -> list[dict]:
    """Open the shopping website in the session's browser and search for a product name."""
    b = _browser(session_id)
    b.open_site()
    return b.search(query)


@tool
def open_product(session_id: str, product_id: str) -> dict:
    """Open a product from the current search results and return its name, price and availability."""
    return _browser(session_id).open_product(product_id)


@tool
def add_to_cart(session_id: str) -> dict:
    """Click 'Add to Cart' on the open product page and return the resulting cart contents."""
    return _browser(session_id).add_to_cart()


def run_shopping(
    session_id: str,
    product: dict,
    emit: Callable[[str, str], None],
    accept_price_change: bool = False,
) -> dict:
    """Search -> verify -> add to cart for `product`. Never proceeds to payment.

    Returns {ok, code, message, observed_price, browser_state, cart_state}.
    Codes: added | price_changed | unavailable | not_found | site_unreachable | playwright_error
    """
    expected_price = float(product["price"])
    browser = ShoppingBrowser()
    _registry[session_id] = browser
    state: dict = {}
    try:
        emit("browser", "Launching isolated browser")
        browser.start()
        emit("browser", "Opening shopping website")
        results = search_website.invoke({"session_id": session_id, "query": product["name"]})
        emit("browser", f"Searched for “{product['name']}” — {len(results)} result(s)")
        match = browser.match(product["name"], results)
        if not match:
            raise ShoppingError("not_found", "I couldn't find the exact product on the website.")

        info = open_product.invoke({"session_id": session_id, "product_id": match["product_id"]})
        state.update(product_url=info["url"], observed_price=info["price"], observed_name=info["name"])
        emit("browser", f"Opened product page: {info['name']}")

        if not info["available"]:
            raise ShoppingError("unavailable", "The selected product is currently unavailable.", observed_price=info["price"])
        if abs(info["price"] - expected_price) > 0.5 and not accept_price_change:
            raise ShoppingError(
                "price_changed",
                f"The price changed from ₹{int(expected_price):,} to ₹{int(info['price']):,}.",
                observed_price=info["price"],
            )
        emit("browser", f"Product and price verified (₹{int(info['price']):,})")

        emit("browser", "Adding to cart")
        cart = add_to_cart.invoke({"session_id": session_id})
        if not any(i["product_id"] == match["product_id"] for i in cart["items"]):
            raise ShoppingError("playwright_error", "The item did not appear in the cart after clicking Add to Cart.")
        emit("browser", "Cart verified — stopping before payment")
        return {
            "ok": True,
            "code": "added",
            "message": f"{info['name']} has been added to your cart.",
            "observed_price": info["price"],
            "browser_state": state,
            "cart_state": cart,
        }
    except ShoppingError as err:
        return {
            "ok": False,
            "code": err.code,
            "message": err.message,
            "observed_price": err.extra.get("observed_price", state.get("observed_price")),
            "browser_state": state,
            "cart_state": {},
        }
    except (PlaywrightError, PlaywrightTimeout) as exc:
        log.exception("Playwright failure")
        return {
            "ok": False,
            "code": "playwright_error",
            "message": f"Browser automation failed while interacting with the page ({exc.__class__.__name__}).",
            "observed_price": state.get("observed_price"),
            "browser_state": state,
            "cart_state": {},
        }
    finally:
        browser.close()
        _registry.pop(session_id, None)
