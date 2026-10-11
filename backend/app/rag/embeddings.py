"""Dependency-free TF-IDF "embeddings" for the optional knowledge base.

Swap this module for Gemini embeddings (langchain-google-genai) + FAISS/Chroma when the corpus grows;
the vectorstore/retriever interfaces stay the same.
"""

import math
import re
from collections import Counter

STOPWORDS = {"the", "a", "an", "is", "are", "of", "for", "to", "and", "or", "in", "on", "it", "this", "that", "with",
             "what", "which", "how", "do", "does", "i", "my", "me", "be", "can", "than", "vs", "between", "difference"}


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 1]


class TfidfEmbedder:
    def __init__(self) -> None:
        self.idf: dict[str, float] = {}

    def fit(self, documents: list[str]) -> None:
        df: Counter = Counter()
        for doc in documents:
            df.update(set(tokenize(doc)))
        n = len(documents)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def embed(self, text: str) -> dict[str, float]:
        tf = Counter(tokenize(text))
        vec = {t: c * self.idf.get(t, 0.0) for t, c in tf.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())
