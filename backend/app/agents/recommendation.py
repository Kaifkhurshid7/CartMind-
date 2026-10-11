"""Builds the recommendation: deterministic facts + Gemini-written explanation."""

import json

from app.agents.requirements import check_spec, spec_key
from app.llm import prompts
from app.llm.gemini import get_llm
from app.utils.helpers import format_inr
from app.utils.logging import get_logger

log = get_logger("recommendation")

SPEC_LABELS = {"ram_gb": "{:g}GB RAM", "storage_gb": "{:g}GB storage", "battery_hours": "{:g}h battery",
               "battery_mah": "{:g}mAh battery", "camera_mp": "{:g}MP camera"}


def _met_requirements(product: dict, requirements: dict) -> list[str]:
    met = []
    for name, value in (requirements.get("requirements") or {}).items():
        key = spec_key(name)
        ok, _ = check_spec(product, name, value)
        if ok and key in product["specs"]:
            actual = product["specs"][key]
            if isinstance(actual, bool):
                met.append(name.upper() if len(name) <= 4 else name.title())
            elif key in SPEC_LABELS:
                met.append(SPEC_LABELS[key].format(actual))
            else:
                met.append(f"{name}: {actual}")
    maximum = (requirements.get("budget") or {}).get("maximum")
    if maximum:
        met.append(f"{format_inr(maximum - product['price'])} under your {format_inr(maximum)} budget")
    return met


def _drawbacks(product: dict, alternatives: list[dict]) -> list[str]:
    out = []
    for crit, label in (("battery", "battery"), ("display", "display"), ("performance", "performance")):
        mine = product["score_breakdown"].get(crit)
        better = [a for a in alternatives if a["score_breakdown"].get(crit, 0) >= (mine or 0) + 15]
        if mine is not None and better:
            out.append(f"{better[0]['name']} has a noticeably better {label}.")
    if product["rating"] < 4.0:
        out.append(f"Rated {product['rating']}★, which is below average among top picks.")
    return out[:3] or ["No major drawbacks versus the other shortlisted options."]


def build_recommendation(selected: dict, scored: list[dict], requirements: dict) -> dict:
    alternatives = [p for p in scored if p["id"] != selected["id"]][:3]
    reasons = _met_requirements(selected, requirements)
    reasons.append(f"Rated {selected['rating']}★ from {selected['review_count']:,} reviews")
    drawbacks = _drawbacks(selected, alternatives)
    alt_note = ""
    if alternatives:
        a = alternatives[0]
        alt_note = f"{a['name']} ({format_inr(a['price'])}) is the closest alternative, scoring {a['suitability']:.0f}%."
    summary = (
        f"{selected['name']} is the best match for your request at {format_inr(selected['price'])} "
        f"with a suitability score of {selected['suitability']:.0f}%."
    )

    try:
        compact = lambda p: {"name": p["name"], "price": p["price"], "specs": p["specs"], "rating": p["rating"],  # noqa: E731
                             "suitability": p["suitability"], "features": p.get("features", [])}
        data = get_llm().invoke_json(
            prompts.RECOMMEND.format(
                requirements=json.dumps(requirements, ensure_ascii=False),
                product=json.dumps(compact(selected), ensure_ascii=False),
                alternatives=json.dumps([compact(a) for a in alternatives], ensure_ascii=False),
            ),
            system=prompts.SYSTEM,
        )
        if isinstance(data, dict):
            summary = data.get("summary") or summary
            reasons = [str(r) for r in data.get("reasons") or reasons][:6] or reasons
            drawbacks = [str(d) for d in data.get("disadvantages") or drawbacks][:4] or drawbacks
            alt_note = data.get("alternative_note") or alt_note
    except Exception as exc:  # noqa: BLE001
        log.info("LLM recommendation unavailable (%s); using templated explanation", exc)

    return {
        "product": selected,
        "alternatives": alternatives,
        "summary": summary,
        "reasons": reasons,
        "disadvantages": drawbacks,
        "alternative_note": alt_note,
    }
