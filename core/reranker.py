"""Reranking + NLI stance classification."""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

from api.schemas import StanceLabel

logger = logging.getLogger(__name__)

_reranker_model = None
_nli_model = None
_nli_tokenizer = None


def _get_reranker():
    """Lazy-load BGE-Reranker-v2-m3 model."""
    global _reranker_model
    if _reranker_model is not None:
        return _reranker_model

    try:
        from sentence_transformers import CrossEncoder

        model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        logger.info("Loading reranker model: %s", model_name)
        _reranker_model = CrossEncoder(model_name)
        logger.info("Reranker model loaded successfully")
    except Exception:
        logger.exception("Failed to load reranker model")
        _reranker_model = None

    return _reranker_model


def _get_nli_model():
    """Lazy-load DeBERTa-v3-MNLI model for stance classification."""
    global _nli_model, _nli_tokenizer
    if _nli_model is not None:
        return _nli_model, _nli_tokenizer

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        model_name = os.getenv("NLI_MODEL", "cross-encoder/nli-deberta-v3-small")
        logger.info("Loading NLI model: %s", model_name)
        _nli_tokenizer = AutoTokenizer.from_pretrained(model_name)
        _nli_model = AutoModelForSequenceClassification.from_pretrained(model_name)
        logger.info("NLI model loaded successfully")
    except Exception:
        logger.exception("Failed to load NLI model")
        _nli_model = None
        _nli_tokenizer = None

    return _nli_model, _nli_tokenizer


class Reranker:
    """Rerank fact-check matches and classify stance (NLI)."""

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """Rerank documents against a query using BGE-Reranker-v2-m3.

        Args:
            query: The claim text
            documents: List of fact-check texts to rerank
            top_k: Number of top results to return

        Returns:
            List of (original_index, reranker_score) tuples, sorted by score desc.
            Returns original indices with 0.5 score if model not available.
        """
        model = _get_reranker()
        if model is None:
            return [(i, 0.5) for i in range(min(top_k, len(documents)))]

        if not documents:
            return []

        pairs = [(query, doc) for doc in documents]

        try:
            scores = model.predict(pairs)
            normalized = 1 / (1 + np.exp(-np.array(scores)))

            indexed_scores = list(enumerate(normalized.tolist()))
            indexed_scores.sort(key=lambda x: x[1], reverse=True)

            return indexed_scores[:top_k]
        except Exception:
            logger.exception("Reranking failed")
            return [(i, 0.5) for i in range(min(top_k, len(documents)))]

    def classify_stance(
        self,
        claim: str,
        evidence: str,
    ) -> tuple[StanceLabel, float]:
        """Classify the logical relationship between a claim and evidence.

        Uses DeBERTa-v3-MNLI for Natural Language Inference.

        Args:
            claim: The claim text (hypothesis)
            evidence: The fact-check text (premise)

        Returns:
            Tuple of (StanceLabel, confidence) where confidence is in [0, 1].
            Returns (NEI, 0.33) if model not available.
        """
        model, tokenizer = _get_nli_model()
        if model is None or tokenizer is None:
            return StanceLabel.NEI, 0.33

        try:
            import torch

            inputs = tokenizer(
                evidence, claim,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )

            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits.numpy()[0]

            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / exp_logits.sum()

            label_map = {
                0: StanceLabel.REFUTED,    # contradiction
                1: StanceLabel.NEI,        # neutral
                2: StanceLabel.SUPPORTED,  # entailment
            }

            predicted_idx = int(np.argmax(probs))
            confidence = float(probs[predicted_idx])
            stance = label_map[predicted_idx]

            return stance, confidence

        except Exception:
            logger.exception("NLI stance classification failed")
            return StanceLabel.NEI, 0.33
