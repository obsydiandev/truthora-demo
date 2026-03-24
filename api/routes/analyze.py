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


def _compute_verdict(results: list[ClaimResult]) -> tuple[str, float]:
    """Derive an overall verdict and confidence from all claim results.

    Returns (verdict, confidence) where verdict is one of:
      VERIFIED, LIKELY_FALSE, UNVERIFIED, NO_DATA
    """
    if not results:
        return "NO_DATA", 0.0

    all_matches = [m for r in results for m in r.matches]
    if not all_matches:
        return "NO_DATA", 0.0

    stances = [m.stance for m in all_matches]
    scores = [m.final_score for m in all_matches]

    supported = sum(1 for s in stances if s == "SUPPORTED")
    refuted = sum(1 for s in stances if s == "REFUTED")
    total = len(stances)

    avg_score = sum(scores) / len(scores) if scores else 0.0
    avg_uncertainty = sum(r.uncertainty for r in results) / len(results)

    # Confidence = average final_score × (1 - avg_uncertainty)
    confidence = round(avg_score * (1 - avg_uncertainty), 3)

    if total == 0:
        return "NO_DATA", 0.0
    elif refuted / total >= 0.4:
        return "LIKELY_FALSE", confidence
    elif supported / total >= 0.4:
        return "VERIFIED", confidence
    elif avg_uncertainty > 0.7:
        return "NO_DATA", confidence
    else:
        return "UNVERIFIED", confidence


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

    verdict, confidence = _compute_verdict(results)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return AnalyzeResponse(
        url=source_url,
        title=extraction.get("title"),
        language=extraction.get("language"),
        claims=results,
        processing_time_ms=round(elapsed_ms, 2),
        verdict=verdict,
        confidence=confidence,
    )
