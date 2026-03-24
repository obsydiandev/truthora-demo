"""Final scoring pipeline."""

from __future__ import annotations

import logging
import math

from api.schemas import KGSignal
from core.knowledge_graph import kg_signal_to_score

logger = logging.getLogger(__name__)

SCORE_WEIGHTS = {
    "similarity": 0.35,
    "reranker_score": 0.25,
    "nli_confidence": 0.20,
    "freshness_decay": 0.12,
    "kg_signal": 0.08,
}


def compute_final_score(
    similarity: float,
    reranker_score: float,
    nli_confidence: float,
    freshness_decay: float,
    kg_signal: KGSignal | None = None,
) -> float:
    """Compute the weighted final score for a claim-match pair.

    All input scores should be in [0, 1]. The output is in [0, 1].
    """
    kg_score = kg_signal_to_score(kg_signal) if kg_signal else 0.5

    score = (
        similarity * SCORE_WEIGHTS["similarity"]
        + reranker_score * SCORE_WEIGHTS["reranker_score"]
        + nli_confidence * SCORE_WEIGHTS["nli_confidence"]
        + freshness_decay * SCORE_WEIGHTS["freshness_decay"]
        + kg_score * SCORE_WEIGHTS["kg_signal"]
    )

    return max(0.0, min(1.0, score))


def compute_entropy(scores: list[float]) -> float:
    """Compute normalized entropy of a score distribution.

    H = -Σ p_i × log2(p_i), normalized to [0, 1].
    """
    if not scores or len(scores) < 2:
        return 0.0

    total = sum(scores)
    if total == 0:
        return 1.0

    probs = [s / total for s in scores]
    probs = [p for p in probs if p > 0]

    if len(probs) <= 1:
        return 0.0

    entropy = -sum(p * math.log2(p) for p in probs)
    max_entropy = math.log2(len(probs))

    if max_entropy == 0:
        return 0.0

    return entropy / max_entropy


def get_uncertainty_level(entropy: float) -> str:
    """Map entropy to human-readable uncertainty level."""
    if entropy < 0.30:
        return "LOW"
    elif entropy <= 0.70:
        return "MODERATE"
    else:
        return "HIGH"


def compute_uncertainty(top_scores: list[float]) -> tuple[float, str]:
    """Compute entropy-based uncertainty and level for top-5 scores."""
    entropy = compute_entropy(top_scores)
    level = get_uncertainty_level(entropy)
    return round(entropy, 4), level
