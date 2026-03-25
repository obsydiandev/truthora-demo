"""POST /analyze endpoint (URL or headline → claims)."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException

from api.schemas import AnalyzeRequest, AnalyzeResponse, ClaimResult
from core.detector import ClaimDetector
from core.extractor import extract_text
from core.matcher import ClaimMatcher
from core.normalizer import normalize_claims

router = APIRouter()


def _compute_verdict(results: list[ClaimResult]) -> tuple[str, float, str]:
    """Derive an overall verdict, confidence, and explanation from claim results.

    Confidence = consensus_weight(0.6) × consensus + quality_weight(0.4) × avg_quality
    - consensus: how strongly the dominant stance dominates (majority/total)
    - quality: average final_score of matches

    Returns (verdict, confidence, explanation).
    """
    if not results:
        return "NO_DATA", 0.0, "No claims were detected in this content."

    all_matches = [m for r in results for m in r.matches]
    if not all_matches:
        return "NO_DATA", 0.0, "No fact-check matches found for the detected claims."

    stances = [
        m.stance.value if hasattr(m.stance, "value") else m.stance
        for m in all_matches
    ]
    scores = [m.final_score for m in all_matches]
    total = len(stances)

    supported = sum(1 for s in stances if s == "SUPPORTED")
    refuted = sum(1 for s in stances if s == "REFUTED")
    nei = total - supported - refuted

    # Dominant stance
    dominant_count = max(supported, refuted, nei)
    consensus = dominant_count / total if total else 0.0

    avg_score = sum(scores) / total if total else 0.0

    # Confidence: consensus (0.6) + quality (0.4)
    confidence = round(consensus * 0.6 + avg_score * 0.4, 3)
    confidence = max(0.0, min(1.0, confidence))

    # Count outdated
    outdated = sum(
        1 for m in all_matches
        if (m.freshness_badge.value if hasattr(m.freshness_badge, "value") else m.freshness_badge) == "outdated"
    )

    # Determine verdict
    avg_uncertainty = sum(r.uncertainty for r in results) / len(results)
    if total == 0:
        verdict = "NO_DATA"
    elif refuted / total >= 0.4:
        verdict = "LIKELY_FALSE"
    elif supported / total >= 0.4:
        verdict = "VERIFIED"
    elif avg_uncertainty > 0.7:
        verdict = "NO_DATA"
    else:
        verdict = "UNVERIFIED"

    # Build explanation
    parts: list[str] = []
    if refuted > 0 or supported > 0:
        dominant_label = "refute" if refuted >= supported else "support"
        dominant_n = refuted if refuted >= supported else supported
        parts.append(f"{dominant_n} of {total} matched fact-checks {dominant_label} this claim")

    quality_word = "high" if avg_score >= 0.7 else "moderate" if avg_score >= 0.45 else "low"
    parts.append(f"Match quality: {quality_word} (avg score {avg_score:.2f})")

    if outdated > 0:
        parts.append(
            f"{outdated} of {total} match{'es are' if outdated != 1 else ' is'} "
            f"outdated — manual review recommended"
        )

    if consensus < 0.6 and total >= 3:
        parts.append(
            f"Matches conflict in stance ({supported} supported vs "
            f"{refuted} refuted vs {nei} NEI). Human verification required"
        )

    explanation = ". ".join(parts) + "." if parts else ""

    return verdict, confidence, explanation


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(request: AnalyzeRequest) -> AnalyzeResponse:
    start = time.perf_counter()

    if not request.url and not request.headline:
        raise HTTPException(status_code=422, detail="Provide either 'url' or 'headline'")

    if request.headline:
        extraction = {
            "text": request.headline,
            "title": request.headline[:120],
            "language": None,
            "url": "headline://input",
        }
        source_url = "headline://input"
    else:
        source_url = str(request.url)
        extraction = await extract_text(source_url)
        if extraction is None:
            raise HTTPException(status_code=422, detail=f"Could not extract text from {source_url}")

    detector = ClaimDetector()
    raw_claims = await detector.detect_claims(
        text=extraction["text"],
        language=extraction.get("language", "en"),
    )

    claims = normalize_claims(raw_claims)

    for claim in claims:
        claim.claim_id = uuid.uuid4().hex[:12]

    matcher = ClaimMatcher()
    results: list[ClaimResult] = []
    for claim in claims:
        match_result = await matcher.match(claim)
        results.append(match_result)

    verdict, confidence, explanation = _compute_verdict(results)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Use detected language from extraction, or infer from first claim
    response_language = extraction.get("language")
    if not response_language and claims:
        response_language = getattr(claims[0], "language", None)

    return AnalyzeResponse(
        url=source_url,
        title=extraction.get("title"),
        language=response_language,
        claims=results,
        processing_time_ms=round(elapsed_ms, 2),
        verdict=verdict,
        confidence=confidence,
        verdict_explanation=explanation,
    )
