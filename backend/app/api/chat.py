from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.shopping import ChatRequest, ChatResponse
from app.services import chat_service, runner, sessions

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{session_id}", response_model=ChatResponse)
def chat(session_id: str, req: ChatRequest, background: BackgroundTasks):
    view = sessions.session_view(session_id)
    if view is None:
        raise HTTPException(404, "Session not found")
    message = req.message.strip()
    sessions.append_message(session_id, "user", message)

    if view["status"] in ("running", "executing"):
        reply = "I'm still working on that — give me a moment, then ask again."
        sessions.append_message(session_id, "assistant", reply)
        return ChatResponse(reply=reply, intent="busy")

    intent = chat_service.classify_intent(message, view["requirements"])

    if intent == "refine":
        reply = "Got it — I'm updating your requirements and searching again."
        sessions.append_message(session_id, "assistant", reply)
        background.add_task(runner.start_run, session_id, view["query"], view["requirements"], message)
        return ChatResponse(reply=reply, intent=intent, action="replanning")

    if intent == "approve":
        if view["status"] == "waiting_for_approval":
            reply = "Please confirm with the “Add to Cart” button so I know you approve the action."
            action = "request_approval"
        else:
            reply, action = "There's no recommendation waiting for approval yet.", None
        sessions.append_message(session_id, "assistant", reply)
        return ChatResponse(reply=reply, intent=intent, action=action)

    if intent == "cancel":
        background.add_task(runner.cancel, session_id)
        reply = "Okay, cancelling. Nothing will be added to your cart."
        sessions.append_message(session_id, "assistant", reply)
        return ChatResponse(reply=reply, intent=intent, action="cancelled")

    reply = chat_service.answer_question(session_id, message)
    sessions.append_message(session_id, "assistant", reply)
    return ChatResponse(reply=reply, intent="question")
