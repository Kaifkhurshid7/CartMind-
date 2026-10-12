"""Deterministic suitability scoring plus a Gemini-written comparison summary."""

import json

from app.llm import prompts
from app.llm.gemini import get_llm
from app.utils.helpers import format_inr
from app.utils.logging import get_logger

log = get_logger("comparison")

PRIORITY_TO_CRITERION = {
    "battery": "battery", "performance": "performance", "speed": "performance", "display": "display",
    "screen": "display", "price": "value", "budget": "value", "cheap": "value", "camera": "camera",
    "sound": "rating", "quality": "rating", "reviews": "rating", "rating": "rating",
}

BASE_WEIGHTS = {
    "laptop": {"performance": 0.25, "battery": 0.2, "display": 0.1, "rating": 0.25, "value": 0.2},
    "headphones": {"battery": 0.25, "rating": 0.35, "value": 0.25, "features": 0.15},
    "phone": {"performance": 0.2, "battery": 0.2, "camera": 0.15, "display": 0.1, "rating": 0.2, "value": 0.15},
}
DEFAULT_WEIGHTS = {"rating": 0.5, "value": 0.5}

CPU_TIERS = (("ryzen 9", 1.0), ("ryzen 7", 0.95), ("core i7", 0.95), ("m2", 0.95), ("m3", 1.0), ("ryzen 5", 0.75),
             ("core i5", 0.75), ("ryzen 3", 0.5), ("core i3", 0.5))


def _cpu_score(processor: str) -> float:
    low = processor.lower()
    return next((s for key, s in CPU_TIERS if key in low), 0.5)


def _display_score(display: str) -> float:
    low = display.lower()
    if "oled" in low or "retina" in low:
        return 1.0
    if "144hz" in low or "120hz" in low:
        return 0.9
    return 0.8 if "ips" in low else 0.6


def _rating_score(p: dict) -> float:
    # Bayesian average so 4.7★ from 12 reviews doesn't beat 4.4★ from 8,000.
    n = p.get("review_count", 0)
    if n == 0:
        return 0.4  # unrated: below a typical rated product
    return ((p["rating"] * n + 4.0 * 100) / (n + 100)) / 5.0


def criteria_scores(p: dict, peers: list[dict], budget: float | None) -> dict[str, float]:
    s = p["specs"]
    top_battery = max((x["specs"].get("battery_hours", 0) for x in peers), default=0) or 1
    out: dict[str, float] = {"rating": _rating_score(p)}
    ceiling = budget or max(x["price"] for x in peers)
    out["value"] = max(0.0, min(1.0, 1 - 0.6 * (p["price"] / ceiling))) if ceiling else 0.5

    if "battery_hours" in s:
        out["battery"] = min(1.0, s["battery_hours"] / top_battery)
    elif "battery_mah" in s:
        out["battery"] = min(1.0, s["battery_mah"] / 6000)
    category = p.get("category", "")
    if category == "laptop":
        gpu_bonus = 0.1 if "nvidia" in str(s.get("gpu", "")).lower() else 0.0
        out["performance"] = min(
            1.0, 0.45 * _cpu_score(s.get("processor", "")) + 0.3 * min(s.get("ram_gb", 8) / 16, 1.0)
            + 0.15 * min(s.get("storage_gb", 256) / 512, 1.0) + gpu_bonus,
        )
        out["display"] = _display_score(s.get("display", ""))
    elif category == "phone":
        out["performance"] = min(1.0, 0.6 * min(s.get("ram_gb", 4) / 8, 1.0) + 0.4 * min(s.get("storage_gb", 64) / 256, 1.0))
        out["camera"] = min(1.0, s.get("camera_mp", 12) / 108) * 0.5 + 0.5 * out["rating"]
        out["display"] = _display_score(s.get("display", ""))
    elif category == "headphones":
        out["features"] = min(1.0, len(p.get("features", [])) / 4) * 0.6 + (0.4 if s.get("anc") else 0.0)
    return out


def weights_for(requirements: dict, available: set[str]) -> dict[str, float]:
    weights = dict(BASE_WEIGHTS.get(requirements.get("category", ""), DEFAULT_WEIGHTS))
    for pr in requirements.get("priorities", []):
        crit = PRIORITY_TO_CRITERION.get(pr.lower())
        if crit in weights:
            weights[crit] *= 2.5
    weights = {k: v for k, v in weights.items() if k in available}
    total = sum(weights.values()) or 1
    return {k: v / total for k, v in weights.items()}


def score_products(products: list[dict], requirements: dict) -> list[dict]:
    budget = (requirements.get("budget") or {}).get("maximum")
    scored = []
    for p in products:
        crit = criteria_scores(p, products, budget)
        scored.append((p, crit))
    available = set.intersection(*(set(c) for _, c in scored)) if scored else set()
    weights = weights_for(requirements, available)
    out = []
    for p, crit in scored:
        total = sum(weights[k] * crit[k] for k in weights)
        penalty = min(30, 8 * len(p.get("warnings", [])))
        out.append({**p, "suitability": round(max(0.0, total * 100 - penalty), 1),
                    "score_breakdown": {k: round(crit[k] * 100) for k in weights}})
    out.sort(key=lambda x: -x["suitability"])
    return out


def _key_specs(p: dict) -> dict:
    keep = ("ram_gb", "storage_gb", "battery_hours", "battery_mah", "processor", "display", "anc", "camera_mp", "type")
    return {k: v for k, v in p["specs"].items() if k in keep}


def build_comparison(scored: list[dict], requirements: dict) -> dict:
    rows = [
        {"id": p["id"], "name": p["name"], "price": p["price"], "specs": _key_specs(p), "rating": p["rating"],
         "review_count": p["review_count"], "suitability": p["suitability"]}
        for p in scored
    ]
    return {"table": rows, "summary": _summary(scored, requirements)}


def _summary(scored: list[dict], requirements: dict) -> str:
    compact = [
        {"name": p["name"], "price": p["price"], "specs": _key_specs(p), "rating": p["rating"],
         "reviews": p["review_count"], "suitability": p["suitability"]}
        for p in scored[:5]
    ]
    try:
        return get_llm().invoke(
            prompts.COMPARE.format(requirements=json.dumps(requirements, ensure_ascii=False),
                                   products=json.dumps(compact, ensure_ascii=False)),
            system=prompts.SYSTEM,
        ).strip()
    except Exception as exc:  # noqa: BLE001
        log.info("LLM comparison unavailable (%s); using templated summary", exc)
    top = scored[0]
    cheapest = min(scored, key=lambda p: p["price"])
    parts = [f"{top['name']} scores highest ({top['suitability']:.0f}%) at {format_inr(top['price'])}."]
    if cheapest["id"] != top["id"]:
        parts.append(f"{cheapest['name']} is the cheapest at {format_inr(cheapest['price'])}.")
    best_rated = max(scored, key=lambda p: p["rating"])
    if best_rated["id"] != top["id"]:
        parts.append(f"{best_rated['name']} has the best rating ({best_rated['rating']}★).")
    return " ".join(parts)


def analyze_reviews(products: list[dict], reviews: dict[str, dict]) -> dict[str, str]:
    payload = {p["id"]: {"name": p["name"], "rating": p["rating"], "snippets": reviews.get(p["id"], {}).get("reviews", [])}
               for p in products}
    if not any(v["snippets"] for v in payload.values()):  # nothing to summarise: save the model call
        return {
            pid: f"Rated {v['rating']} stars on the listing (no review text available)." for pid, v in payload.items()
        }
    try:
        data = get_llm().invoke_json(
            prompts.REVIEW_SUMMARY.format(reviews=json.dumps(payload, ensure_ascii=False)), system=prompts.SYSTEM
        )
        if isinstance(data, dict) and data:
            return {k: str(v) for k, v in data.items() if k in payload}
    except Exception as exc:  # noqa: BLE001
        log.info("LLM review summary unavailable (%s); using snippets", exc)
    return {
        pid: " ".join(v["snippets"][:2]) or f"Rated {v['rating']}★ on the listing (no review text available)."
        for pid, v in payload.items()
    }

