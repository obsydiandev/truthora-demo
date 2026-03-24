"""Truthora — Final scoring pipeline (Layer 6).

Computes the composite final_score for each claim-match pair:

    final_score = (
        similarity     × 0.35
      + reranker_score × 0.25
      + nli_confidence × 0.20
      + freshness_decay × 0.12
      + kg_signal      × 0.08
    )

Also computes entropy-based uncertainty for operator flagging:
    H = -Σ p_i × log2(p_i) [normalized to 0–1]
    H < 0.30 → LOW (system confident)
    H 0.30–0.70 → MODERATE
    H > 0.70 → HIGH (⚠️ mandatory flag)
"""

from __future__ import annotations

import logging
import math

from api.schemas import KGSignal
from core.knowledge_graph import kg_signal_to_score
from core.matcher import compute_entropy, get_uncertainty_level

logger = logging.getLogger(__name__)

# Final score component weights (must sum to 1.0)
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

    # Clamp to [0, 1]
    return max(0.0, min(1.0, score))


def compute_uncertainty(top_scores: list[float]) -> tuple[float, str]:
    """Compute entropy-based uncertainty and level for top-5 scores.

    Returns:
        Tuple of (entropy, uncertainty_level)
        entropy: float in [0, 1]
        uncertainty_level: "LOW" | "MODERATE" | "HIGH"
    """
    entropy = compute_entropy(top_scores)
    level = get_uncertainty_level(entropy)
    return round(entropy, 4), level
