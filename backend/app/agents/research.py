"""Product research (tool calls) and mandatory-requirement filtering."""

from typing import Callable

from app.agents.requirements import check_spec
from app.config import get_settings
from app.llm.gemini import LLMUnavailable, get_llm
from app.tools import amazon_tool, browser_agent
from app.tools.review_tool import get_reviews
from app.tools.search_tool import search_products


class AgentCancelled(Exception):
    """The user cancelled while the browsing agent was waiting for them."""


class AgentFailed(Exception):
    """The browsing agent could not find anything (robot check, site problem, step budget)."""


def research(
    requirements: dict,
    emit: Callable[[str, str], None] | None = None,
    ask_user: Callable[[str], bool] | None = None,
) -> list[dict]:
    """Find candidate products. Budget/spec filtering happens in `filter_products` so rejections can be explained.

    Live mode browses Amazon.in with Playwright; demo mode searches the built-in catalog.
    Raises `amazon_tool.LiveSiteError` when the live site can't be searched (blocked, unreachable).
    """
    mode = get_settings().shopping_mode
    if mode == "agent":
        if not get_llm().available:
            raise LLMUnavailable("No Gemini/Groq API key is configured")
        outcome = browser_agent.research_with_agent(requirements, emit or (lambda *_: None), ask_user or (lambda _m: False))
        if outcome.outcome == "cancelled":
            raise AgentCancelled(outcome.summary)
        if not outcome.products:
            raise AgentFailed(outcome.summary or "The browsing agent did not find any products.")
        return outcome.products
    if mode == "live":
        return amazon_tool.search_amazon(requirements, emit)
    return search_products.invoke({"query": requirements["category"]})


def evaluate(product: dict, requirements: dict, budget_slack: float = 0.0) -> list[str]:
    """Reasons a product fails the mandatory requirements (empty list = passes)."""
    reasons: list[str] = []
    maximum = (requirements.get("budget") or {}).get("maximum")
    if maximum and product["price"] > maximum * (1 + budget_slack):
        reasons.append(f"price ₹{int(product['price']):,} over budget ₹{int(maximum):,}")
    for name, value in (requirements.get("requirements") or {}).items():
        ok, why = check_spec(product, name, value)
        if not ok:
            reasons.append(why)
    return reasons


# Scraped listings can be anything (ads, no-name brands, brand-new ASINs). Don't recommend what shoppers haven't vetted.
LIVE_MIN_RATING = 3.5
LIVE_MIN_REVIEWS = 10


def trust_issues(product: dict) -> list[str]:
    if not product.get("live"):
        return []
    issues = []
    if product.get("review_count", 0) < LIVE_MIN_REVIEWS:
        issues.append(f"only {product.get('review_count', 0)} reviews (need {LIVE_MIN_REVIEWS}+)")
    elif product.get("rating", 0) < LIVE_MIN_RATING:
        issues.append(f"rated {product.get('rating')}★ (need {LIVE_MIN_RATING}★+)")
    return issues


def filter_products(products: list[dict], requirements: dict) -> tuple[list[dict], list[dict]]:
    kept, rejected = [], []
    for p in products:
        reasons = evaluate(p, requirements) + trust_issues(p)
        if reasons:
            rejected.append({"id": p["id"], "name": p["name"], "reasons": reasons})
        elif not p.get("available", True):
            rejected.append({"id": p["id"], "name": p["name"], "reasons": ["currently unavailable"]})
        else:
            kept.append(p)
    return kept, rejected


def fetch_reviews(products: list[dict]) -> dict[str, dict]:
    out = {}
    for p in products:
        if p.get("live"):  # listing-level data only; CartMind doesn't scrape individual reviews
            out[p["id"]] = {"rating": p["rating"], "review_count": p["review_count"], "reviews": []}
        else:
            out[p["id"]] = get_reviews.invoke({"product_id": p["id"]})
    return out
