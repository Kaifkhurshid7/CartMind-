"""Shared fixtures. Environment is configured BEFORE the app is imported so tests never touch real data."""

import os
import socket
import tempfile
import threading
import time
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="cartmind-tests-"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _free_port()
os.environ.update(
    DATABASE_URL=f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    CHECKPOINT_DB=str(_TMP / "checkpoints.db"),
    STORE_URL=f"http://127.0.0.1:{PORT}/store",
    PLAYWRIGHT_HEADLESS="true",
    GEMINI_API_KEY_1="",
    GEMINI_API_KEY_2="",
    GEMINI_API_KEY_3="",
    GROQ_API_KEY="",
)

import httpx  # noqa: E402
import pytest  # noqa: E402
import uvicorn  # noqa: E402

from app.database.database import init_db  # noqa: E402
from app.store import catalog  # noqa: E402


@pytest.fixture(scope="session")
def live_server():
    """The real FastAPI app (API + demo store) on a free port, so Playwright has a site to drive."""
    from app.main import app

    init_db()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            if httpx.get(f"http://127.0.0.1:{PORT}/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        raise RuntimeError("test server did not start")
    yield f"http://127.0.0.1:{PORT}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _reset_store():
    catalog.clear_overrides()
    yield
    catalog.clear_overrides()


@pytest.fixture
def client(live_server):
    with httpx.Client(base_url=live_server, timeout=60) as c:
        yield c


def wait_for_status(client: httpx.Client, session_id: str, targets: set[str], timeout: float = 90) -> dict:
    deadline = time.time() + timeout
    data: dict = {}
    while time.time() < deadline:
        data = client.get(f"/api/shopping/{session_id}").json()
        if data["status"] in targets:
            return data
        time.sleep(0.4)
    raise AssertionError(f"Timed out waiting for {targets}; last status={data.get('status')} error={data.get('error')}")
