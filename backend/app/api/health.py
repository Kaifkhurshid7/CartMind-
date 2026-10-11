from fastapi import APIRouter

from app.config import get_settings
from app.llm.gemini import get_llm

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    llm = get_llm()
    settings = get_settings()
    return {
        "status": "ok",
        "llm_configured": llm.available,
        "gemini_keys": len(llm.keys),
        "llm_model": settings.gemini_model if llm.keys.available else ("groq" if settings.groq_api_key else None),
        "shopping_mode": settings.shopping_mode,
        "agent_ready": settings.shopping_mode == "agent" and llm.available,
        "site": {"agent": "Web: Google, Amazon, Flipkart", "live": "Amazon.in"}.get(settings.shopping_mode, "Demo store"),
    }
