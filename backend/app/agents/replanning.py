"""Replanning: merging user refinements into requirements, and finding near-miss products."""

import json

from app.agents.requirements import (
    PRIORITY_WORDS,
    _find_budget,
    heuristic_extract,
    normalize,
    spec_key,
)
from app.agents.research import evaluate
from app.llm import prompts
from app.llm.gemini import get_llm
from app.utils.logging import get_logger

log = get_logger("replanning")


def merge_requirements(current: dict, message: str) -> dict:
    """Apply a conversational change ("increase budget to 60k", "I want ANC") to existing requirements."""
    try:
        data = get_llm().invoke_json(
            prompts.MERGE_REQUIREMENTS.format(current=json.dumps(current, ensure_ascii=False), message=message),
            system=prompts.SYSTEM,
        )
        if isinstance(data, dict):
            merged = normalize(data)
            if merged["category"]:
                return merged
    except Exception as exc:  # noqa: BLE001
        log.info("LLM merge unavailable (%s); using rule-based merge", exc)
    return _heuristic_merge(current, message)


def _heuristic_merge(current: dict, message: str) -> dict:
    merged = normalize(current)
    found = normalize(heuristic_extract(message, allow_generic=False))
    if (budget := _find_budget(message)) is not None:
        merged["budget"]["maximum"] = budget
    if found["category"] and found["category"] != merged["category"]:
        merged["category"] = found["category"]
        merged["requirements"] = {}
    existing = {spec_key(k): k for k in merged["requirements"]}
    for key, value in found["requirements"].items():
        merged["requirements"].pop(existing.get(spec_key(key), key), None)
        merged["requirements"][key] = value
    for pref in found["preferences"]:
        if pref not in merged["preferences"]:
            merged["preferences"].append(pref)
    if found["use_case"]:
        merged["use_case"] = found["use_case"]
    low = message.lower()
    if any(w in low for w in ("more important", "priorit", "focus on", "matters most")):
        prios = list(found["priorities"])
        merged["priorities"] = prios + [p for p in merged["priorities"] if p not in prios]
    return merged


def near_misses(products: list[dict], requirements: dict, limit: int = 3) -> list[dict]:
    """Products that fail exactly one mandatory requirement (or are within 20% of the budget)."""
    out = []
    for p in products:
        if not p.get("available", True):
            continue
        reasons = evaluate(p, requirements, budget_slack=0.2)
        strict = evaluate(p, requirements)
        if len(strict) == 1 and len(reasons) <= 1:
            out.append({"product": p, "fails": strict[0]})
    out.sort(key=lambda x: -x["product"]["rating"])
    return out[:limit]
