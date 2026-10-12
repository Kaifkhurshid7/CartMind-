"""Gemini access through LangChain, with key rotation, quota cool-downs and an optional Groq fallback."""

from functools import lru_cache
from typing import Any, Callable

from app.config import get_settings
from app.llm.key_manager import KeyManager, cooldown_seconds, is_quota_error
from app.utils.helpers import extract_json
from app.utils.logging import get_logger

log = get_logger("llm")


class LLMUnavailable(RuntimeError):
    """No LLM could answer (no keys configured, or every provider failed)."""


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.keys = KeyManager(self.settings.gemini_keys)
        self._models: dict[str, Any] = {}

    @property
    def available(self) -> bool:
        return self.keys.available or bool(self.settings.groq_api_key)

    def _gemini(self, key: str, temperature: float):
        cache_key = f"{key}:{temperature}"
        if cache_key not in self._models:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._models[cache_key] = ChatGoogleGenerativeAI(
                model=self.settings.gemini_model,
                google_api_key=key,
                temperature=temperature,
                max_retries=1,
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

    def _run(self, temperature: float, call: Callable[[Any], Any]) -> Any:
        """Run `call(model)` on Gemini keys (skipping cooled-down ones), then on Groq."""
        last_exc: Exception | None = None

        for _ in range(len(self.keys)):
            key = self.keys.current()
            if key is None:  # every key is parked: go straight to the fallback provider
                break
            try:
                return call(self._gemini(key, temperature))
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if is_quota_error(exc):
                    seconds = cooldown_seconds(exc)
                    log.warning("Gemini key hit its quota; parking it for %ds", seconds)
                    self.keys.cool_down(key, seconds)
                else:
                    log.warning("Gemini call failed: %s", exc)
                    self.keys.rotate()

        if self.settings.groq_api_key:
            try:
                return call(self._groq_model(temperature))
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                log.warning("Groq fallback failed: %s", exc)

        raise LLMUnavailable(str(last_exc) if last_exc else "No LLM provider configured")

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
