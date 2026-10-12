"""Requirement extraction (Gemini, with a rule-based fallback), validation and spec parsing."""

import re
from typing import Any

from app.llm import prompts
from app.llm.gemini import LLMUnavailable, get_llm
from app.utils.logging import get_logger

log = get_logger("requirements")

CATEGORY_WORDS = {
    "laptop": ("laptop", "notebook", "macbook"),
    "headphones": ("headphone", "earphone", "earbud", "headset", "neckband"),
    "phone": ("smartphone", "phone", "mobile"),
}

SPEC_ALIASES = {
    "ram": "ram_gb", "memory": "ram_gb", "ram_gb": "ram_gb",
    "storage": "storage_gb", "ssd": "storage_gb", "disk": "storage_gb", "rom": "storage_gb", "storage_gb": "storage_gb",
    "battery": "battery_hours", "battery_life": "battery_hours", "battery_hours": "battery_hours",
    "anc": "anc", "noise_cancellation": "anc", "noise_cancelling": "anc",
    "camera": "camera_mp", "camera_mp": "camera_mp",
    "battery_mah": "battery_mah",
}

PRIORITY_WORDS = {
    "battery": ("battery",),
    "performance": ("performance", "speed", "fast", "processor"),
    "display": ("display", "screen"),
    "price": ("price", "cheap", "budget"),
    "camera": ("camera",),
    "sound": ("sound", "audio", "bass"),
}

# Specs that titles reliably state; a live listing missing one of these fails a mandatory requirement.
LIVE_STRICT_KEYS = {"ram_gb", "storage_gb", "anc", "camera_mp", "battery_mah"}

USE_CASES = ("coding", "programming", "software development", "gaming", "college", "office", "video editing",
             "travel", "gym", "music", "students", "student", "photography")


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def _money(num: str, suffix: str | None) -> float:
    value = _num(num)
    suffix = (suffix or "").lower()
    if suffix == "k":
        value *= 1_000
    elif suffix in ("l", "lakh", "lac"):
        value *= 100_000
    return value


_BUDGET_RES = [
    r"budget[^\d₹]{0,20}(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(k|lakh|lac|l)?\b",
    r"(?:under|below|less than|within|upto|up to|max(?:imum)?|around|about)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(k|lakh|lac|l)?\b",
    r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(k|lakh|lac|l)?\b",
]


def _find_budget(text: str) -> float | None:
    low = text.lower()
    for pattern in _BUDGET_RES:
        m = re.search(pattern, low)
        if m:
            value = _money(m.group(1), m.group(2))
            if value >= 100:
                return value
    return None


_LEADING = re.compile(
    r"^(?:please\s+)?(?:can you\s+)?(?:find|search for|look for|looking for|get|buy|order|show|i\s+(?:need|want|am looking for)|"
    r"add)(?:\s+me)?\s+(?:(?:a|an|the|some|my)\b\s*)?",
    re.I,
)
_CUT = re.compile(
    r"\s+(?:under|below|within|upto|up to|less than|for|with|having|that|which|and|in|at least|around)\b|"
    r"\s+(?:to|into)\s+(?:my|the|your)\s+(?:cart|basket|bag)\b|[,;:]|\s+-\s+",
    re.I,
)


def generic_category(query: str) -> str:
    """Product phrase for anything outside the known categories: 'paperback of "Atomic Habits" by James Clear'."""
    first = re.split(r"(?<=[a-z0-9\"'\)])[.!?]\s", query.strip(), maxsplit=1)[0]
    phrase = _LEADING.sub("", first.strip().rstrip(".!?"))
    phrase = _CUT.split(phrase, maxsplit=1)[0]
    phrase = re.sub(r"[\"“”]", "", phrase).strip(" -")
    if len(phrase) < 3 or re.match(r"^(something|anything|stuff|things?|a product|products?|items?|it|that|this)\b", phrase, re.I):
        return ""
    return phrase[:80]


def heuristic_extract(query: str, allow_generic: bool = True) -> dict:
    low = query.lower()
    category = None
    for cat, words in CATEGORY_WORDS.items():
        if any(w in low for w in words):
            category = cat
            break

    reqs: dict[str, str] = {}
    if m := re.search(r"(\d+)\s*gb\s*(?:of\s*)?(?:ram|memory)", low) or re.search(r"\bram\D{0,12}(\d+)\s*gb", low):
        reqs["ram"] = f"{m.group(1)}GB+"
    if m := re.search(r"(\d+)\s*(gb|tb)\s*(?:of\s*)?(?:ssd|storage|hdd|rom|nvme)", low) or re.search(
        r"(?:ssd|storage)\D{0,12}(\d+)\s*(gb|tb)", low
    ):
        gb = int(m.group(1)) * (1024 if m.group(2) == "tb" else 1)
        reqs["storage"] = f"{gb}GB+"
    if m := re.search(r"(\d+)\s*\+?\s*(?:hours?|hrs?)\b[^.,]{0,25}battery", low) or re.search(
        r"battery[^\d.,]{0,25}(\d+)\s*\+?\s*(?:hours?|hrs?)", low
    ):
        reqs["battery"] = f"{m.group(1)} hours+"
    if re.search(r"\banc\b|noise[- ]cancel", low):
        reqs["anc"] = "yes"

    use_case = next((u for u in USE_CASES if u in low), None)

    preferences = []
    for m in re.finditer(r"prefer(?:ably)?\s+([^,.]+)", low):
        preferences.append(m.group(1).strip())
    for m in re.finditer(r"good\s+(battery(?: life)?|display|camera|sound|performance)", low):
        preferences.append(f"good {m.group(1)}")

    priorities = []
    for name, words in PRIORITY_WORDS.items():
        if any(w in " ".join(preferences) for w in words):
            priorities.append(name)
    for m in re.finditer(r"(\w+)(?: life| quality)? is (?:more|most) important", low):
        for name, words in PRIORITY_WORDS.items():
            if m.group(1) in words and name not in priorities:
                priorities.append(name)
    for m in re.finditer(r"priorit(?:y|ize|ise)\s+(\w+)", low):
        for name, words in PRIORITY_WORDS.items():
            if m.group(1) in words and name not in priorities:
                priorities.append(name)

    return {
        "category": category or (generic_category(query) if allow_generic else ""),
        "budget": {"maximum": _find_budget(query), "currency": "INR"},
        "use_case": use_case,
        "requirements": reqs,
        "preferences": list(dict.fromkeys(preferences)),
        "priorities": priorities,
        "location": "India",
    }


def normalize(req: dict | None) -> dict:
    req = dict(req or {})
    budget = req.get("budget") or {}
    if not isinstance(budget, dict):
        budget = {"maximum": budget}
    maximum = budget.get("maximum")
    try:
        maximum = float(maximum) if maximum not in (None, "") else None
    except (TypeError, ValueError):
        maximum = None
    return {
        "category": str(req.get("category") or "").strip().lower(),
        "budget": {"maximum": maximum, "currency": budget.get("currency") or "INR"},
        "use_case": req.get("use_case") or None,
        "requirements": {str(k): v for k, v in (req.get("requirements") or {}).items() if v not in (None, "", False)},
        "preferences": [str(p) for p in (req.get("preferences") or [])],
        "priorities": [str(p).lower() for p in (req.get("priorities") or [])],
        "location": req.get("location") or "India",
        "search_text": str(req.get("search_text") or "")[:300],
    }


def extract_requirements(query: str) -> dict:
    result = _extract(query)
    result["search_text"] = query.strip()[:300]
    return result


def _extract(query: str) -> dict:
    try:
        data = get_llm().invoke_json(prompts.EXTRACT_REQUIREMENTS.format(query=query), system=prompts.SYSTEM)
        if isinstance(data, dict):
            result = normalize(data)
            # LLM occasionally misses a clearly stated budget; backfill from rules.
            if result["budget"]["maximum"] is None:
                result["budget"]["maximum"] = _find_budget(query)
            return result
    except (LLMUnavailable, ValueError) as exc:
        log.info("LLM extraction unavailable (%s); using rule-based extraction", exc)
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM extraction failed (%s); using rule-based extraction", exc)
    return normalize(heuristic_extract(query))


def validate(req: dict) -> tuple[bool, str]:
    if not req.get("category"):
        return False, (
            "I couldn't tell what you want to buy. Which product category are you after "
            "(for example a laptop, a book, headphones or a kettle)?"
        )
    return True, ""


# ---- spec parsing / matching -------------------------------------------------------------------


def spec_key(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return SPEC_ALIASES.get(key, key)


def parse_requirement(value: Any) -> tuple[str, Any] | None:
    """-> ("min", number) | ("eq", number) | ("bool", True/False) | None if not understood."""
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("min", float(value))
    text = str(value).strip().lower()
    if text in ("yes", "true", "required", "needed", "must"):
        return ("bool", True)
    if text in ("no", "false"):
        return ("bool", False)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(tb|gb|mah|mp|hours?|hrs?|h)?", text)
    if not m:
        return None
    number = float(m.group(1))
    if m.group(2) == "tb":
        number *= 1024
    return ("eq" if text.endswith("only") else "min", number)


def check_spec(product: dict, name: str, value: Any, strict: bool = True) -> tuple[bool, str]:
    """Does `product` satisfy one mandatory requirement? Unknown specs pass (can't be judged)."""
    key = spec_key(name)
    spec = product.get("specs", {})
    parsed = parse_requirement(value)
    if parsed is None:
        return True, ""
    if key not in spec:
        # A scraped listing that never states a mandatory spec is not trusted to have it.
        if strict and product.get("live") and key in LIVE_STRICT_KEYS:
            return False, f"{name} not stated in the listing"
        return True, ""
    kind, wanted = parsed
    actual = spec[key]
    if kind == "bool":
        ok = bool(actual) == wanted
        return ok, "" if ok else f"{name} {'missing' if wanted else 'present'}"
    try:
        actual_num = float(actual)
    except (TypeError, ValueError):
        return True, ""
    ok = actual_num == wanted if kind == "eq" else actual_num >= wanted
    return ok, "" if ok else f"{name} {actual_num:g} < {wanted:g}"
