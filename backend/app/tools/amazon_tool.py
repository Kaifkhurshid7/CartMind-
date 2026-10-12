"""Live shopping on Amazon.in through Playwright (search -> verify -> add to cart).

Free: no API keys, it browses the public site like a person would. Rules this module follows:
- one real browser per task, human-paced (a handful of page loads per request);
- never clicks Buy Now / checkout, never touches payment or login;
- if the site shows a CAPTCHA / robot check it does NOT try to bypass it: with a visible browser
  (PLAYWRIGHT_HEADLESS=false) it waits for the *user* to solve it, otherwise it reports the block.
"""

import re
import time
from typing import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from app.config import get_settings
from app.utils.logging import get_logger

log = get_logger("amazon")

SOURCE = "amazon_in"
BASE = "https://www.amazon.in"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)
NAV_TIMEOUT_MS = 30_000

RESULTS_JS = """
() => [...document.querySelectorAll('div[data-component-type="s-search-result"]')].slice(0, 60).map(c => {
  const q = s => c.querySelector(s);
  const txt = el => (el ? (el.textContent || '').trim() : null);
  return {
    asin: c.getAttribute('data-asin'),
    title: ((q('h2') || {}).innerText || '').trim(),
    price: txt(q('.a-price:not(.a-text-price) .a-offscreen')),
    rating: txt(q('span.a-icon-alt')),
    count: txt(q('a[aria-label*="ratings"] span, span.s-underline-text')),
    sponsored: /Sponsored/i.test((c.innerText || '').slice(0, 250)),
  };
})
"""


class LiveSiteError(Exception):
    """A recoverable problem with the live site. `code` matches the shopping result codes."""

    def __init__(self, code: str, message: str, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


# ---- parsing -------------------------------------------------------------------------------------


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", text) or re.fullmatch(r"\s*([\d,]+(?:\.\d+)?)\s*", text)
    return float(m.group(1).replace(",", "")) if m else None


def parse_rating(text: str | None) -> float:
    m = re.search(r"(\d(?:\.\d)?)\s*out of", text or "")
    return float(m.group(1)) if m else 0.0


def parse_count(text: str | None) -> int:
    m = re.search(r"([\d,.]+)\s*([kKmM]?)", text or "")
    if not m:
        return 0
    value = float(m.group(1).replace(",", "") or 0)
    return int(value * {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1))


def _to_gb(number: str, unit: str) -> int:
    return int(float(number) * (1024 if unit.lower() == "tb" else 1))


def parse_title_specs(title: str) -> dict:
    """Best-effort structured specs from a listing title. Only states what the title actually says."""
    t = title.replace(" ", " ")
    low = t.lower()
    specs: dict = {}

    pair = re.search(r"\b(\d{1,2})\s*gb\s*/\s*(\d{2,4})\s*(gb|tb)\b", low)  # "8GB/256GB"
    ram = re.search(r"\b(\d{1,2})\s*gb\s*(?:lp)?(?:ddr\d\w*\s*)?(?:ram|memory)\b", low) or re.search(
        r"\b(\d{1,2})\s*gb\s*(?:lp)?ddr\d", low
    ) or re.search(r"\((\d{1,2})\s*gb[,/ ]", low)
    if ram:
        specs["ram_gb"] = int(ram.group(1))
    elif pair:
        specs["ram_gb"] = int(pair.group(1))

    storage = re.search(r"\b(\d{2,4})\s*(gb|tb)\s*(?:nvme\s*)?(?:ssd|storage|rom|emmc|hdd)\b", low) or re.search(
        r"\b(\d)\s*(tb)\b", low
    )
    if storage:
        specs["storage_gb"] = _to_gb(storage.group(1), storage.group(2))
    elif pair:
        specs["storage_gb"] = _to_gb(pair.group(2), pair.group(3))
    else:
        loose = re.search(r"(?:ram|ddr\d\w*)[^,]{0,12}[,/]\s*(\d{3,4})\s*(?:ssd|gb)", low)  # "8GB DDR4, 512 SSD"
        if loose:
            specs["storage_gb"] = int(loose.group(1))

    if cpu := re.search(r"(core ultra \d|core i[3579]|core [357]\b|ryzen [3579]|ryzen ai|\bm[1-4]\b|celeron|pentium)", low):
        specs["processor"] = cpu.group(1)
    if re.search(r"\banc\b|noise[- ]?cancel", low):
        specs["anc"] = True
    if m := re.search(r"(\d{2,3})\s*(?:hours?|hrs?|h)\b[^,)]{0,20}(?:playtime|battery|playback)", low) or re.search(
        r"(?:playtime|battery)[^\d,]{0,20}(\d{2,3})\s*(?:hours?|hrs?|h)\b", low
    ):
        specs["battery_hours"] = int(m.group(1))
    if m := re.search(r"(\d{4,5})\s*mah", low):
        specs["battery_mah"] = int(m.group(1))
    if m := re.search(r"(\d{2,3})\s*mp\b", low):
        specs["camera_mp"] = int(m.group(1))
    for key, label in (("oled", "OLED"), ("amoled", "AMOLED"), ("ips", "IPS"), ("qhd", "QHD"), ("fhd", "FHD")):
        if re.search(rf"\b{key}\b", low):
            specs["display"] = label
            break
    if m := re.search(r"(\d{1,2}(?:\.\d)?)\s*(?:\"|''|inch|-inch)", low):
        specs["screen_inches"] = float(m.group(1))
    return specs


def to_product(raw: dict, category: str) -> dict | None:
    price = parse_price(raw.get("price"))
    asin, title = raw.get("asin"), raw.get("title")
    if not (asin and title and price):
        return None
    return {
        "id": f"amz-{asin}",
        "asin": asin,
        "name": title if len(title) <= 110 else title[:107].rstrip(" ,-") + "…",
        "full_title": title,
        "brand": title.split()[0].strip(",") if title.split() else "",
        "category": category,
        "price": price,
        "currency": "INR",
        "specs": parse_title_specs(title),
        "rating": parse_rating(raw.get("rating")),
        "review_count": parse_count(raw.get("count")),
        "available": True,
        "url": f"{BASE}/dp/{asin}",
        "source": SOURCE,
        "live": True,
        "features": [],
        "reviews": [],
    }


# ---- browser plumbing ----------------------------------------------------------------------------


def _is_blocked(page: Page) -> bool:
    try:
        title = (page.title() or "").lower()
    except PlaywrightError:
        return False
    return (
        "robot check" in title
        or "/errors/" in page.url
        or "captcha" in page.url.lower()
        or page.locator("form[action*='validateCaptcha']").count() > 0
    )


def _guard(page: Page, emit: Callable[[str, str], None] | None = None) -> None:
    """Raise LiveSiteError if the site is blocking us. A visible browser lets the user solve it."""
    if not _is_blocked(page):
        return
    settings = get_settings()
    if not settings.playwright_headless:
        if emit:
            emit("browser", "Amazon is showing a robot check — please solve it in the browser window")
        deadline = time.time() + settings.captcha_wait_seconds
        while time.time() < deadline:
            page.wait_for_timeout(1000)
            if not _is_blocked(page):
                return
    raise LiveSiteError(
        "blocked",
        "Amazon.in is asking for a robot check (CAPTCHA), and CartMind does not bypass those. "
        "Set PLAYWRIGHT_HEADLESS=false to solve it yourself in the browser window, or try again later.",
    )


class _Session:
    """Fresh anonymous browser, or (persistent=True) the user's visible, logged-in profile."""

    def __init__(self, persistent: bool = False) -> None:
        self.persistent = persistent

    def __enter__(self) -> Page:
        self._pw = sync_playwright().start()
        s = get_settings()
        if self.persistent:
            common = dict(user_data_dir=s.browser_profile_dir, headless=s.agent_headless,
                          viewport={"width": 1366, "height": 820}, locale="en-IN", timezone_id="Asia/Kolkata")
            try:
                ctx = self._pw.chromium.launch_persistent_context(channel=s.agent_browser_channel or None, **common)
            except PlaywrightError:
                ctx = self._pw.chromium.launch_persistent_context(**common)
            self._browser = ctx  # closing the context closes the browser
            self.page = ctx.pages[0] if ctx.pages else ctx.new_page()
            self.page.set_default_timeout(NAV_TIMEOUT_MS)
            return self.page
        self._browser = self._pw.chromium.launch(headless=s.playwright_headless)
        ctx = self._browser.new_context(
            locale="en-IN", timezone_id="Asia/Kolkata", viewport={"width": 1366, "height": 900}, user_agent=USER_AGENT
        )
        self.page = ctx.new_page()
        self.page.set_default_timeout(NAV_TIMEOUT_MS)
        return self.page

    def __exit__(self, *exc) -> None:
        for step in (self._browser.close, self._pw.stop):
            try:
                step()
            except Exception:  # noqa: BLE001
                pass


def _goto(page: Page, url: str, emit=None) -> None:
    try:
        resp = page.goto(url, wait_until="domcontentloaded")
    except (PlaywrightError, PlaywrightTimeout) as exc:
        raise LiveSiteError("site_unreachable", f"Amazon.in could not be reached ({exc.__class__.__name__}).")
    if resp is not None and resp.status >= 500:
        raise LiveSiteError("site_unreachable", f"Amazon.in returned an error ({resp.status}).")
    page.wait_for_timeout(600)
    _guard(page, emit)


# ---- search --------------------------------------------------------------------------------------


def build_query(requirements: dict) -> str:
    from app.agents.requirements import CATEGORY_WORDS, generic_category

    category = requirements.get("category", "")
    if category not in CATEGORY_WORDS and requirements.get("search_text"):
        category = generic_category(requirements["search_text"]) or category
    parts = [category]
    for name, value in (requirements.get("requirements") or {}).items():
        n = name.lower()
        digits = re.search(r"\d+", str(value))
        if n in ("ram", "memory") and digits:
            parts.append(f"{digits.group()}GB RAM")
        elif n in ("storage", "ssd") and digits:
            parts.append(f"{digits.group()}GB SSD" if requirements.get("category") == "laptop" else f"{digits.group()}GB")
        elif n in ("anc", "noise_cancellation"):
            parts.append("ANC")
    return " ".join(p for p in parts if p)


def search_amazon(requirements: dict, emit: Callable[[str, str], None] | None = None, limit: int = 20) -> list[dict]:
    query = build_query(requirements)
    maximum = (requirements.get("budget") or {}).get("maximum")
    url = f"{BASE}/s?k={query.replace(' ', '+')}"
    if maximum:
        url += f"&rh=p_36%3A-{int(maximum * 100)}"  # price filter, in paise
    with _Session() as page:
        if emit:
            emit("research", f"Searching Amazon.in for “{query}”")
        _goto(page, url, emit)
        try:
            page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=15_000)
        except PlaywrightTimeout:
            _guard(page, emit)
            return []
        raw = page.evaluate(RESULTS_JS)
    products, seen = [], set()
    for r in raw:
        if r.get("asin") in seen:  # the same product often appears as both an ad and an organic result
            continue
        p = to_product(r, requirements.get("category", ""))
        if p:
            seen.add(r["asin"])
            products.append(p)
    return products[:limit]


# ---- add to cart ---------------------------------------------------------------------------------


def _read_price(page: Page) -> float | None:
    for sel in ("#corePriceDisplay_desktop_feature_div", "#apex_desktop", ".priceToPay"):
        loc = page.locator(sel)
        if loc.count():
            price = parse_price(loc.first.inner_text())
            if price:
                return price
    return None


def signed_in(page: Page) -> bool | None:
    """True/False from the header greeting; None when the header is not on the page."""
    loc = page.locator("#nav-link-accountList-nav-line-1")
    if loc.count() == 0:
        return None
    return "sign in" not in loc.first.inner_text().strip().lower()


SIGN_IN_PROMPT = (
    "You are not signed in to Amazon in this CartMind browser window, so the item would go into a guest cart "
    "that is NOT your account's cart. Sign in to Amazon in this window yourself (OTP and all), then click "
    "Continue. Click Continue without signing in to use a guest cart."
)


def run_amazon_shopping(
    session_id: str,
    product: dict,
    emit: Callable[[str, str], None],
    accept_price_change: bool = False,
    persistent: bool = False,
    ask_user: Callable[[str], bool] | None = None,
) -> dict:
    """Open the exact ASIN, verify price/stock, add to the (guest) cart and confirm it is there."""
    expected = float(product["price"])
    asin = product.get("asin") or product["id"].removeprefix("amz-")
    state: dict = {"site": SOURCE}

    def result(ok: bool, code: str, message: str, **kw) -> dict:
        return {"ok": ok, "code": code, "message": message, "observed_price": state.get("observed_price"),
                "browser_state": state, "cart_state": kw.get("cart", {})}

    try:
        emit("browser", "Launching isolated browser")
        with _Session(persistent) as page:
            emit("browser", "Opening the product page on Amazon.in")
            _goto(page, f"{BASE}/dp/{asin}", emit)
            try:
                page.wait_for_selector("#productTitle", timeout=15_000)
            except PlaywrightTimeout:
                _guard(page, emit)
                raise LiveSiteError("not_found", "I couldn't open that product page on Amazon.in.")
            page.wait_for_timeout(1200)
            title = page.locator("#productTitle").first.inner_text().strip()
            price = _read_price(page)
            state.update(product_url=page.url.split("?")[0], observed_name=title, observed_price=price)
            emit("browser", f"Opened: {title[:70]}")

            if persistent and ask_user and signed_in(page) is False:
                emit("browser", "Not signed in to Amazon in this window")
                if not ask_user(SIGN_IN_PROMPT):
                    raise LiveSiteError("cancelled", "Cancelled while waiting for you to sign in.")
                _goto(page, f"{BASE}/dp/{asin}", emit)  # signing in navigates away; come back to the product
                try:
                    page.wait_for_selector("#productTitle", timeout=15_000)
                except PlaywrightTimeout:
                    raise LiveSiteError("not_found", "I couldn't re-open the product page after sign-in.")
                page.wait_for_timeout(1200)
                price = _read_price(page)
                state["observed_price"] = price

            add = page.locator("#add-to-cart-button:visible")
            if add.count() == 0:
                raise LiveSiteError("unavailable", "The selected product is currently unavailable.")
            if price is None:
                raise LiveSiteError("playwright_error", "I couldn't read the price on the product page.")
            if abs(price - expected) > 0.5 and not accept_price_change:
                raise LiveSiteError(
                    "price_changed", f"The price changed from ₹{int(expected):,} to ₹{int(price):,}.", observed_price=price
                )
            emit("browser", f"Product and price verified (₹{int(price):,})")

            emit("browser", "Adding to cart")
            add.first.click()
            try:
                page.wait_for_url(re.compile(r"/cart"), timeout=8_000)
            except PlaywrightTimeout:
                pass  # some layouts confirm in a side sheet instead of navigating
            _goto(page, f"{BASE}/cart", emit)
            page.wait_for_timeout(1500)

            rows = page.locator("[data-asin].sc-list-item")
            items = []
            for i in range(rows.count()):
                row = rows.nth(i)
                item_asin = row.get_attribute("data-asin")
                if not item_asin:
                    continue
                price_loc = row.locator(".sc-product-price")
                name_loc = row.locator(".sc-product-title, .a-truncate-full")
                items.append({
                    "product_id": f"amz-{item_asin}",
                    "name": name_loc.first.inner_text().strip().splitlines()[0] if name_loc.count() else title,
                    "price": parse_price(price_loc.first.inner_text()) if price_loc.count() else price,
                })
            if not any(i["product_id"] == f"amz-{asin}" for i in items):
                raise LiveSiteError("playwright_error", "The item did not appear in the cart after clicking Add to Cart.")
            sub = page.locator("#sc-subtotal-amount-buybox, #sc-subtotal-amount-activecart")
            total = parse_price(sub.first.inner_text()) if sub.count() else sum(i["price"] or 0 for i in items)
            account = signed_in(page)
            emit("browser", "Cart verified — stopping before payment" if account is not False
                 else "Cart verified (guest cart: not signed in) — stopping before payment")
            return result(True, "added", f"{title[:80]} has been added to your cart.",
                          cart={"items": items, "total": total, "url": f"{BASE}/cart", "signed_in": account})
    except LiveSiteError as err:
        if err.extra.get("observed_price"):
            state["observed_price"] = err.extra["observed_price"]
        return result(False, err.code, err.message)
    except (PlaywrightError, PlaywrightTimeout) as exc:
        log.exception("Amazon automation failure")
        return result(False, "playwright_error",
                      f"Browser automation failed while interacting with the page ({exc.__class__.__name__}).")
