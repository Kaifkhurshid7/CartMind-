from fastapi import APIRouter

from app.llm.gemini import get_llm

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    llm = get_llm()
    return {"status": "ok", "llm_configured": llm.available, "gemini_keys": len(llm.keys)}
