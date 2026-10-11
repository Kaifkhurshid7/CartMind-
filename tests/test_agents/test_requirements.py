from app.agents import requirements as R
from app.agents.replanning import _heuristic_merge, near_misses
from app.agents.research import evaluate, filter_products
from app.store import catalog


def test_extracts_prd_laptop_example():
    req = R.normalize(R.heuristic_extract("I need a laptop under 50k for coding with at least 16GB RAM and 512GB storage."))
    assert req["category"] == "laptop"
    assert req["budget"] == {"maximum": 50000.0, "currency": "INR"}
    assert req["use_case"] == "coding"
    assert req["requirements"] == {"ram": "16GB+", "storage": "512GB+"}


def test_extracts_headphone_example():
    req = R.normalize(R.heuristic_extract(
        "I need wireless headphones under ₹5,000 with ANC and at least 30 hours battery life."))
    assert req["category"] == "headphones"
    assert req["budget"]["maximum"] == 5000
    assert req["requirements"]["anc"] == "yes"
    assert req["requirements"]["battery"] == "30 hours+"


def test_storage_in_tb_is_converted():
    req = R.heuristic_extract("laptop with 1TB SSD under 60000")
    assert req["requirements"]["storage"] == "1024GB+"


def test_validation_requires_category():
    ok, message = R.validate(R.normalize(R.heuristic_extract("something nice please")))
    assert not ok and "category" in message.lower()


def test_check_spec_handles_numbers_booleans_and_unknowns():
    product = {"specs": {"ram_gb": 16, "anc": True}}
    assert R.check_spec(product, "ram", "16GB+")[0]
    assert not R.check_spec(product, "ram", "32GB+")[0]
    assert R.check_spec(product, "anc", "yes")[0]
    assert R.check_spec(product, "gpu", "RTX")[0]  # unknown spec can't disqualify


def test_filter_removes_over_budget_and_weak_specs():
    req = R.normalize({"category": "laptop", "budget": {"maximum": 50000}, "requirements": {"ram": "16GB+", "storage": "512GB+"}})
    products = [p for p in catalog.all_products() if p["category"] == "laptop"]
    kept, rejected = filter_products(products, req)
    kept_ids = {p["id"] for p in kept}
    assert "lap-001" in kept_ids  # ₹47,990, 16GB, 512GB
    assert "lap-005" not in kept_ids  # ₹52,990 over budget
    assert "lap-003" not in kept_ids  # only 8GB
    assert "lap-009" not in kept_ids  # unavailable
    assert all(r["reasons"] for r in rejected)
    assert all(p["price"] <= 50000 and p["specs"]["ram_gb"] >= 16 for p in kept)


def test_merge_refinement_updates_budget_and_priorities():
    base = R.normalize(R.heuristic_extract("laptop under 50k for coding"))
    merged = _heuristic_merge(base, "Increase budget to 60k and prioritize performance")
    assert merged["budget"]["maximum"] == 60000
    assert merged["priorities"] == ["performance"]
    assert merged["category"] == "laptop"


def test_merge_adds_anc_requirement():
    base = R.normalize(R.heuristic_extract("Find headphones under ₹5,000"))
    assert _heuristic_merge(base, "Actually, I want ANC")["requirements"]["anc"] == "yes"


def test_near_misses_report_single_failure():
    req = R.normalize({"category": "laptop", "budget": {"maximum": 40000}, "requirements": {"ram": "16GB+"}})
    products = [p for p in catalog.all_products() if p["category"] == "laptop"]
    assert not filter_products(products, req)[0]
    near = near_misses(products, req)
    assert near and all(len(evaluate(n["product"], req)) == 1 for n in near)


def test_llm_failure_falls_back_to_rules(monkeypatch):
    class Broken:
        def invoke_json(self, *a, **k):
            raise RuntimeError("quota exhausted")

    monkeypatch.setattr(R, "get_llm", lambda: Broken())
    req = R.extract_requirements("headphones under 3000 with anc")
    assert req["category"] == "headphones" and req["budget"]["maximum"] == 3000


def test_any_product_works_not_just_known_categories():
    book = R.normalize(R.heuristic_extract(
        'Find the paperback of "Atomic Habits" by James Clear under ₹500, with a good rating. Add it to my cart.'))
    assert book["category"] == "paperback of atomic habits by james clear"
    assert book["budget"]["maximum"] == 500
    assert R.validate(book)[0]
    kettle = R.heuristic_extract("A Prestige 1.5 litre electric kettle under ₹1,500 with 4+ stars")
    assert kettle["category"] == "A Prestige 1.5 litre electric kettle" and kettle["budget"]["maximum"] == 1500


def test_vague_requests_still_ask_for_clarification():
    for vague in ("something nice please", "hi", "I want something"):
        assert not R.validate(R.normalize(R.heuristic_extract(vague)))[0]
