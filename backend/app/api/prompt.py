from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm import prompts
from app.llm.gemini import LLMUnavailable, get_llm

router = APIRouter(prefix="/api/prompt", tags=["prompt"])


class ImproveRequest(BaseModel):
    text: str = Field(min_length=3, max_length=1000)


@router.post("/improve")
def improve(req: ImproveRequest):
    """Rewrite a shopping request to be clearer for the agent (one model call)."""
    try:
        reply = get_llm().invoke(prompts.IMPROVE_PROMPT.format(text=req.text.strip()), system=prompts.SYSTEM, temperature=0.3)
    except LLMUnavailable:
        raise HTTPException(503, "Improving prompts needs an AI model. Add GEMINI_API_KEY_1 to .env and restart.")
    improved = reply.strip().strip('"').strip()
    return {"prompt": improved or req.text.strip()}
