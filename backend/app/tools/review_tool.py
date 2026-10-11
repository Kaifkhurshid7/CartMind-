from langchain_core.tools import tool

from app.store import catalog


@tool
def get_reviews(product_id: str) -> dict:
    """Get customer review snippets, rating and review count for a product id."""
    p = catalog.get_product(product_id)
    if not p:
        return {}
    return {"product_id": product_id, "rating": p["rating"], "review_count": p["review_count"], "reviews": p["reviews"]}
