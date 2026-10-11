from typing import TypedDict


class ShoppingState(TypedDict, total=False):
    session_id: str
    user_query: str
    requirements: dict
    refinement: str | None  # set when the user changed requirements mid-session (replanning)

    search_results: list
    shortlisted_products: list
    rejected_products: list
    near_misses: list

    comparison: dict
    review_analysis: dict
    recommendation: dict
    selected_product_id: str | None
    excluded_ids: list  # products that failed during shopping (unavailable / not found)

    user_approval: bool
    approved_product_id: str | None
    accept_price_change: bool
    price_confirmed: bool

    browser_state: dict
    cart_state: dict
    shopping_result: dict

    current_step: str
    error: str | None
