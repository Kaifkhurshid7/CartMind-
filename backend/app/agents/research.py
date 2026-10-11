"""Product research (tool calls) and mandatory-requirement filtering."""

from app.agents.requirements import check_spec
from app.tools.review_tool import get_reviews
from app.tools.search_tool import search_products


def research(requirements: dict) -> list[dict]:
    """Search by category. Budget/spec filtering happens in `filter_products` so rejections can be explained."""
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


def filter_products(products: list[dict], requirements: dict) -> tuple[list[dict], list[dict]]:
    kept, rejected = [], []
    for p in products:
        reasons = evaluate(p, requirements)
        if reasons:
            rejected.append({"id": p["id"], "name": p["name"], "reasons": reasons})
        elif not p.get("available", True):
            rejected.append({"id": p["id"], "name": p["name"], "reasons": ["currently unavailable"]})
        else:
            kept.append(p)
    return kept, rejected


def fetch_reviews(products: list[dict]) -> dict[str, dict]:
    return {p["id"]: get_reviews.invoke({"product_id": p["id"]}) for p in products}
