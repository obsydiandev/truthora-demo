"""Truthora — Qdrant vector database service.

Manages two collections:
  - fact_checks: embeddings of known fact-checks (for semantic retrieval)
  - audit_log:   operator review decisions (human-in-the-loop audit trail)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from api.schemas import ClaimResult, ReviewAction

logger = logging.getLogger(__name__)

# BGE-M3 produces 1024-dimensional embeddings
EMBEDDING_DIM = 1024

FACT_CHECKS_COLLECTION = "fact_checks"
AUDIT_LOG_COLLECTION = "audit_log"


class QdrantService:
    """Client for Qdrant vector DB operations."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self._api_key = api_key or os.getenv("QDRANT_API_KEY") or None
        self._client = QdrantClient(
            url=self._url,
            api_key=self._api_key,
            timeout=10,
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def is_healthy(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except (ResponseHandlingException, Exception):
            return False

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def ensure_collections(self) -> None:
        """Create collections if they don't already exist."""
        existing = {c.name for c in self._client.get_collections().collections}

        if FACT_CHECKS_COLLECTION not in existing:
            self._client.create_collection(
                collection_name=FACT_CHECKS_COLLECTION,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Created collection: %s", FACT_CHECKS_COLLECTION)

        if AUDIT_LOG_COLLECTION not in existing:
            self._client.create_collection(
                collection_name=AUDIT_LOG_COLLECTION,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Created collection: %s", AUDIT_LOG_COLLECTION)

    # ------------------------------------------------------------------
    # Fact-check operations
    # ------------------------------------------------------------------

    def upsert_fact_check(
        self,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Insert or update a fact-check embedding with metadata."""
        self._client.upsert(
            collection_name=FACT_CHECKS_COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    def search_fact_checks(
        self,
        query_vector: list[float],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for top-N nearest fact-checks by embedding similarity."""
        results = self._client.query_points(
            collection_name=FACT_CHECKS_COLLECTION,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results.points
        ]

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def record_audit(
        self,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Write an audit entry (operator decision) to the audit_log collection."""
        self._client.upsert(
            collection_name=AUDIT_LOG_COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    # ------------------------------------------------------------------
    # Review queue (used by /claims endpoints)
    # ------------------------------------------------------------------

    async def get_pending_claims(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ClaimResult]:
        """Return claims that have not been reviewed yet.

        In MVP, this returns an empty list — claims are stored in-memory
        during the /analyze call and served via the Streamlit UI.
        Full persistence will be added when the review queue is built out.
        """
        return []

    async def record_review(
        self,
        claim_id: str,
        action: ReviewAction,
        note: Optional[str] = None,
    ) -> bool:
        """Record an operator review decision in the audit log.

        Returns True if the claim was found and the review was recorded.
        In MVP, we always record (no existence check) and return True.
        """
        payload = {
            "claim_id": claim_id,
            "action": action.value,
            "note": note,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Use a deterministic point ID based on claim + timestamp
        point_id = f"{claim_id}_{int(datetime.now(timezone.utc).timestamp())}"
        # Use a zero vector for audit entries (we don't search by similarity)
        zero_vector = [0.0] * EMBEDDING_DIM
        try:
            self.record_audit(point_id, zero_vector, payload)
            return True
        except Exception:
            logger.exception("Failed to record review for claim %s", claim_id)
            return False
