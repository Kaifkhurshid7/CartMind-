import re
from dataclasses import dataclass
from pathlib import Path

from app.rag.embeddings import TfidfEmbedder, cosine


@dataclass
class Chunk:
    source: str
    text: str


def load_chunks(directory: str) -> list[Chunk]:
    """One chunk per markdown section ("## Heading"), keeping the heading as context."""
    chunks: list[Chunk] = []
    for path in sorted(Path(directory).glob("*.md")):
        for section in re.split(r"\n(?=## )", path.read_text(encoding="utf-8")):
            text = section.strip()
            if text.startswith("## ") and "\n" in text:
                chunks.append(Chunk(path.stem, text))
    return chunks


class VectorStore:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.embedder = TfidfEmbedder()
        self.embedder.fit([c.text for c in chunks])
        self.vectors = [self.embedder.embed(c.text) for c in chunks]

    def search(self, query: str, k: int = 3, min_score: float = 0.12) -> list[tuple[Chunk, float]]:
        q = self.embedder.embed(query)
        scored = sorted(((c, cosine(q, v)) for c, v in zip(self.chunks, self.vectors)), key=lambda x: -x[1])
        return [(c, s) for c, s in scored[:k] if s >= min_score]
