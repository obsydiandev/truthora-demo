"""Truthora — BGE-M3 embeddings service.

Generates multilingual embeddings using BGE-M3 (BAAI/bge-m3)
via sentence-transformers. Runs on CPU by default for data sovereignty.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded model (avoid import-time downloads)
_model = None
_model_name: str = ""


def _get_model():
    """Lazy-load the BGE-M3 model on first use."""
    global _model, _model_name

    if _model is not None:
        return _model

    model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    _model_name = model_name

    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", model_name)
        _model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully")
    except Exception:
        logger.exception("Failed to load embedding model: %s", model_name)
        raise

    return _model


class EmbeddingService:
    """Generate multilingual embeddings using BGE-M3."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        if model_name:
            os.environ["EMBEDDING_MODEL"] = model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Returns a list of 1024-dimensional float vectors.
        """
        if not texts:
            return []

        model = _get_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        results = self.embed([text])
        if results:
            return results[0]
        return []

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        va = np.array(a)
        vb = np.array(b)
        dot = np.dot(va, vb)
        norm = np.linalg.norm(va) * np.linalg.norm(vb)
        if norm == 0:
            return 0.0
        return float(dot / norm)
