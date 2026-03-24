"""GET/PATCH /claims endpoints (review queue)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.schemas import ClaimReviewRequest, ClaimReviewResponse, ClaimResult
from services.qdrant import QdrantService

router = APIRouter()


@router.get("/claims", response_model=list[ClaimResult])
async def list_claims(
    limit: int = 20,
    offset: int = 0,
) -> list[ClaimResult]:
    """Return pending claims from the review queue."""
    qdrant = QdrantService()
    results = await qdrant.get_pending_claims(limit=limit, offset=offset)
    return results


@router.patch("/claims/{claim_id}", response_model=ClaimReviewResponse)
async def review_claim(
    claim_id: str,
    body: ClaimReviewRequest,
) -> ClaimReviewResponse:
    """Record an operator's review decision for a claim."""
    qdrant = QdrantService()
    stored = await qdrant.record_review(
        claim_id=claim_id,
        action=body.action,
        note=body.note,
    )
    if not stored:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    return ClaimReviewResponse(
        claim_id=claim_id,
        action=body.action,
        note=body.note,
        timestamp=datetime.now(timezone.utc),
    )
