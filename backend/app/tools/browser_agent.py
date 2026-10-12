"""A real browsing agent: an LLM looks at the live page and decides each action.

Loop:  observe page  ->  LLM picks ONE tool (goto / click / type / scroll / ask_user / ...)  ->  act  ->  repeat

Design rules
- Visible browser with a *persistent profile*, so the logins you do once (Amazon, Flipkart) are reused.
- Logging in, OTPs and robot checks are always handed to the human (`ask_user`); the agent never types
  credentials and never tries to solve a CAPTCHA.
- Hard guardrails live in CODE, not in the prompt: Buy Now / checkout / payment clicks and URLs are refused,
  Add to Cart is refused until the price on the page was confirmed, and only allow-listed domains can be opened.
- The agent's claim of success is never trusted: the cart page is re-opened and checked independently.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable, Literal
from urllib.parse import quote_plus, urljoin, urlparse

from pydantic import BaseModel, Field
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from app.config import get_settings
from app.llm.gemini import LLMUnavailable, get_llm
from app.tools.amazon_tool import parse_title_specs, run_amazon_shopping, signed_in
from app.utils.logging import get_logger

log = get_logger("browser-agent")

SYSTEM_PROMPT = """You are CartMind's browsing agent. You operate a REAL web browser to help a shopper.
Each turn you see the current page (URL, title, numbered interactive elements, visible text) and must call
exactly ONE tool.

Rules:
- Work like a careful person: search the web, open shopping sites, use their search box and filters, read the page.
- Only report what is actually on the page. Never invent prices, ratings or specs.
- Prices are in INR (₹). Use the exact price shown for the specific product.
- Never buy. You may only ADD TO CART. Never click Buy Now / Proceed to Buy / Checkout / Pay, never open
  checkout or payment pages, never enter card, UPI, OTP or any credentials.
- If you need the user to sign in, or see a CAPTCHA / robot check / OTP, call ask_user and wait.
- If a step fails twice, try a different approach (different link, different search wording).
- Be efficient. Call finish as soon as the goal is achieved or impossible."""

# ---- tool schemas (bound to the model; execution happens in `_execute`) ------------------------


class Goto(BaseModel):
    """Open a URL. Only search engines (google.com) and shopping sites (amazon.in, flipkart.com) are allowed."""

    url: str


class Click(BaseModel):
    """Click an interactive element by its [id] from the numbered list on the current page."""

    id: int


class TypeText(BaseModel):
    """Type text into an input element by its [id]. Set submit=true to press Enter afterwards (e.g. to search)."""

    id: int
    text: str
    submit: bool = False


class PressKey(BaseModel):
    """Press a keyboard key such as Enter, Escape or ArrowDown."""

    key: str


class Scroll(BaseModel):
    """Scroll the page to reveal more elements and text."""

    direction: Literal["down", "up"] = "down"


class ReadMore(BaseModel):
    """Read more of the page's visible text, starting at a character offset (page text is shown truncated)."""

    offset: int = Field(ge=0)


class GoBack(BaseModel):
    """Go back to the previous page."""


class AskUser(BaseModel):
    """Pause and ask the human to do something in the browser (sign in, solve a CAPTCHA, OTP). Waits for them."""

    message: str


class ReportProduct(BaseModel):
    """Record one candidate product you have verified on a product or listing page."""

    name: str
    price_inr: float
    url: str = Field(description="URL of the product's own detail page")
    rating: float | None = None
    review_count: int | None = None
    specs: str | None = Field(default=None, description="Specs you saw on the page, e.g. '16GB RAM, 512GB SSD, i5'")


class ReportProducts(BaseModel):
    """Record several verified candidate products at once (preferred: one call instead of many)."""

    products: list[ReportProduct]


class ConfirmPrice(BaseModel):
    """On the product page, report the price currently displayed. Required before clicking Add to Cart."""

    observed_price_inr: float


class Finish(BaseModel):
    """End the task. outcome: done (research complete) | added (item is in the cart) | unavailable | not_found |
    blocked (robot check / cannot proceed) | failed."""

    outcome: Literal["done", "added", "unavailable", "not_found", "blocked", "failed"]
    summary: str


COMMON_TOOLS = [Goto, Click, TypeText, PressKey, Scroll, ReadMore, GoBack, AskUser]
RESEARCH_TOOLS = [*COMMON_TOOLS, ReportProducts, ReportProduct, Finish]
SHOPPING_TOOLS = [*COMMON_TOOLS, ConfirmPrice, Finish]
TOOL_BY_NAME = {t.__name__: t for t in [*COMMON_TOOLS, ReportProducts, ReportProduct, ConfirmPrice, Finish]}

# ---- guardrails ----------------------------------------------------------------------------------

BLOCKED_LABEL = re.compile(
    r"\b(buy\s*now|buy\s*with|place\s*(your\s*)?order|proceed\s*to\s*(buy|checkout|pay\w*)|check\s*-?\s*out|"
    r"pay\s*(now|with|using)|make\s*payment|continue\s*to\s*payment|confirm\s*order|complete\s*(the\s*)?purchase|"
    r"1-?click|one[- ]click|set\s*up\s*(1|one)-?click)\b",
    re.I,
)
BLOCKED_URL = re.compile(
    r"(/checkout|/gp/buy|/buy/|/payment|/pay/|/pay\?|go-to-checkout|/spc/|placeorder|/order-?review|/gp/cart/desktop/go)",
    re.I,
)
ADD_TO_CART = re.compile(r"\badd\s*to\s*(cart|basket|bag)\b", re.I)
SENSITIVE_FIELD = re.compile(r"(pass(word|code)?|card|cvv|cvc|expir|otp|one-time|\bpin\b|upi|ifsc|account\s*number)", re.I)
LOGIN_PATH = re.compile(r"(/ap/(signin|register|cvf)|/sign-?in|/login|/account/login|/accounts?/|/signup)", re.I)
SEARCH_ENGINES = ("google.com", "google.co.in", "bing.com", "duckduckgo.com")
ROBOT_TITLE = re.compile(r"(robot check|captcha|are you a human|unusual traffic|access denied)", re.I)


class Refused(Exception):
    """A guardrail refused the action; the message goes back to the model."""


class Aborted(Exception):
    """The user cancelled, or a required hand-off timed out."""


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def domain_allowed(url: str, allowed: list[str]) -> bool:
    host = host_of(url)
    return bool(host) and any(host == d or host.endswith("." + d) for d in allowed)


def check_url(url: str, allowed: list[str]) -> None:
    if not url.startswith(("http://", "https://")):
        raise Refused("Only http(s) URLs can be opened.")
    if not domain_allowed(url, allowed):
        raise Refused(f"{host_of(url)} is not an allowed site. Allowed: {', '.join(allowed)}.")
    if BLOCKED_URL.search(urlparse(url).path + ("?" + urlparse(url).query if urlparse(url).query else "")):
        raise Refused("Checkout and payment pages are off limits. CartMind only adds items to the cart.")


def check_click(label: str, href: str) -> None:
    if BLOCKED_LABEL.search(label or "") or BLOCKED_LABEL.search(href or ""):
        raise Refused(f"Refused: “{label[:40]}” would start a purchase. Only Add to Cart is allowed.")
    if href and BLOCKED_URL.search(href):
        raise Refused("Refused: that link leads to checkout/payment.")


def check_type(attrs: dict, page_url: str) -> None:
    blob = " ".join(str(attrs.get(k, "")) for k in ("type", "name", "id", "placeholder", "autocomplete", "label"))
    if attrs.get("type") == "password" or SENSITIVE_FIELD.search(blob):
        raise Refused("Refused: never type passwords, card details, OTPs or other credentials. Use ask_user.")
    if LOGIN_PATH.search(urlparse(page_url).path):
        raise Refused("This is a sign-in page: the user must sign in themselves. Use ask_user.")


# ---- browser -------------------------------------------------------------------------------------

OBSERVE_JS = """
(max) => {
  document.querySelectorAll('[data-cm-id]').forEach(e => e.removeAttribute('data-cm-id'));
  const sel = 'a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=link], [role=tab], [role=option]';
  const mains = [...document.querySelectorAll('main, [role=main], #search, #main-content, .s-main-slot')];
  const inMain = el => mains.some(m => m.contains(el));
  const noise = /^(skip to|main content|results$|keyboard shortcuts|show\/hide|shift \+|alt \+)/i;
  const main = [], rest = [];
  for (const el of document.querySelectorAll(sel)) {
    if (main.length + rest.length > 500) break;
    const r = el.getBoundingClientRect(); const st = getComputedStyle(el);
    if (r.width < 3 || r.height < 3 || st.visibility === 'hidden' || st.display === 'none') continue;
    if (r.bottom < 0 || r.top > innerHeight * 3) continue;
    const href = el.tagName === 'A' ? (el.getAttribute('href') || '') : '';
    if (href.startsWith('javascript:') || href === '#' || href.startsWith('#')) continue;
    const label = (el.innerText || el.value || el.getAttribute('aria-label') || el.placeholder || el.alt || el.title || '')
      .trim().replace(/\s+/g, ' ').replace(/^Add to Compare\s*/i, '').slice(0, 90);
    if (!label && el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA') continue;
    if (noise.test(label)) continue;
    (inMain(el) ? main : rest).push({el, label, href: href.slice(0, 100)});
  }
  const out = [];
  for (const {el, label, href} of [...main, ...rest].slice(0, max)) {
    const id = out.length + 1;
    el.setAttribute('data-cm-id', String(id));
    out.push({id, tag: el.tagName.toLowerCase(), type: el.type || '', label, href});
  }
  return out;
}
"""

ATTRS_JS = """
(el) => ({tag: el.tagName.toLowerCase(), type: el.type || '', name: el.name || '', id: el.id || '',
          placeholder: el.placeholder || '', autocomplete: el.autocomplete || '',
          label: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 120),
          href: el.tagName === 'A' ? (el.getAttribute('href') || '') : ''})
"""


class AgentBrowser:
    """Persistent-profile browser. Keep one instance per task; use as a context manager."""

    def __init__(self, headless: bool | None = None) -> None:
        self.settings = get_settings()
        self.headless = self.settings.agent_headless if headless is None else headless
        self.page: Page | None = None
        self._pw = self._ctx = None
        self.text_cache = ""

    def __enter__(self) -> "AgentBrowser":
        self._pw = sync_playwright().start()
        common = dict(
            user_data_dir=self.settings.browser_profile_dir,
            headless=self.headless,
            viewport={"width": 1366, "height": 820},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        try:
            if not self.settings.agent_browser_channel:
                raise PlaywrightError("no channel configured")
            self._ctx = self._pw.chromium.launch_persistent_context(channel=self.settings.agent_browser_channel, **common)
        except PlaywrightError:
            self._ctx = self._pw.chromium.launch_persistent_context(**common)  # bundled Chromium
        self._ctx.set_default_timeout(15_000)
        self._ctx.on("page", self._on_new_page)
        self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        return self

    def __exit__(self, *exc) -> None:
        for step in (lambda: self._ctx.close(), lambda: self._pw.stop()):
            try:
                step()
            except Exception:  # noqa: BLE001
                pass

    def _on_new_page(self, page: Page) -> None:  # product links often open in a new tab
        self.page = page

    # -- observation ---------------------------------------------------------------------------

    def settle(self) -> None:
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=8_000)
        except PlaywrightTimeout:
            pass
        self.page.wait_for_timeout(900)

    def is_blocked(self) -> bool:
        try:
            title = self.page.title() or ""
        except PlaywrightError:
            return False
        url = self.page.url
        return bool(
            ROBOT_TITLE.search(title)
            or "/sorry/" in url
            or "validateCaptcha" in url
            or self.page.locator("form[action*='validateCaptcha']").count() > 0
        )

    def observe(self, max_elements: int = 70, text_chars: int = 4500, offset: int = 0) -> dict:
        elements = self.page.evaluate(OBSERVE_JS, max_elements)
        try:
            text = self.page.evaluate(
                """() => {
                  const m = document.querySelector('main, [role=main], #search, #main-content');
                  const t = m ? m.innerText : '';
                  return t && t.length > 400 ? t : (document.body ? document.body.innerText : '');
                }"""
            )
        except PlaywrightError:
            text = ""
        text = re.sub(r"\n{2,}", "\n", text)
        self.text_cache = text
        return {
            "url": self.page.url,
            "title": (self.page.title() or "")[:120],
            "elements": elements,
            "text": text[offset : offset + text_chars],
            "text_total": len(text),
            "offset": offset,
        }

    def element_attrs(self, element_id: int) -> tuple:
        loc = self.page.locator(f'[data-cm-id="{element_id}"]').first
        if loc.count() == 0:
            raise Refused(f"There is no element [{element_id}] on this page. Use an id from the current list.")
        return loc, loc.evaluate(ATTRS_JS)


def format_observation(obs: dict) -> str:
    lines = [f"URL: {obs['url']}", f"TITLE: {obs['title']}", "", "INTERACTIVE ELEMENTS:"]
    for e in obs["elements"]:
        extra = f" -> {e['href']}" if e["href"] else (f" ({e['type']})" if e["type"] and e["tag"] == "input" else "")
        lines.append(f"[{e['id']}] <{e['tag']}> “{e['label']}”{extra}")
    shown = len(obs["text"])
    more = obs["text_total"] - obs["offset"] - shown
    lines += ["", f"PAGE TEXT (chars {obs['offset']}–{obs['offset'] + shown} of {obs['text_total']}):", obs["text"]]
    if more > 0:
        lines.append(f"[... {more} more characters: call read_more(offset={obs['offset'] + shown})]")
    return "\n".join(lines)


# ---- agent loop ----------------------------------------------------------------------------------


@dataclass
class Outcome:
    outcome: str = "failed"  # done | added | unavailable | not_found | blocked | failed | cancelled | price_changed
    summary: str = ""
    products: list[dict] = field(default_factory=list)
    observed_price: float | None = None
    steps: int = 0
    final_url: str = ""


def _describe(name: str, args: dict, label: str = "") -> str:
    host = host_of(args.get("url", "")) if name == "Goto" else ""
    return {
        "Goto": f"Opening {host or args.get('url', '')}",
        "Click": f"Clicking “{label[:60]}”" if label else f"Clicking element {args.get('id')}",
        "TypeText": f"Typing “{str(args.get('text', ''))[:60]}”" + (" and searching" if args.get("submit") else ""),
        "PressKey": f"Pressing {args.get('key')}",
        "Scroll": f"Scrolling {args.get('direction', 'down')}",
        "ReadMore": "Reading more of the page",
        "GoBack": "Going back",
        "AskUser": "Waiting for you",
        "ReportProducts": f"Recording {len(args.get('products') or [])} products",
        "ReportProduct": f"Found: {str(args.get('name', ''))[:60]} — ₹{int(args.get('price_inr') or 0):,}",
        "ConfirmPrice": f"Checking displayed price ₹{int(args.get('observed_price_inr') or 0):,}",
        "Finish": f"Finished ({args.get('outcome')})",
    }.get(name, name)


class BrowsingAgent:
    def __init__(
        self,
        browser: AgentBrowser,
        goal: str,
        tools: list[type[BaseModel]],
        *,
        max_steps: int,
        emit: Callable[[str, str], None],
        ask_user: Callable[[str], bool],
        expected_price: float | None = None,
        accept_price_change: bool = False,
        max_products: int = 10,
        category: str = "",
    ) -> None:
        self.b = browser
        self.category = category
        self.goal, self.tools, self.max_steps = goal, tools, max_steps
        self.emit, self.ask_user = emit, ask_user
        self.expected_price = expected_price
        self.accept_price_change = accept_price_change
        self.max_products = max_products
        self.allowed = [d.strip() for d in get_settings().agent_allowed_domains.split(",") if d.strip()]
        self.price_confirmed = expected_price is None
        self.result = Outcome()
        self.history: list[str] = []
        self.offset = 0
        self._last_labels: dict[int, str] = {}

    # -- helpers -----------------------------------------------------------------------------

    def _handoff(self, message: str) -> None:
        if not self.ask_user(message):
            raise Aborted("The user cancelled or did not respond in time.")
        self.b.settle()

    def _post_navigation_guard(self) -> None:
        url = self.b.page.url
        if url.startswith("about:"):
            return
        try:
            check_url(url, self.allowed)
        except Refused as err:
            self.b.page.go_back()
            self.b.settle()
            raise Refused(f"The page navigated somewhere off limits and I went back. {err}") from err

    # -- tool execution ----------------------------------------------------------------------

    def _execute(self, name: str, a: dict) -> str:
        page = self.b.page
        if name == "Goto":
            check_url(a["url"], self.allowed)
            try:
                page.goto(a["url"], wait_until="domcontentloaded")
            except (PlaywrightError, PlaywrightTimeout) as exc:
                return f"Could not open the page ({exc.__class__.__name__})."
            self.b.settle()
            self.offset = 0
            return "Opened."
        if name == "Click":
            loc, attrs = self.b.element_attrs(a["id"])
            check_click(attrs["label"], attrs["href"])
            if ADD_TO_CART.search(attrs["label"]) and not self.price_confirmed:
                raise Refused("Call confirm_price with the price shown on this product page before adding to cart.")
            self._last_labels[a["id"]] = attrs["label"]
            loc.scroll_into_view_if_needed()
            loc.click()
            self.b.settle()
            self.offset = 0
            self._post_navigation_guard()
            return "Clicked."
        if name == "TypeText":
            loc, attrs = self.b.element_attrs(a["id"])
            check_type(attrs, page.url)
            loc.fill(a["text"])
            if a.get("submit"):
                loc.press("Enter")
                self.b.settle()
                self.offset = 0
                self._post_navigation_guard()
            return "Typed."
        if name == "PressKey":
            page.keyboard.press(a["key"])
            self.b.settle()
            self._post_navigation_guard()
            return "Pressed."
        if name == "Scroll":
            page.mouse.wheel(0, 700 if a.get("direction", "down") == "down" else -700)
            page.wait_for_timeout(500)
            return "Scrolled."
        if name == "ReadMore":
            self.offset = int(a["offset"])
            return f"Page text now starts at offset {self.offset}."
        if name == "GoBack":
            page.go_back()
            self.b.settle()
            self._post_navigation_guard()
            self.offset = 0
            return "Went back."
        if name == "AskUser":
            self._handoff(a["message"])
            return "The user says they are done. Look at the page again."
        if name == "ReportProduct":
            return self._report(a)
        if name == "ReportProducts":
            notes = [self._report(item) for item in (a.get("products") or [])]
            return f"{len(self.result.products)} recorded. " + " ".join(n for n in notes if not n.startswith("Recorded"))
        if name == "ConfirmPrice":
            return self._confirm_price(float(a["observed_price_inr"]))
        raise Refused(f"Unknown tool {name}")

    def _report(self, a: dict) -> str:
        url = urljoin(self.b.page.url, str(a.get("url", "")))
        try:
            check_url(url, self.allowed)
        except Refused as err:
            return f"Not recorded: {err}"
        price = float(a.get("price_inr") or 0)
        if price <= 0 or not a.get("name"):
            return "Not recorded: a product needs a name and a positive price."
        if any(p["url"] == url or p["name"] == a["name"] for p in self.result.products):
            return "Already recorded."
        text = f"{a['name']} {a.get('specs') or ''}"
        host = host_of(url)
        self.result.products.append({
            "id": "web-" + hashlib.sha1(url.encode()).hexdigest()[:10],
            "name": a["name"] if len(a["name"]) <= 110 else a["name"][:107].rstrip(" ,-") + "…",
            "full_title": a["name"],
            "brand": a["name"].split()[0].strip(",") if a["name"].split() else "",
            "category": self.category,
            "price": price,
            "currency": "INR",
            "specs": parse_title_specs(text),
            "rating": float(a.get("rating") or 0),
            "review_count": int(a.get("review_count") or 0),
            "available": True,
            "url": url,
            "source": host,
            "live": True,
            "via_agent": True,
            "features": [],
            "reviews": [],
        })
        n = len(self.result.products)
        return f"Recorded ({n}/{self.max_products})." + (" That is enough — call finish." if n >= self.max_products else "")

    def _confirm_price(self, observed: float) -> str:
        self.result.observed_price = observed
        expected = self.expected_price or observed
        if abs(observed - expected) > 0.5 and not self.accept_price_change:
            self.result.outcome = "price_changed"
            self.result.summary = f"The price changed from ₹{int(expected):,} to ₹{int(observed):,}."
            raise _Stop()
        self.price_confirmed = True
        return "Price confirmed. You may now click Add to Cart."

    # -- main loop ---------------------------------------------------------------------------

    def run(self) -> Outcome:
        llm = get_llm()
        if not llm.available:
            raise LLMUnavailable("No LLM configured")
        repeats = 0
        last_action = None
        try:
            for step in range(1, self.max_steps + 1):
                self.result.steps = step
                notice = ""
                if self.b.is_blocked():
                    host = host_of(self.b.page.url)
                    if any(host.endswith(d) for d in SEARCH_ENGINES):
                        self.emit("browser", f"{host} blocked automated access — trying another way")
                        notice = (
                            f"\n\nNOTICE: {host} is showing a robot check. Do NOT try to solve it. Open a different "
                            "search engine (https://www.bing.com or https://duckduckgo.com) or go straight to "
                            "https://www.amazon.in or https://www.flipkart.com."
                        )
                    else:
                        self.emit("browser", "A robot check is showing — waiting for you to handle it")
                        self._handoff(
                            "The site is showing a robot check / CAPTCHA. Please solve it in the browser window, "
                            "then click Continue. (CartMind never solves these itself.)"
                        )
                obs = self.b.observe(offset=self.offset)
                prompt = (
                    f"GOAL:\n{self.goal}\n\nSTEP {step} of {self.max_steps}\n\n"
                    f"RECENT ACTIONS:\n{chr(10).join(self.history[-10:]) or '(none yet)'}\n\n"
                    f"CURRENT PAGE:\n{format_observation(obs)}"
                )
                prompt += notice
                if repeats >= 2:
                    prompt += "\n\nWARNING: you repeated the same action several times. Try something different."
                decision = llm.decide(prompt, self.tools, system=SYSTEM_PROMPT)
                if decision is None:
                    self.history.append(f"{step}. (no tool chosen) -> call a tool")
                    continue
                name, args = decision["name"], decision["args"]
                signature = (name, str(sorted(args.items())))
                repeats = repeats + 1 if signature == last_action else 0
                last_action = signature

                if name == "Finish":
                    return self._finish(args)
                label = self._label_for(args.get("id")) if name in ("Click", "TypeText") else ""
                self.emit("browser", _describe(name, args, label))
                try:
                    feedback = self._execute(name, args)
                except Refused as err:
                    feedback = str(err)
                    self.emit("browser", feedback)
                except (PlaywrightError, PlaywrightTimeout) as exc:
                    feedback = f"That action failed ({exc.__class__.__name__}); the page may have changed. Look again."
                self.history.append(f"{step}. {name}({self._short(args)}) -> {feedback[:160]}")
                if name in ("ReportProduct", "ReportProducts") and len(self.result.products) >= self.max_products:
                    self.result.outcome, self.result.summary = "done", "Collected enough candidates."
                    return self.result
            self.result.outcome = self.result.outcome if self.result.products else "failed"
            self.result.summary = self.result.summary or f"Stopped after {self.max_steps} steps."
            if self.result.products and self.result.outcome == "failed":
                self.result.outcome = "done"
            return self.result
        except _Stop:
            return self.result
        except Aborted as err:
            self.result.outcome, self.result.summary = "cancelled", str(err)
            return self.result
        finally:
            try:
                self.result.final_url = self.b.page.url
            except Exception:  # noqa: BLE001
                pass

    def _label_for(self, element_id) -> str:
        try:
            return self.b.page.locator(f'[data-cm-id="{element_id}"]').first.evaluate(ATTRS_JS)["label"]
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _short(args: dict) -> str:
        return ", ".join(f"{k}={str(v)[:40]!r}" for k, v in args.items())

    def _finish(self, args: dict) -> Outcome:
        self.result.outcome = args.get("outcome", "failed")
        self.result.summary = args.get("summary", "")
        return self.result


class _Stop(Exception):
    pass


# ---- task entry points ---------------------------------------------------------------------------


def _requirements_text(req: dict) -> str:
    lines = []
    if req.get("search_text"):
        lines.append(f"The shopper's exact request: \"{req['search_text']}\"")
    lines.append(f"Product category: {req.get('category')}")
    budget = (req.get("budget") or {}).get("maximum")
    if budget:
        lines.append(f"Budget: at most ₹{int(budget):,}")
    for k, v in (req.get("requirements") or {}).items():
        lines.append(f"Mandatory: {k} {v}")
    if req.get("use_case"):
        lines.append(f"Use case: {req['use_case']}")
    if req.get("preferences"):
        lines.append("Nice to have: " + "; ".join(req["preferences"]))
    if req.get("priorities"):
        lines.append("Matters most: " + ", ".join(req["priorities"]))
    return "\n".join(lines)


def research_with_agent(
    requirements: dict, emit: Callable[[str, str], None], ask_user: Callable[[str], bool]
) -> Outcome:
    s = get_settings()
    n = s.agent_max_products
    start_url = None
    if s.agent_start == "shop":
        from app.tools.amazon_tool import BASE, build_query

        maximum = (requirements.get("budget") or {}).get("maximum")
        start_url = f"{BASE}/s?k={quote_plus(build_query(requirements))}"
        if maximum:
            start_url += f"&rh=p_36%3A-{int(maximum * 100)}"  # price filter, in paise

    if start_url:
        how = (
            "You are ALREADY on the Amazon.in search results for this request, so do not use a search engine.\n"
            "1. Read the results on this page. Scroll down at most once or twice if you need to see more.\n"
            f"2. Call report_products ONCE with the {n} best candidates that are within budget and meet the mandatory "
            "specs. For each give the exact name, the displayed price, rating, review count, specs you saw, and the "
            "product page URL (use the link shown for that result). Prefer products with many reviews.\n"
            "3. Then call finish with outcome 'done'.\n"
            "Do not open individual product pages unless the results page does not show a price."
        )
    else:
        how = (
            "1. Open https://www.google.com and search for the product (include key specs). If Google shows a robot "
            "check, use https://www.bing.com or https://duckduckgo.com instead, or go straight to Amazon.in / Flipkart.\n"
            "2. Go to Amazon.in and/or Flipkart. Use the site's own search box and filters.\n"
            f"3. Call report_products with the {n} best candidates within budget that meet the mandatory specs (exact "
            "name, price, rating, review count, specs, product page URL), then call finish with outcome 'done'."
        )
    goal = (
        "Find good candidate products for this shopper by browsing the real web. Work quickly: collect "
        f"{n} solid candidates, not an exhaustive list.\n\n"
        f"{_requirements_text(requirements)}\n\nHow to work:\n{how}\n"
        "Do not add anything to the cart in this phase."
    )
    with AgentBrowser() as browser:
        if start_url:
            emit("browser", "Opening Amazon.in results")
            try:
                browser.page.goto(start_url, wait_until="domcontentloaded")
                browser.settle()
            except (PlaywrightError, PlaywrightTimeout):
                pass  # the agent loop will notice the empty page and navigate itself
        else:
            emit("browser", "Opened the browser, searching the web")
        return BrowsingAgent(
            browser, goal, RESEARCH_TOOLS, max_steps=s.agent_research_steps, emit=emit, ask_user=ask_user,
            max_products=n, category=requirements.get("category", ""),
        ).run()


def _amazon_asin(url: str) -> str | None:
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    return m.group(1) if m else None


CART_URLS = {"amazon.in": "https://www.amazon.in/cart", "amazon.com": "https://www.amazon.com/cart",
             "flipkart.com": "https://www.flipkart.com/viewcart"}
_STOP_TOKENS = {"with", "and", "the", "for", "laptop", "headphones", "phone", "new", "model", "inch", "windows"}


def _in_cart(browser: AgentBrowser, product: dict, cart_url: str) -> tuple[bool, str]:
    page = browser.page
    page.goto(cart_url, wait_until="domcontentloaded")
    browser.settle()
    html = page.content().lower()
    text = (page.evaluate("document.body ? document.body.innerText : ''") or "").lower()
    url_id = re.search(r"(?:/dp/|pid=|/p/)([a-z0-9]{6,})", product["url"].lower())
    if url_id and url_id.group(1) in html:
        return True, text
    tokens = [t for t in re.findall(r"[a-z0-9]{3,}", product.get("full_title", product["name"]).lower()) if t not in _STOP_TOKENS]
    tokens = list(dict.fromkeys(tokens))[:8]
    hits = sum(1 for t in tokens if t in text)
    return bool(tokens) and hits / len(tokens) >= 0.6, text


def shop_with_agent(
    session_id: str,
    product: dict,
    emit: Callable[[str, str], None],
    ask_user: Callable[[str], bool],
    accept_price_change: bool = False,
) -> dict:
    """Open the product, verify the price, sign-in hand-off if needed, add to cart, verify the cart."""
    s = get_settings()
    expected = float(product["price"])
    goal = (
        f"Add this exact product to the shopper's cart (NEVER buy it):\n"
        f"  Name: {product.get('full_title', product['name'])}\n"
        f"  Expected price: ₹{int(expected):,}\n"
        f"  Product page: {product['url']}\n\n"
        "Steps:\n"
        "1. Open the product page URL (goto). If it fails, search the site for the exact name instead.\n"
        "2. Make sure it is the right product. Read the displayed price and call confirm_price with it.\n"
        "3. If the product is unavailable / out of stock, call finish with outcome 'unavailable'.\n"
        "4. If the page header shows a 'Sign in' prompt instead of the user's account, call ask_user once so the "
        "user can sign in, then continue. (Guest carts also work if they just click Continue.)\n"
        "5. Click the Add to Cart button (only this). Ignore warranty/protection upsells and extras.\n"
        "6. When the page confirms the item was added, call finish with outcome 'added'.\n"
        "Never click Buy Now, Proceed to Buy, Checkout or anything about payment."
    )
    result = {"ok": False, "code": "failed", "message": "", "observed_price": None, "browser_state": {}, "cart_state": {}}

    # Fast path: the Amazon.in product flow is deterministic, so it needs no model calls at all.
    asin = _amazon_asin(product.get("url", ""))
    if asin and s.agent_fast_path and host_of(product["url"]).endswith("amazon.in"):
        emit("browser", "Adding to cart with the built-in Amazon.in routine")
        fast = run_amazon_shopping(
            session_id, {**product, "asin": asin}, emit, accept_price_change, persistent=True, ask_user=ask_user
        )
        if fast["code"] == "cancelled":
            return fast
        if fast["ok"] or fast["code"] in ("unavailable", "price_changed"):
            return fast
        emit("browser", "The built-in routine could not finish, handing over to the AI agent")

    try:
        with AgentBrowser() as browser:
            emit("browser", "Opened the browser — going to the product page")
            outcome = BrowsingAgent(
                browser, goal, SHOPPING_TOOLS, max_steps=s.agent_shopping_steps, emit=emit, ask_user=ask_user,
                expected_price=expected, accept_price_change=accept_price_change,
            ).run()
            result["observed_price"] = outcome.observed_price
            result["browser_state"] = {"final_url": outcome.final_url, "steps": outcome.steps,
                                       "observed_price": outcome.observed_price}
            code = outcome.outcome
            if code == "added":
                host = host_of(product["url"])
                cart_url = next((u for d, u in CART_URLS.items() if host.endswith(d)), None)
                if cart_url is None and host_of(s.store_url) == host:
                    cart_url = s.store_url.rstrip("/") + "/cart"
                if cart_url is None:
                    result.update(code="failed", message="Added, but I can't verify the cart on this site.")
                else:
                    emit("browser", "Checking the cart to confirm")
                    ok, _ = _in_cart(browser, product, cart_url)
                    account = signed_in(browser.page) if host.endswith("amazon.in") else None
                    if ok:
                        emit("browser", "Cart verified — stopping before payment")
                        result.update(
                            ok=True, code="added", message=f"{product['name'][:80]} has been added to your cart.",
                            cart_state={"items": [{"product_id": product["id"], "name": product["name"],
                                                   "price": outcome.observed_price or expected}],
                                        "total": outcome.observed_price or expected, "url": cart_url,
                                        "signed_in": account},
                        )
                    else:
                        result.update(code="failed", message="I clicked Add to Cart but couldn't find the item in the cart.")
            elif code in ("unavailable", "not_found", "price_changed", "blocked", "cancelled"):
                result.update(code={"blocked": "blocked"}.get(code, code),
                              message=outcome.summary or "The task could not be completed.")
            else:
                result.update(code="playwright_error",
                              message=outcome.summary or "The browsing agent could not finish the task.")
    except LLMUnavailable as exc:
        result.update(code="failed", message=f"The AI model is unavailable ({exc}).")
    except (PlaywrightError, PlaywrightTimeout) as exc:
        log.exception("Browser agent failure")
        result.update(code="playwright_error", message=f"Browser automation failed ({exc.__class__.__name__}).")
    return result
