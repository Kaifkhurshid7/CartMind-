"""LangChain tools for product research (backed by the demo store catalog)."""

from langchain_core.tools import tool

from app.store.routes import search_catalog


def public_product(p: dict) -> dict:
    out = {k: v for k, v in p.items() if k != "reviews"}
    out["url"] = f"/store/product/{p['id']}"
    return out


@tool
def search_products(query: str, max_price: float | None = None) -> list[dict]:
    """Search the shopping catalog for products matching a query (e.g. 'laptop'). Optionally cap the price in INR."""
    results = search_catalog(query)
    if max_price:
        results = [p for p in results if p["price"] <= max_price]
    return [public_product(p) for p in results]
