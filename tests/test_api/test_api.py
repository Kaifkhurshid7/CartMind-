import httpx

from tests.conftest import wait_for_status

WAITING = {"waiting_for_approval", "failed", "no_results", "needs_clarification"}


def _start(client: httpx.Client, query="I need a laptop under ₹50,000 for coding with 16GB RAM and 512GB storage") -> str:
    r = client.post("/api/shopping/start", json={"query": query})
    assert r.status_code == 200
    return r.json()["session_id"]


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["llm_configured"] is False


def test_start_validates_input(client):
    assert client.post("/api/shopping/start", json={"query": "x"}).status_code == 422


def test_unknown_session_is_404(client):
    assert client.get("/api/shopping/nope/status").status_code == 404
    assert client.post("/api/chat/nope", json={"message": "hi"}).status_code == 404


def test_session_lifecycle_and_recommendations(client):
    sid = _start(client)
    data = wait_for_status(client, sid, WAITING)
    assert data["status"] == "waiting_for_approval"

    status = client.get(f"/api/shopping/{sid}/status").json()
    assert status["status"] == "waiting_for_approval"

    recs = client.get(f"/api/shopping/{sid}/recommendations").json()
    assert recs["recommendation"]["product"]["price"] <= 50000
    assert recs["comparison"]["table"] and recs["products"]
    assert [s["id"] for s in client.get("/api/shopping/sessions").json()].count(sid) == 1


def test_session_payload_exposes_near_misses_and_price_change_fields(client):
    sid = _start(client, "laptop under 20000 with 16GB RAM")
    data = wait_for_status(client, sid, {"no_results"})
    assert "near_misses" in data and "price_change" in data


def test_approve_requires_waiting_state(client):
    sid = _start(client, "I want something nice")
    wait_for_status(client, sid, {"needs_clarification"})
    assert client.post(f"/api/shopping/{sid}/approve", json={"approved": True}).status_code == 409
    assert client.post(f"/api/shopping/{sid}/execute").status_code == 409


def test_approve_adds_to_cart(client):
    sid = _start(client, "wireless headphones under 5000 with ANC")
    wait_for_status(client, sid, WAITING)
    assert client.post(f"/api/shopping/{sid}/approve", json={"approved": True}).json()["status"] == "executing"
    done = wait_for_status(client, sid, {"completed", "failed"})
    assert done["status"] == "completed" and done["cart_state"]["items"]


def test_double_approve_is_rejected(client):
    sid = _start(client, "wireless headphones under 5000 with ANC")
    wait_for_status(client, sid, WAITING)
    assert client.post(f"/api/shopping/{sid}/approve", json={"approved": True}).status_code == 200
    assert client.post(f"/api/shopping/{sid}/approve", json={"approved": True}).status_code == 409
    wait_for_status(client, sid, {"completed", "failed"})


def test_cancel_endpoint(client):
    sid = _start(client, "wireless headphones under 5000 with ANC")
    wait_for_status(client, sid, WAITING)
    client.post(f"/api/shopping/{sid}/cancel")
    data = wait_for_status(client, sid, {"cancelled"})
    assert data["cart_state"] == {}


def test_chat_question_refine_and_approve_intents(client):
    sid = _start(client)
    wait_for_status(client, sid, WAITING)

    q = client.post(f"/api/chat/{sid}", json={"message": "Why did you choose this?"}).json()
    assert q["intent"] == "question" and q["reply"]

    a = client.post(f"/api/chat/{sid}", json={"message": "Add it to cart"}).json()
    assert a["intent"] == "approve" and a["action"] == "request_approval"
    # chat alone never performs the purchase action
    assert client.get(f"/api/shopping/{sid}/status").json()["status"] == "waiting_for_approval"

    r = client.post(f"/api/chat/{sid}", json={"message": "Actually increase budget to 60k"}).json()
    assert r["intent"] == "refine" and r["action"] == "replanning"
    data = wait_for_status(client, sid, WAITING)
    assert data["requirements"]["budget"]["maximum"] == 60000


def test_sse_stream_replays_activity(client, live_server):
    sid = _start(client, "wireless headphones under 5000 with ANC")
    wait_for_status(client, sid, WAITING)
    seen = []
    with httpx.stream("GET", f"{live_server}/api/shopping/{sid}/events", timeout=10) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            seen.append(line)
            if "Waiting for your approval" in line:
                break
    assert any(line.startswith("event: activity") for line in seen)


def test_improve_prompt_needs_a_model_and_validates_input(client):
    r = client.post("/api/prompt/improve", json={"text": "laptop under 50k"})
    assert r.status_code == 503 and "AI model" in r.json()["detail"]
    assert client.post("/api/prompt/improve", json={"text": "x"}).status_code == 422


def test_improve_prompt_returns_the_rewrite(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import prompt as prompt_api
    from app.main import app

    class Fake:
        def invoke(self, text, system=None, temperature=0.2):
            assert "laptop under 50k" in text
            return ' "A laptop under ₹50,000 for coding with at least 16GB RAM." '

    monkeypatch.setattr(prompt_api, "get_llm", lambda: Fake())
    with TestClient(app) as c:
        out = c.post("/api/prompt/improve", json={"text": "laptop under 50k"}).json()
    assert out["prompt"] == "A laptop under ₹50,000 for coding with at least 16GB RAM."
