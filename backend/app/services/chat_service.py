"""Conversational layer: intent routing, grounded Q&A, and refinement (replanning)."""

import json
import re

from app.llm import prompts
from app.llm.gemini import get_llm
from app.rag.retriever import retrieve_context
from app.services import sessions
from app.utils.helpers import format_inr
from app.utils.logging import get_logger

log = get_logger("chat")

INTENTS = {"question", "refine", "approve", "cancel"}


def classify_intent(message: str, requirements: dict) -> str:
    try:
        data = get_llm().invoke_json(
            prompts.CLASSIFY_INTENT.format(requirements=json.dumps(requirements, ensure_ascii=False), message=message),
            system=prompts.SYSTEM,
        )
        intent = str(data.get("intent", "")).lower() if isinstance(data, dict) else ""
        if intent in INTENTS:
            return intent
    except Exception as exc:  # noqa: BLE001
        log.info("LLM intent classification unavailable (%s); using rules", exc)
    return _heuristic_intent(message)


def _heuristic_intent(message: str) -> str:
    low = message.lower().strip()
    if re.match(r"^(cancel|stop|abort|never ?mind|forget it)\b", low):
        return "cancel"
    if re.search(r"\b(add (it|this|that|the .*) to (my |the )?cart|buy (it|this)|go ahead|order it)\b", low):
        return "approve"
    if "?" in low or re.match(r"^(why|what|which|how|is|are|does|do|can|should|would|tell me)\b", low):
        return "question"
    if re.search(
        r"\b(actually|instead|increase|decrease|raise|reduce|lower|change|i want|i need|must|should have|"
        r"prioriti[sz]e|more important|under|below|budget)\b",
        low,
    ):
        return "refine"
    return "question"


def answer_question(session_id: str, question: str) -> str:
    view = sessions.session_view(session_id) or {}
    context = retrieve_context(question)
    history = "\n".join(f"{m['role']}: {m['content']}" for m in view.get("messages", [])[-8:])
    rec = view.get("recommendation") or {}
    slim = lambda p: {k: p[k] for k in ("name", "price", "specs", "rating", "review_count", "suitability") if k in p}  # noqa: E731
    try:
        return get_llm().invoke(
            prompts.ANSWER.format(
                requirements=json.dumps(view.get("requirements", {}), ensure_ascii=False),
                products=json.dumps([slim(p) for p in view.get("shortlisted_products", [])[:6]], ensure_ascii=False),
                recommendation=json.dumps(
                    {"product": slim(rec.get("product", {})), "reasons": rec.get("reasons"),
                     "disadvantages": rec.get("disadvantages")}, ensure_ascii=False) if rec else "none yet",
                comparison=(view.get("comparison") or {}).get("summary", "none yet"),
                context=context or "(none)",
                history=history or "(none)",
                question=question,
            ),
            system=prompts.SYSTEM,
            temperature=0.3,
        ).strip()
    except Exception as exc:  # noqa: BLE001
        log.info("LLM Q&A unavailable (%s); using fallback answer", exc)
        return _fallback_answer(view, question, context)


def _fallback_answer(view: dict, question: str, context: str) -> str:
    rec = view.get("recommendation") or {}
    product = rec.get("product")
    low = question.lower()
    if product and re.search(r"\bwhy\b", low):
        reasons = "; ".join(rec.get("reasons", [])[:4])
        return f"I picked {product['name']} ({format_inr(product['price'])}). {rec.get('summary', '')} Key reasons: {reasons}."
    if product and "battery" in low:
        rows = sorted(view.get("shortlisted_products", []), key=lambda p: -p["specs"].get("battery_hours", 0))
        if rows and "battery_hours" in rows[0]["specs"]:
            return "Battery life: " + ", ".join(f"{p['name']} {p['specs'].get('battery_hours', '?')}h" for p in rows[:4]) + "."
    if context:
        best = context.split("\n\n[")[0].split("] ", 1)[-1]
        return "\n".join(line for line in best.splitlines() if not line.startswith("#")).strip()
    if product:
        return (f"I can't reach the language model right now, but my current pick is {product['name']} at "
                f"{format_inr(product['price'])}. {rec.get('alternative_note', '')}").strip()
    return "I don't have a recommendation yet — once the search finishes I can explain it."
