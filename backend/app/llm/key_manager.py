import re
import threading
import time


class KeyManager:
    """Round-robin Gemini key pool with quota cool-downs.

    A key that hit its quota is parked for a while so later calls skip it (and fall through to the
    fallback provider immediately) instead of failing again on every request.
    """

    def __init__(self, keys: list[str]):
        self._keys = list(keys)
        self._index = 0
        self._cooling: dict[str, float] = {}  # key -> monotonic time when usable again
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._keys)

    @property
    def available(self) -> bool:
        """Any keys configured at all (even if currently cooling down)."""
        return bool(self._keys)

    def _is_cooling(self, key: str) -> bool:
        until = self._cooling.get(key)
        if until is None:
            return False
        if time.monotonic() >= until:
            del self._cooling[key]
            return False
        return True

    @property
    def usable(self) -> bool:
        with self._lock:
            return any(not self._is_cooling(k) for k in self._keys)

    def current(self) -> str | None:
        """The key to use now, or None if every key is cooling down."""
        with self._lock:
            for offset in range(len(self._keys)):
                key = self._keys[(self._index + offset) % len(self._keys)]
                if not self._is_cooling(key):
                    self._index = (self._index + offset) % len(self._keys)
                    return key
            return None

    def rotate(self) -> str | None:
        with self._lock:
            if not self._keys:
                return None
            self._index = (self._index + 1) % len(self._keys)
        return self.current()

    def cool_down(self, key: str, seconds: float) -> None:
        with self._lock:
            self._cooling[key] = time.monotonic() + seconds


def is_quota_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(m in text for m in ("429", "quota", "resource_exhausted", "resourceexhausted", "rate limit", "rate_limit"))


def cooldown_seconds(exc: Exception) -> float:
    """Daily quotas park the key for hours; per-minute limits only for about a minute."""
    text = str(exc).lower()
    return 6 * 3600 if re.search(r"per\s?day|daily|perday", text) else 70
