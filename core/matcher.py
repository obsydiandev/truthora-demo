"""Truthora — Semantic claim matcher (BGE-M3 + Qdrant + temporal decay).

Matches extracted claims against indexed fact-checks using:
  1. BGE-M3 multilingual embeddings → Qdrant top-10 nearest
  2. Temporal Freshness Decay: weight(t) = exp(-0.693 × days_old / 180)
  3. Returns ClaimResult with matches and entropy-based uncertainty
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

from api.schemas import (
    Claim,
    ClaimResult,
    FactCheckMatch,
    FreshnessBadge,
    StanceLabel,
)
from services.embeddings import EmbeddingService
from services.qdrant import QdrantService

logger = logging.getLogger(__name__)

# Temporal decay half-life in days
HALF_LIFE_DAYS = 180
DECAY_LAMBDA = 0.693 / HALF_LIFE_DAYS  # ln(2) / half_life


def compute_freshness_decay(published_at: Optional[str | datetime]) -> float:
    """Compute temporal freshness decay weight.

    weight(t) = exp(-0.693 × days_old / 180)
    Returns 1.0 for very recent, 0.5 at 180 days, 0.25 at 360 days.
    """
    if published_at is None:
        return 0.5  # Default to 180-day-old equivalent

    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return 0.5

    now = datetime.now(timezone.utc)
    days_old = max(0, (now - published_at).days)
    return math.exp(-DECAY_LAMBDA * days_old)


def get_freshness_badge(published_at: Optional[str | datetime]) -> FreshnessBadge:
    """Determine the freshness badge based on publication date.

    🟢 Fresh: < 30 days
    🟡 Aging: < 1 year (365 days)
    🔴 Outdated: >= 1 year
    """
    if published_at is None:
        return FreshnessBadge.AGING

    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return FreshnessBadge.AGING

    now = datetime.now(timezone.utc)
    days_old = (now - published_at).days

    if days_old < 30:
        return FreshnessBadge.FRESH
    elif days_old < 365:
        return FreshnessBadge.AGING
    else:
        return FreshnessBadge.OUTDATED


def compute_entropy(scores: list[float]) -> float:
    """Compute normalized entropy of a score distribution.

    H = -Σ p_i × log2(p_i), normalized to [0, 1].

    H < 0.30 → system confident (one clear match)
    H 0.30–0.70 → moderate confidence
    H > 0.70 → ⚠️ mandatory flag — manual review required
    """
    if not scores or len(scores) < 2:
        return 0.0

    # Normalize scores to a probability distribution
    total = sum(scores)
    if total == 0:
        return 1.0

    probs = [s / total for s in scores]
    # Filter out zeros (log2(0) is undefined)
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


class ClaimMatcher:
    """Match claims against indexed fact-checks using semantic similarity."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        qdrant_service: QdrantService | None = None,
    ) -> None:
        self._embeddings = embedding_service or EmbeddingService()
        self._qdrant = qdrant_service or QdrantService()

    async def match(self, claim: Claim, top_k: int = 10) -> ClaimResult:
        """Find matching fact-checks for a claim.

        Returns a ClaimResult with top matches and uncertainty score.
        """
        # Generate embedding for the claim
        try:
            query_vector = self._embeddings.embed_single(claim.claim_text)
        except Exception:
            logger.exception("Failed to generate embedding for claim")
            return ClaimResult(
                claim=claim,
                matches=[],
                uncertainty=1.0,
                uncertainty_level="HIGH",
            )

        if not query_vector:
            return ClaimResult(
                claim=claim,
                matches=[],
                uncertainty=1.0,
                uncertainty_level="HIGH",
            )

        # Search Qdrant for nearest fact-checks
        try:
            hits = self._qdrant.search_fact_checks(query_vector, limit=top_k)
        except Exception:
            logger.exception("Qdrant search failed")
            hits = []

        # Build match results with freshness decay
        matches: list[FactCheckMatch] = []
        scores: list[float] = []

        for hit in hits:
            payload = hit.get("payload", {})
            similarity = hit.get("score", 0.0)
            published_at = payload.get("published_at")
            decay = compute_freshness_decay(published_at)
            badge = get_freshness_badge(published_at)

            # In Faza 3, final_score = similarity × freshness_decay
            # (reranker_score and nli_confidence added in Faza 5)
            final_score = similarity * decay

            match = FactCheckMatch(
                matched_url=payload.get("source_url", ""),
                source_name=payload.get("source_name", ""),
                claim_reviewed=payload.get("claim_text", ""),
                stance=StanceLabel.NEI,  # NLI classification added in Faza 5
                similarity_score=similarity,
                freshness_decay=decay,
                freshness_badge=badge,
                final_score=final_score,
                published_at=published_at,
            )
            matches.append(match)
            scores.append(final_score)

        # Sort by final score descending
        matches.sort(key=lambda m: m.final_score, reverse=True)

        # Compute entropy-based uncertainty
        top_scores = [m.final_score for m in matches[:5]]
        uncertainty = compute_entropy(top_scores)
        uncertainty_level = get_uncertainty_level(uncertainty)

        return ClaimResult(
            claim=claim,
            matches=matches,
            uncertainty=round(uncertainty, 4),
            uncertainty_level=uncertainty_level,
        )

    def index_fact_check(
        self,
        point_id: str,
        claim_text: str,
        metadata: dict[str, Any],
    ) -> None:
        """Index a fact-check into Qdrant for future matching.

        Args:
            point_id: Unique identifier for the fact-check
            claim_text: Text of the claim to embed
            metadata: Additional payload (source_url, source_name, published_at, etc.)
        """
        vector = self._embeddings.embed_single(claim_text)
        if not vector:
            logger.warning("Empty embedding for fact-check: %s", point_id)
            return

        payload = {
            "claim_text": claim_text,
            **metadata,
        }
        self._qdrant.upsert_fact_check(point_id, vector, payload)
        logger.info("Indexed fact-check: %s", point_id)
