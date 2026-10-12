"""Gemini access through LangChain.

Resilience, in the order a call tries things:
  1. every (API key, model) "slot": the primary model first, then fallback models, because free-tier
     quotas and demand spikes are per model;
  2. an optional Groq fallback;
  3. a short wait for the soonest parked slot to recover (a per-minute limit clears in about a minute),
     so a browsing task slows down instead of failing.
A key whose project is refused outright (403) is parked for hours; the last error is kept for the UI.
"""

import re
import threading
import time
from functools import lru_cache
from typing import Any, Callable

from app.config import get_settings
from app.llm.key_manager import KeyManager, cooldown_seconds, is_permanent_error, is_quota_error
from app.utils.helpers import extract_json
from app.utils.logging import get_logger

log = get_logger("llm")

TRANSIENT_COOLDOWN = 15.0  # 503 "high demand", timeouts
OTHER_COOLDOWN = 30.0
HOURS = 3600.0


def _short(exc: Exception) -> str:
    """One readable line for the UI, e.g. 'Your project has been denied access.'"""
    text = str(exc)
    m = re.search(r"'message': '([^']+)'", text) or re.search(r'"message": "([^"]+)"', text)
    return (m.group(1) if m else text)[:200]


def is_model_unavailable(exc: Exception) -> bool:
    """This model name is retired / not offered to this key (other models on the key may still work)."""
    text = str(exc).lower()
    return "no longer available" in text or ("404" in text and "not_found" in text) or "is not found" in text


def is_transient_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(m in text for m in ("503", "unavailable", "high demand", "overloaded", "timeout", "timed out", "deadline", "500"))


class LLMUnavailable(RuntimeError):
    """No LLM could answer (no keys configured, or every provider failed)."""


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.keys = KeyManager(self.settings.gemini_keys)
        self._models: dict[str, Any] = {}
        self._cooling: dict[tuple[str, str], float] = {}  # (key, model) -> monotonic time usable again
        self._last_call: dict[tuple[str, str], float] = {}
        self._lock = threading.Lock()
        self.last_error: str | None = None  # most recent failure, cleared by the next success
        self.max_wait = float(getattr(self.settings, "llm_max_wait_seconds", 90))
        self.min_interval = float(getattr(self.settings, "llm_min_interval_seconds", 0.0))

    # ---- configuration ------------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self.keys.available or bool(self.settings.groq_api_key)

    @property
    def models(self) -> list[str]:
        extra = [m.strip() for m in str(getattr(self.settings, "gemini_fallback_models", "")).split(",") if m.strip()]
        return list(dict.fromkeys([self.settings.gemini_model, *extra]))

    def _gemini(self, key: str, temperature: float, model: str | None = None):
        model = model or self.settings.gemini_model
        cache_key = f"{key}:{model}:{temperature}"
        if cache_key not in self._models:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._models[cache_key] = ChatGoogleGenerativeAI(
                model=model, google_api_key=key, temperature=temperature, max_retries=1
            )
        return self._models[cache_key]

    def _groq_model(self, temperature: float):
        from langchain_groq import ChatGroq

        return ChatGroq(model=self.settings.groq_model, api_key=self.settings.groq_api_key, temperature=temperature)

    @staticmethod
    def _messages(prompt: str, system: str | None):
        from langchain_core.messages import HumanMessage, SystemMessage

        msgs = [SystemMessage(content=system)] if system else []
        msgs.append(HumanMessage(content=prompt))
        return msgs

    @staticmethod
    def _text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):  # content blocks
            return "".join(b if isinstance(b, str) else b.get("text", "") for b in content)
        return str(content)

    # ---- slot bookkeeping -----------------------------------------------------------------------

    def _slot_ready(self, key: str, model: str) -> bool:
        if self.keys.is_cooling(key):
            return False
        with self._lock:
            until = self._cooling.get((key, model))
            if until is not None and time.monotonic() >= until:
                del self._cooling[(key, model)]
                return True
            return until is None

    def _park(self, key: str, model: str, seconds: float) -> None:
        with self._lock:
            self._cooling[(key, model)] = time.monotonic() + seconds

    def _soonest_recovery(self) -> float | None:
        """Seconds until some parked (key, model) slot is usable again, or None if nothing will recover soon."""
        now = time.monotonic()
        with self._lock:
            waits = [until - now for (key, _m), until in self._cooling.items() if not self.keys.is_cooling(key)]
        return max(min(waits), 0.0) if waits else None

    def _pace(self, key: str, model: str) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            ready_at = self._last_call.get((key, model), 0.0) + self.min_interval
            self._last_call[(key, model)] = max(time.monotonic(), ready_at)
        delay = ready_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    # ---- the call loop --------------------------------------------------------------------------

    def _try_gemini(self, temperature: float, call: Callable[[Any], Any]) -> tuple[bool, Any, Exception | None]:
        last_exc: Exception | None = None
        for model in self.models:
            for key in self.keys.all_keys():
                if not self._slot_ready(key, model):
                    continue
                self._pace(key, model)
                try:
                    return True, call(self._gemini(key, temperature, model)), None
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if is_quota_error(exc):
                        seconds = cooldown_seconds(exc)
                        log.warning("Gemini %s hit its quota; parking that model for %ds", model, seconds)
                        self._park(key, model, seconds)
                    elif is_model_unavailable(exc):
                        log.warning("Gemini model %s is not available to this key; skipping it", model)
                        self._park(key, model, 6 * HOURS)
                    elif is_permanent_error(exc):
                        log.warning("Gemini refused this key/project (%s); parking the key for 6h", _short(exc)[:100])
                        self.keys.cool_down(key, 6 * HOURS)
                    elif is_transient_error(exc):
                        log.warning("Gemini %s is busy (%s); trying the next option", model, _short(exc)[:80])
                        self._park(key, model, TRANSIENT_COOLDOWN)
                    else:
                        log.warning("Gemini call failed: %s", _short(exc))
                        self._park(key, model, OTHER_COOLDOWN)
        return False, None, last_exc

    def _run(self, temperature: float, call: Callable[[Any], Any]) -> Any:
        last_exc: Exception | None = None
        waited = 0.0
        while True:
            ok, result, exc = self._try_gemini(temperature, call)
            if ok:
                self.last_error = None
                return result
            last_exc = exc or last_exc

            if self.settings.groq_api_key:
                try:
                    result = call(self._groq_model(temperature))
                    self.last_error = None
                    return result
                except Exception as groq_exc:  # noqa: BLE001
                    last_exc = groq_exc
                    log.warning("Groq fallback failed: %s", _short(groq_exc))
                break  # Groq was the last resort

            # No other provider: a brief wait beats failing the whole task.
            soon = self._soonest_recovery()
            if soon is None or soon > self.max_wait - waited:
                break
            log.info("All Gemini slots are busy; waiting %.0fs for one to recover", soon)
            time.sleep(soon + 0.3)
            waited += soon + 0.3

        if last_exc is not None:
            self.last_error = _short(last_exc)
        elif not self.last_error:  # every key is parked: keep the earlier, more specific reason
            self.last_error = "No LLM provider configured"
        raise LLMUnavailable(str(last_exc) if last_exc else self.last_error)

    # ---- public API -------------------------------------------------------------------------------

    def invoke(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> str:
        messages = self._messages(prompt, system)
        return self._text(self._run(temperature, lambda model: model.invoke(messages).content))

    def decide(self, prompt: str, tools: list, system: str | None = None) -> dict | None:
        """Ask the model to pick ONE tool call. Returns {"name": ..., "args": {...}} or None if it only chatted."""
        messages = self._messages(prompt, system)

        def call(model):
            response = model.bind_tools(tools).invoke(messages)
            calls = getattr(response, "tool_calls", None) or []
            return {"name": calls[0]["name"], "args": calls[0].get("args") or {}} if calls else None

        return self._run(0.0, call)

    def invoke_json(self, prompt: str, system: str | None = None) -> Any:
        raw = self.invoke(prompt, system=system, temperature=0.0)
        try:
            return extract_json(raw)
        except ValueError:
            raw = self.invoke(prompt + "\n\nReturn ONLY valid JSON, no commentary.", system=system, temperature=0.0)
            return extract_json(raw)


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()
