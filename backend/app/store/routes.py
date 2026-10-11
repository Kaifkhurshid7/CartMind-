"""Server-rendered demo shopping site (CartMart) that Playwright drives."""

import html
import re

from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app.store import catalog
from app.utils.helpers import format_inr

router = APIRouter(prefix="/store", tags=["demo-store"])

_STYLE = """
body{font-family:system-ui,sans-serif;margin:0;background:#f6f7f9;color:#1b1f24}
header{background:#131a22;color:#fff;padding:14px 24px;display:flex;gap:24px;align-items:center}
header a{color:#fff;text-decoration:none}
header form{flex:1;display:flex;gap:8px}
header input[type=search]{flex:1;padding:8px 12px;border-radius:6px;border:0}
button,.btn{background:#f0a500;border:0;border-radius:6px;padding:8px 16px;font-weight:600;cursor:pointer;color:#111;text-decoration:none;display:inline-block}
button:disabled{background:#ccc;cursor:not-allowed}
main{max-width:960px;margin:24px auto;padding:0 16px}
.card{background:#fff;border-radius:10px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px #0001}
.price{font-size:22px;font-weight:700}
.muted{color:#667}
.tag{display:inline-block;background:#eef;border-radius:4px;padding:2px 8px;margin:2px;font-size:12px}
.out{color:#b00020;font-weight:600}.in{color:#0a7d33;font-weight:600}
table{width:100%;border-collapse:collapse}td,th{padding:6px;text-align:left;border-bottom:1px solid #eee}
"""


def _page(title: str, body: str, q: str = "") -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{_STYLE}</style></head><body>
<header><a href="/store"><strong>CartMart</strong></a>
<form action="/store/search" method="get">
<input type="search" name="q" value="{html.escape(q)}" placeholder="Search products" data-testid="search-input">
<button type="submit" data-testid="search-button">Search</button></form>
<a href="/store/cart" data-testid="cart-link">Cart</a></header>
<main>{body}</main></body></html>"""
    )


def _cart_ids(cart: str | None) -> list[str]:
    return [c for c in (cart or "").split(",") if c]


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def search_catalog(query: str) -> list[dict]:
    """All query tokens must appear in name/brand/category (plural 's' tolerated)."""
    tokens = [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in _tokens(query)]
    if not tokens:
        return []
    results = []
    for p in catalog.all_products():
        haystack = " ".join([p["name"], p["brand"], p["category"]]).lower()
        if all(t in haystack for t in tokens):
            results.append(p)
    return results


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    cats = "".join(
        f'<a class="btn" style="margin-right:8px" href="/store/search?q={c}">{c.title()}s</a>'
        for c in ("laptop", "headphones", "phone")
    )
    return _page(
        "CartMart",
        f'<div class="card"><h1>Welcome to CartMart</h1><p class="muted">Demo store for CartMind.</p>{cats}</div>',
    )


@router.get("/search", response_class=HTMLResponse)
def search(q: str = Query("")):
    results = search_catalog(q)
    if not results:
        body = f'<div class="card" data-testid="no-results">No results for “{html.escape(q)}”.</div>'
    else:
        rows = []
        for p in results:
            stock = '<span class="in">In stock</span>' if p["available"] else '<span class="out">Out of stock</span>'
            rows.append(
                f'<div class="card result" data-testid="result" data-product-id="{p["id"]}">'
                f'<a href="/store/product/{p["id"]}" data-testid="result-link"><h3>{html.escape(p["name"])}</h3></a>'
                f'<div class="price">{format_inr(p["price"])}</div>'
                f'<div class="muted">{p["rating"]}★ ({p["review_count"]} reviews)</div>{stock}</div>'
            )
        body = f'<p class="muted">{len(results)} result(s) for “{html.escape(q)}”</p>' + "".join(rows)
    return _page(f"Search: {q}", body, q)


@router.get("/product/{product_id}", response_class=HTMLResponse)
def product_page(product_id: str):
    p = catalog.get_product(product_id)
    if not p:
        return HTMLResponse(_page("Not found", '<div class="card">Product not found.</div>').body, status_code=404)
    specs = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>" for k, v in p["specs"].items())
    tags = "".join(f'<span class="tag">{html.escape(f)}</span>' for f in p["features"])
    if p["available"]:
        action = (
            f'<form method="post" action="/store/cart/add"><input type="hidden" name="product_id" value="{p["id"]}">'
            '<button type="submit" data-testid="add-to-cart">Add to Cart</button></form>'
        )
        stock = '<span class="in" data-testid="availability">In stock</span>'
    else:
        action = '<button disabled data-testid="add-to-cart">Currently unavailable</button>'
        stock = '<span class="out" data-testid="availability">Out of stock</span>'
    body = (
        f'<div class="card" data-testid="product" data-product-id="{p["id"]}">'
        f'<h1 data-testid="product-name">{html.escape(p["name"])}</h1>'
        f'<div class="muted">{html.escape(p["brand"])} · {p["rating"]}★ ({p["review_count"]} reviews)</div>'
        f'<div class="price" data-testid="price" data-price="{p["price"]}">{format_inr(p["price"])}</div>'
        f"{stock}<div>{tags}</div><table>{specs}</table><p>{action}</p></div>"
    )
    return _page(p["name"], body)


@router.post("/cart/add")
def cart_add(product_id: str = Form(...), cart: str | None = Cookie(default=None)):
    product = catalog.get_product(product_id)
    ids = _cart_ids(cart)
    if product and product["available"] and product_id not in ids:
        ids.append(product_id)
    resp = RedirectResponse("/store/cart", status_code=303)
    resp.set_cookie("cart", ",".join(ids), httponly=True, samesite="lax")
    return resp


@router.post("/cart/remove")
def cart_remove(product_id: str = Form(...), cart: str | None = Cookie(default=None)):
    ids = [i for i in _cart_ids(cart) if i != product_id]
    resp = RedirectResponse("/store/cart", status_code=303)
    resp.set_cookie("cart", ",".join(ids), httponly=True, samesite="lax")
    return resp


@router.get("/cart", response_class=HTMLResponse)
def cart_page(cart: str | None = Cookie(default=None)):
    items = [p for p in (catalog.get_product(i) for i in _cart_ids(cart)) if p]
    if not items:
        return _page("Cart", '<div class="card" data-testid="cart-empty">Your cart is empty.</div>')
    rows = "".join(
        f'<div class="card" data-testid="cart-item" data-product-id="{p["id"]}">'
        f'<strong data-testid="cart-item-name">{html.escape(p["name"])}</strong>'
        f'<div class="price" data-testid="cart-item-price" data-price="{p["price"]}">{format_inr(p["price"])}</div></div>'
        for p in items
    )
    total = sum(p["price"] for p in items)
    return _page(
        "Cart",
        f'<h1>Your cart</h1>{rows}<div class="card"><strong>Total: '
        f'<span data-testid="cart-total" data-total="{total}">{format_inr(total)}</span></strong>'
        '<p class="muted">Checkout is intentionally disabled — CartMind stops before payment.</p>'
        '<button disabled>Proceed to checkout</button></div>',
    )
