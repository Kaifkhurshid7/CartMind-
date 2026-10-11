from functools import lru_cache

from app.config import get_settings
from app.rag.vectorstore import VectorStore, load_chunks


@lru_cache
def _store() -> VectorStore:
    return VectorStore(load_chunks(get_settings().knowledge_base_dir))


def retrieve_context(query: str, k: int = 3) -> str:
    """Relevant knowledge-base passages for `query`, or '' when nothing is relevant."""
    try:
        hits = _store().search(query, k=k)
    except Exception:  # noqa: BLE001  (RAG is optional; never break chat)
        return ""
    return "\n\n".join(f"[{c.source}] {c.text}" for c, _ in hits)
