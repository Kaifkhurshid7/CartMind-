import pytest

from app.agents.research import filter_products
from app.tools.amazon_tool import build_query, parse_count, parse_price, parse_rating, parse_title_specs, to_product


@pytest.mark.parametrize("text,expected", [("₹47,990", 47990), ("₹47,990.00", 47990), ("₹ 1,05,999", 105999), (None, None), ("n/a", None)])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_parse_rating_and_count():
    assert parse_rating("4.2 out of 5 stars") == 4.2 and parse_rating(None) == 0.0
    assert parse_count("(1,234)") == 1234 and parse_count("(2.5K)") == 2500 and parse_count(None) == 0


def test_title_specs_laptop_variants():
    s = parse_title_specs('Acer Aspire 3, Intel Core i3-1305U, 16GB DDR4 RAM/512GB SSD, 15.6" FHD IPS Display')
    assert s["ram_gb"] == 16 and s["storage_gb"] == 512 and s["processor"] == "core i3" and s["display"] == "IPS"
    s = parse_title_specs("HP 15 AMD Ryzen 3 7320U (8GB LPDDR5, 512GB SSD) FHD")
    assert s["ram_gb"] == 8 and s["storage_gb"] == 512
    s = parse_title_specs("Dell 15 Laptop, Core 3 100U, 8GB DDR4, 512 SSD, 15.6\" FHD")
    assert s["ram_gb"] == 8 and s["storage_gb"] == 512
    assert parse_title_specs("Laptop with 1TB SSD and 16GB RAM")["storage_gb"] == 1024


def test_title_specs_phone_and_headphones():
    assert parse_title_specs("Redmi Note 13 5G (8GB/256GB) 5100mAh 200MP")["storage_gb"] == 256
    h = parse_title_specs("boAt Rockerz 551 ANC Bluetooth Headphones, 100 Hours Playtime")
    assert h["anc"] is True and h["battery_hours"] == 100


def test_title_specs_state_only_what_is_written():
    assert parse_title_specs("Generic Laptop 15.6 inch Windows 11") .get("ram_gb") is None


def test_build_query_from_requirements():
    req = {"category": "laptop", "requirements": {"ram": "16GB+", "storage": "512GB+"}}
    assert build_query(req) == "laptop 16GB RAM 512GB SSD"
    assert build_query({"category": "headphones", "requirements": {"anc": "yes"}}) == "headphones ANC"


def _live(title, price, rating, count):
    return to_product({"asin": "B0TEST", "title": title, "price": f"₹{price:,}", "rating": f"{rating} out of 5 stars",
                       "count": f"({count})"}, "laptop")


def test_live_filter_keeps_weak_listings_with_warnings_and_rejects_only_hard_failures():
    req = {"category": "laptop", "budget": {"maximum": 50000}, "requirements": {"ram": "16GB+", "storage": "512GB+"}}
    good = _live("Acer 16GB RAM 512GB SSD Laptop", 40000, 4.2, 300)
    unrated = {**_live("Noname 16GB RAM 512GB SSD Laptop", 30000, 0, 0), "id": "amz-2"}
    no_storage_stated = {**_live("Mystery 16GB RAM Laptop", 30000, 4.5, 500), "id": "amz-3"}
    over_budget = {**_live("Fancy 16GB RAM 512GB SSD Laptop", 70000, 4.5, 500), "id": "amz-4"}
    too_little_ram = {**_live("Small 8GB RAM 512GB SSD Laptop", 30000, 4.5, 500), "id": "amz-5"}

    kept, rejected = filter_products([good, unrated, no_storage_stated, over_budget, too_little_ram], req)
    by_id = {p["id"]: p for p in kept}

    assert set(by_id) == {"amz-B0TEST", "amz-2", "amz-3"}
    assert by_id["amz-B0TEST"]["warnings"] == []
    assert any("no customer reviews" in w for w in by_id["amz-2"]["warnings"])
    assert any("storage" in w and "not stated" in w for w in by_id["amz-3"]["warnings"])
    assert {r["id"] for r in rejected} == {"amz-4", "amz-5"}      # over budget / stated spec too low


def test_warnings_rank_a_product_lower_but_do_not_hide_it():
    from app.agents.comparison import score_products

    req = {"category": "laptop", "budget": {"maximum": 50000}, "requirements": {"ram": "16GB+"}, "priorities": []}
    solid = _live("Acer 16GB RAM 512GB SSD Laptop", 42000, 4.3, 800)
    risky = {**_live("Noname 16GB RAM 512GB SSD Laptop", 30000, 0, 0), "id": "amz-2"}
    kept, _ = filter_products([risky, solid], req)
    scored = score_products(kept, req)
    assert [p["id"] for p in scored] == ["amz-B0TEST", "amz-2"]
    assert scored[0]["suitability"] > scored[1]["suitability"]
