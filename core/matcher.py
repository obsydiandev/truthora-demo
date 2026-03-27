"""Semantic claim matcher (BGE-M3 + Qdrant + temporal decay)."""

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
from core.reranker import Reranker
from core.scorer import compute_entropy, compute_final_score, get_uncertainty_level
from services.embeddings import EmbeddingService
from services.qdrant import QdrantService

logger = logging.getLogger(__name__)

HALF_LIFE_DAYS = 180
DECAY_LAMBDA = 0.693 / HALF_LIFE_DAYS  # ln(2) / half_life

_LANG_MAP = {"ua": "uk"}  # detector uses "ua", Qdrant payloads use ISO 639-1 "uk"


def _map_language(lang: str | None) -> str | None:
    """Normalize detector language code to Qdrant payload value."""
    if lang is None:
        return None
    return _LANG_MAP.get(lang, lang)


def compute_freshness_decay(published_at: Optional[str | datetime]) -> float:
    """Compute temporal freshness decay weight.

    weight(t) = exp(-0.693 × days_old / 180)
    Returns 1.0 for very recent, 0.5 at 180 days, 0.25 at 360 days.
    """
    if published_at is None:
        return 0.5

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


class ClaimMatcher:
    """Match claims against indexed fact-checks using semantic similarity."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        qdrant_service: QdrantService | None = None,
        nli_only: bool = False,
        no_freshness: bool = False,
    ) -> None:
        self._embeddings = embedding_service or EmbeddingService()
        self._qdrant = qdrant_service or QdrantService()
        self._reranker = Reranker()
        self._nli_only = nli_only
        self._no_freshness = no_freshness

    # Map fact-checker verdicts to stance labels (exact match, lowercased)
    _RATING_MAP: dict[str, StanceLabel] = {
        # English – REFUTED
        "false": StanceLabel.REFUTED,
        "mostly false": StanceLabel.REFUTED,
        "pants on fire": StanceLabel.REFUTED,
        "pants on fire!": StanceLabel.REFUTED,
        "fake": StanceLabel.REFUTED,
        "incorrect": StanceLabel.REFUTED,
        "inaccurate": StanceLabel.REFUTED,
        "partly false": StanceLabel.REFUTED,
        "mostly false": StanceLabel.REFUTED,
        "not true.": StanceLabel.REFUTED,
        "four pinocchios": StanceLabel.REFUTED,
        "three pinocchios": StanceLabel.REFUTED,
        "bottomless pinocchio": StanceLabel.REFUTED,
        "altered photo/video": StanceLabel.REFUTED,
        "altered video": StanceLabel.REFUTED,
        "fake ai voice": StanceLabel.REFUTED,
        "ai-generated": StanceLabel.REFUTED,
        "scam": StanceLabel.REFUTED,
        "cgi satire": StanceLabel.REFUTED,
        # English – SUPPORTED
        "true": StanceLabel.SUPPORTED,
        "mostly true": StanceLabel.SUPPORTED,
        "correct": StanceLabel.SUPPORTED,
        "correct attribution": StanceLabel.SUPPORTED,
        "one pinocchio": StanceLabel.SUPPORTED,
        "geppetto checkmark": StanceLabel.SUPPORTED,
        "well-studied": StanceLabel.SUPPORTED,
        "earth is round": StanceLabel.SUPPORTED,
        "contrails": StanceLabel.SUPPORTED,
        # English – NEI
        "misleading": StanceLabel.NEI,
        "mixture": StanceLabel.NEI,
        "unproven": StanceLabel.NEI,
        "missing context": StanceLabel.NEI,
        "unsupported": StanceLabel.NEI,
        "not supported": StanceLabel.NEI,
        "lacks context": StanceLabel.NEI,
        "lacks_context": StanceLabel.NEI,
        "out of context": StanceLabel.NEI,
        "half true": StanceLabel.NEI,
        "two pinocchios": StanceLabel.NEI,
        "exaggerated": StanceLabel.NEI,
        "needs context": StanceLabel.NEI,
        "outdated": StanceLabel.NEI,
        "no evidence": StanceLabel.NEI,
        "doubtful": StanceLabel.NEI,
        "unsubstantiated": StanceLabel.NEI,
        "distorts the facts": StanceLabel.NEI,
        "flawed study": StanceLabel.NEI,
        "study in dispute": StanceLabel.NEI,
        "probably at high doses": StanceLabel.NEI,
        "we explain": StanceLabel.NEI,
        "most research disputes": StanceLabel.NEI,
        "humor": StanceLabel.NEI,
        "satire": StanceLabel.NEI,
        # Polish – REFUTED
        "fałsz": StanceLabel.REFUTED,
        "fałsz.": StanceLabel.REFUTED,
        "nieprawda": StanceLabel.REFUTED,
        "manipulacja": StanceLabel.REFUTED,
        "raczej fałsz": StanceLabel.REFUTED,
        "częściowy fałsz": StanceLabel.REFUTED,
        "przerobiony film": StanceLabel.REFUTED,
        # Polish – SUPPORTED
        "prawda": StanceLabel.SUPPORTED,
        # Polish – NEI
        "blisko prawdy": StanceLabel.NEI,
        "półprawda": StanceLabel.NEI,
        "brakujący kontekst": StanceLabel.NEI,
        "brakujący kontekst.": StanceLabel.NEI,
        # Ukrainian – REFUTED
        "брехня": StanceLabel.REFUTED,
        "маніпуляція": StanceLabel.REFUTED,
        "фейк": StanceLabel.REFUTED,
        "неправда": StanceLabel.REFUTED,
        # Ukrainian – SUPPORTED
        "правда": StanceLabel.SUPPORTED,
        # Direct stance labels
        "refuted": StanceLabel.REFUTED,
        "supported": StanceLabel.SUPPORTED,
        "nei": StanceLabel.NEI,
    }

    # Keyword-based fallback for long/descriptive ratings (checked in order).
    # REFUTED checked before SUPPORTED to avoid "not true" matching "true".
    _RATING_KEYWORDS: list[tuple[list[str], StanceLabel]] = [
        (["false", "fake", "fabricat", "debunk", "pinocchio", "scam",
          "hoax", "inaccurat", "not true", "altered", "fałsz", "nieprawda",
          "фейк", "неправда", "брехня"], StanceLabel.REFUTED),
        (["misleading", "missing context", "no evidence", "unproven",
          "unsupported", "mixture", "partly", "cherry-pick", "lacks context",
          "exaggerat", "out of context", "not supported", "needs context",
          "no proof", "distort", "manipul", "brakując", "półprawda",
          "маніпуляц"], StanceLabel.NEI),
        (["true", "correct", "accurate", "confirmed", "prawda", "правда",
          "підтверджено"], StanceLabel.SUPPORTED),
    ]

    def _resolve_stance(
        self,
        claim_text: str,
        evidence_text: str,
        review_rating: str | None,
    ) -> tuple[StanceLabel, float]:
        """Determine stance from review_rating if available, else NLI.

        When self._nli_only is True, always uses NLI model regardless of
        review_rating availability (benchmark mode to measure real NLI
        performance).
        """
        if not self._nli_only and review_rating:
            key = review_rating.strip().lower()
            # Exact match
            if key in self._RATING_MAP:
                return self._RATING_MAP[key], 0.9
            # Keyword fallback for descriptive ratings
            for keywords, stance in self._RATING_KEYWORDS:
                if any(kw in key for kw in keywords):
                    return stance, 0.85
        return self._reranker.classify_stance(claim_text, evidence_text)

    async def match(self, claim: Claim, top_k: int = 10) -> ClaimResult:
        """Find matching fact-checks for a claim.

        Returns a ClaimResult with top matches and uncertainty score.
        """
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

        # Map detector language codes to Qdrant payload values
        lang = _map_language(getattr(claim, "language", None))

        try:
            hits = self._qdrant.search_fact_checks(
                query_vector, limit=top_k, language=lang,
            )
        except Exception:
            logger.exception("Qdrant search failed")
            hits = []

        if not hits:
            return ClaimResult(
                claim=claim,
                matches=[],
                uncertainty=1.0,
                uncertainty_level="HIGH",
            )

        # Extract texts for reranker
        hit_texts = [h.get("payload", {}).get("claim_text", "") for h in hits]

        # Rerank (falls back to original order with score 0.5 if model unavailable)
        reranked = self._reranker.rerank(claim.claim_text, hit_texts, top_k=top_k)

        matches: list[FactCheckMatch] = []

        for orig_idx, reranker_score in reranked:
            hit = hits[orig_idx]
            payload = hit.get("payload", {})
            similarity = hit.get("score", 0.0)
            published_at = payload.get("published_at")
            decay = 1.0 if self._no_freshness else compute_freshness_decay(published_at)
            badge = get_freshness_badge(published_at)
            claim_reviewed = payload.get("claim_text", "")

            # Stance: prefer fact-checker's review_rating, fall back to NLI
            stance, nli_confidence = self._resolve_stance(
                claim.claim_text, claim_reviewed, payload.get("review_rating"),
            )

            final_score = compute_final_score(
                similarity=similarity,
                reranker_score=reranker_score,
                nli_confidence=nli_confidence,
                freshness_decay=decay,
                kg_signal=None,  # TODO: wire KG verification when stable
            )

            match = FactCheckMatch(
                matched_url=payload.get("source_url", ""),
                source_name=payload.get("source_name", ""),
                claim_reviewed=claim_reviewed,
                stance=stance,
                similarity_score=similarity,
                reranker_score=round(reranker_score, 4),
                nli_confidence=round(nli_confidence, 4),
                freshness_decay=decay,
                freshness_badge=badge,
                final_score=final_score,
                published_at=published_at,
            )
            matches.append(match)

        matches.sort(key=lambda m: m.final_score, reverse=True)

        # Deduplicate by URL — keep highest-scoring entry per source URL
        seen_urls: set[str] = set()
        deduped: list[FactCheckMatch] = []
        for m in matches:
            url = m.matched_url
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            deduped.append(m)
        matches = deduped

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
