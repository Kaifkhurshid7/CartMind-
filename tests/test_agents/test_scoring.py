from app.agents.comparison import score_products
from app.agents.recommendation import build_recommendation
from app.agents.requirements import normalize
from app.agents.research import filter_products
from app.store import catalog


def _shortlist(req):
    products = [p for p in catalog.all_products() if p["category"] == req["category"]]
    return filter_products(products, req)[0]


def test_scores_are_sorted_and_bounded():
    req = normalize({"category": "laptop", "budget": {"maximum": 50000}, "requirements": {"ram": "16GB+"}})
    scored = score_products(_shortlist(req), req)
    values = [p["suitability"] for p in scored]
    assert values == sorted(values, reverse=True)
    assert all(0 <= v <= 100 for v in values)


def test_battery_priority_promotes_long_battery_product():
    base = {"category": "laptop", "budget": {"maximum": 60000}, "requirements": {"ram": "16GB+"}}
    products = _shortlist(normalize(base))
    best_battery = max(products, key=lambda p: p["specs"]["battery_hours"])["id"]
    boosted = score_products(products, normalize({**base, "priorities": ["battery"]}))
    assert boosted[0]["id"] == best_battery


def test_recommendation_is_grounded_without_llm():
    req = normalize({"category": "headphones", "budget": {"maximum": 5000}, "requirements": {"anc": "yes", "battery": "30 hours+"}})
    scored = score_products(_shortlist(req), req)
    rec = build_recommendation(scored[0], scored, req)
    assert rec["product"]["price"] <= 5000
    assert rec["reasons"] and rec["disadvantages"]
    assert all(a["id"] != rec["product"]["id"] for a in rec["alternatives"])


def test_products_without_a_category_can_be_scored_and_recommended():
    """Browsing-agent products come from arbitrary sites and product types (a book has no 'laptop' logic)."""
    req = normalize({"category": "paperback of atomic habits", "budget": {"maximum": 500}})
    base = {"brand": "Penguin", "currency": "INR", "specs": {}, "available": True, "live": True, "via_agent": True,
            "features": [], "reviews": [], "source": "amazon.in"}
    products = [
        {**base, "id": "web-1", "name": "Atomic Habits (English)", "price": 399.0, "rating": 4.6, "review_count": 90000,
         "url": "https://www.amazon.in/dp/B0A"},
        {**base, "id": "web-2", "name": "Atomic Habits (Hindi)", "price": 277.0, "rating": 4.5, "review_count": 5100,
         "url": "https://www.amazon.in/dp/B0B"},
    ]
    assert all("category" not in p for p in products)
    scored = score_products(products, req)
    assert [p["suitability"] for p in scored] == sorted((p["suitability"] for p in scored), reverse=True)
    rec = build_recommendation(scored[0], scored, req)
    assert rec["product"]["id"] in {"web-1", "web-2"} and rec["reasons"]


def _product(pid, name, price, rating, reviews, **extra):
    return {"id": pid, "name": name, "brand": "X", "currency": "INR", "price": price, "rating": rating,
            "review_count": reviews, "specs": extra.pop("specs", {}), "features": extra.pop("features", []),
            "available": True, "source": "amazon.in", "url": "https://x", **extra}


def test_category_families_map_free_text_to_scoring_logic():
    from app.agents.comparison import family

    assert family("laptop") == "laptop"
    assert family("samsung galaxy tab s9") == "tablet"
    assert family("55 inch smart tv") == "tv"
    assert family("electric kettle") == "appliance"
    assert family("paperback of atomic habits") == "book"
    assert family("something obscure") == ""


def test_tv_scoring_rewards_better_display_and_reviews():
    req = normalize({"category": "55 inch 4k tv", "budget": {"maximum": 60000}})
    plain = _product("a", "Brand 55 inch Full HD LED TV", 30000, 4.2, 800)
    oled = _product("b", "Brand 55 inch OLED 4K TV", 30000, 4.2, 800)
    scored = score_products([plain, oled], req)
    assert scored[0]["id"] == "b"
    assert "display" in scored[0]["score_breakdown"]


def test_review_volume_breaks_equal_ratings():
    req = normalize({"category": "electric kettle", "budget": {"maximum": 2000}})
    few = _product("few", "Kettle A", 1000, 4.5, 12)
    many = _product("many", "Kettle B", 1000, 4.5, 9000)
    scored = score_products([few, many], req)
    assert scored[0]["id"] == "many"
    assert "confidence" in scored[0]["score_breakdown"]
