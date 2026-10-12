import pytest

from app.llm.gemini import LLMClient, LLMUnavailable
from app.llm.key_manager import KeyManager, is_quota_error
from app.rag.retriever import retrieve_context
from app.tools.product_tool import get_product_details
from app.tools.review_tool import get_reviews
from app.tools.search_tool import search_products
from app.utils.helpers import extract_json


def test_search_products_by_category_and_price_cap():
    all_laptops = search_products.invoke({"query": "laptop"})
    assert len(all_laptops) >= 8 and all(p["category"] == "laptop" for p in all_laptops)
    capped = search_products.invoke({"query": "laptop", "max_price": 50000})
    assert capped and all(p["price"] <= 50000 for p in capped)
    assert "reviews" not in all_laptops[0]


def test_search_unknown_returns_empty():
    assert search_products.invoke({"query": "submarine"}) == []


def test_product_details_and_reviews():
    assert get_product_details.invoke({"product_id": "lap-001"})["brand"] == "ASUS"
    assert get_product_details.invoke({"product_id": "nope"}) == {}
    reviews = get_reviews.invoke({"product_id": "hp-001"})
    assert reviews["reviews"] and reviews["rating"] > 0


def test_key_manager_rotates_round_robin():
    km = KeyManager(["a", "b", "c"])
    assert [km.current(), km.rotate(), km.rotate(), km.rotate()] == ["a", "b", "c", "a"]


def test_quota_errors_are_detected():
    assert is_quota_error(RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded"))
    assert not is_quota_error(RuntimeError("invalid argument"))


def test_llm_without_keys_raises_unavailable():
    with pytest.raises(LLMUnavailable):
        LLMClient().invoke("hello")


def test_llm_rotates_key_on_quota_then_succeeds():
    client = LLMClient()
    client.keys = KeyManager(["k1", "k2"])
    seen = []

    class Model:
        def __init__(self, key):
            self.key = key

        def invoke(self, _messages):
            seen.append(self.key)
            if self.key == "k1":
                raise RuntimeError("429 quota exceeded")
            return type("R", (), {"content": "hi"})()

    client._gemini = lambda key, temperature, model=None: Model(key)
    assert client.invoke("hello") == "hi"
    assert seen == ["k1", "k2"]


def test_extract_json_handles_fences_and_chatter():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('here: {"a": [1, 2]} done') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_rag_retrieves_relevant_section():
    assert "16GB" in retrieve_context("Is 16GB RAM enough for programming?")
    assert retrieve_context("zzzz qqqq") == ""
