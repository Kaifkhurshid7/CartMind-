import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.schemas.shopping import ApproveRequest, SessionOut, StartRequest, StartResponse, StatusResponse
from app.services import runner, sessions

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


def _view(session_id: str) -> dict:
    view = sessions.session_view(session_id)
    if view is None:
        raise HTTPException(404, "Session not found")
    return view


@router.post("/start", response_model=StartResponse)
def start(req: StartRequest, background: BackgroundTasks):
    session_id = sessions.create_session(req.query.strip())
    sessions.append_message(session_id, "user", req.query.strip())
    background.add_task(runner.start_run, session_id, req.query.strip())
    return StartResponse(session_id=session_id, status="started")


@router.get("/sessions")
def history():
    return sessions.list_sessions()


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str):
    return _view(session_id)


@router.get("/{session_id}/status", response_model=StatusResponse)
def status(session_id: str):
    v = _view(session_id)
    return StatusResponse(session_id=session_id, status=v["status"], current_step=v["current_step"], error=v["error"])


@router.get("/{session_id}/recommendations")
def recommendations(session_id: str):
    v = _view(session_id)
    rec = v["recommendation"]
    return {
        "status": v["status"],
        "requirements": v["requirements"],
        "recommendation": rec,
        "alternatives": rec.get("alternatives", []) if rec else [],
        "products": v["shortlisted_products"],
        "comparison": v["comparison"],
        "near_misses": v.get("near_misses", []),
    }


@router.get("/{session_id}/events")
async def events(session_id: str):
    """Server-Sent Events: replays the agent activity log, then streams new events and status changes."""
    _view(session_id)

    async def stream():
        last_id, last_status = 0, None
        idle = 0
        while True:
            new = await run_in_threadpool(sessions.list_events, session_id, last_id)
            for e in new:
                last_id = e["id"]
                yield f"event: activity\ndata: {json.dumps(e)}\n\n"
            view = await run_in_threadpool(sessions.session_view, session_id)
            snapshot = (view["status"], view["current_step"]) if view else None
            if snapshot != last_status:
                last_status = snapshot
                if view:
                    yield f"event: status\ndata: {json.dumps({'status': view['status'], 'current_step': view['current_step']})}\n\n"
            idle = 0 if new else idle + 1
            if idle and idle % 30 == 0:
                yield ": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.post("/{session_id}/approve")
def approve(session_id: str, req: ApproveRequest, background: BackgroundTasks):
    v = _view(session_id)
    if v["status"] not in runner.WAITING_STATUSES:
        raise HTTPException(409, f"Nothing is waiting for approval (status: {v['status']})")
    if not req.approved:
        background.add_task(runner.cancel, session_id)
        return {"session_id": session_id, "status": "cancelling"}
    # Flip status immediately so a double click can't resume the graph twice.
    sessions.update_session(session_id, status="executing", current_step="shopping")
    background.add_task(
        runner.resume_run,
        session_id,
        {"approved": True, "product_id": req.product_id, "accept_price_change": req.accept_price_change},
    )
    return {"session_id": session_id, "status": "executing"}


@router.post("/{session_id}/execute")
def execute(session_id: str, background: BackgroundTasks):
    """Start Playwright execution for the current recommendation (same gate as /approve)."""
    v = _view(session_id)
    if v["status"] != "waiting_for_approval":
        raise HTTPException(409, f"Cannot execute from status: {v['status']}. Approval is required first.")
    return approve(session_id, ApproveRequest(approved=True), background)


@router.post("/{session_id}/cancel")
def cancel(session_id: str, background: BackgroundTasks):
    v = _view(session_id)
    if v["status"] in sessions.TERMINAL_STATUSES:
        return {"session_id": session_id, "status": v["status"]}
    background.add_task(runner.cancel, session_id)
    return {"session_id": session_id, "status": "cancelling"}
