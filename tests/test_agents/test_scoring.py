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
