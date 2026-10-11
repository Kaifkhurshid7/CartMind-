import threading


class KeyManager:
    """Round-robin Gemini key pool. `rotate()` is called when a key hits a quota/rate limit."""

    def __init__(self, keys: list[str]):
        self._keys = list(keys)
        self._index = 0
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._keys)

    @property
    def available(self) -> bool:
        return bool(self._keys)

    def current(self) -> str:
        with self._lock:
            if not self._keys:
                raise RuntimeError("No Gemini API keys configured")
            return self._keys[self._index]

    def rotate(self) -> str:
        with self._lock:
            if not self._keys:
                raise RuntimeError("No Gemini API keys configured")
            self._index = (self._index + 1) % len(self._keys)
            return self._keys[self._index]


def is_quota_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(m in text for m in ("429", "quota", "resource_exhausted", "resourceexhausted", "rate limit", "rate_limit"))
