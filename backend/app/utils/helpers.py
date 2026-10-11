import json
import re
import uuid
from typing import Any


def new_session_id() -> str:
    return f"session_{uuid.uuid4().hex[:12]}"


def format_inr(amount: float | int | None) -> str:
    if amount is None:
        return "n/a"
    return f"₹{int(round(amount)):,}"


def extract_json(text: str) -> Any:
    """Parse a JSON object/array out of an LLM reply (handles ```json fences and chatter)."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start, end = text.find(open_ch), text.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("No JSON found in model output")
