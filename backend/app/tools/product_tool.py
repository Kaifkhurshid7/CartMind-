from langchain_core.tools import tool

from app.store import catalog
from app.tools.search_tool import public_product


@tool
def get_product_details(product_id: str) -> dict:
    """Get full details (price, specs, features, availability) for a product id."""
    p = catalog.get_product(product_id)
    return public_product(p) if p else {}
