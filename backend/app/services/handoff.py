"""Human hand-off for browser steps only a person should do (logging in, solving a robot check).

The agent thread blocks in `request_user_action` while the UI shows a "Continue" card.
In-process only: a server restart drops any pending hand-off.
"""

import threading

from app.services import sessions

_events: dict[str, threading.Event] = {}
_aborted: set[str] = set()
_lock = threading.Lock()


def request_user_action(session_id: str, message: str, timeout: float) -> bool:
    """Block until the user clicks Continue. False if they cancelled or the wait timed out."""
    event = threading.Event()
    with _lock:
        _events[session_id] = event
        _aborted.discard(session_id)
    sessions.update_session(session_id, status="waiting_for_user", current_step="user_action", user_prompt=message)
    sessions.emit_event(session_id, "user_action", message, "waiting")
    try:
        signalled = event.wait(timeout)
    finally:
        with _lock:
            _events.pop(session_id, None)
            aborted = session_id in _aborted
            _aborted.discard(session_id)
    sessions.update_session(session_id, status="running", current_step="browser", user_prompt=None)
    return signalled and not aborted


def is_waiting(session_id: str) -> bool:
    with _lock:
        return session_id in _events


def resume(session_id: str) -> bool:
    with _lock:
        event = _events.get(session_id)
    if event is None:
        return False
    event.set()
    return True


def abort(session_id: str) -> bool:
    with _lock:
        event = _events.get(session_id)
        if event is None:
            return False
        _aborted.add(session_id)
    event.set()
    return True
