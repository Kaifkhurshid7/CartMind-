"""Human-in-the-loop: what the agent asks, and how a resume value is interpreted."""

from typing import Any


def approval_request(product: dict) -> dict:
    return {
        "type": "approval",
        "question": f"Add {product['name']} to your cart?",
        "product_id": product["id"],
        "price": product["price"],
    }


def parse_approval(value: Any, default_product_id: str | None) -> tuple[bool, str | None]:
    """Resume payload -> (approved, product_id). Anything but an explicit approved=True is a refusal."""
    if not isinstance(value, dict) or value.get("approved") is not True:
        return False, default_product_id
    return True, value.get("product_id") or default_product_id


def price_confirmation_request(product: dict, old_price: float, new_price: float) -> dict:
    return {
        "type": "price_change",
        "question": f"The price changed from {old_price:g} to {new_price:g}. Continue?",
        "product_id": product["id"],
        "old_price": old_price,
        "new_price": new_price,
    }


def parse_price_confirmation(value: Any) -> bool:
    return isinstance(value, dict) and value.get("approved") is True and value.get("accept_price_change") is True
