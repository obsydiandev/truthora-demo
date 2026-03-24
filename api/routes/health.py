"""Health check endpoint."""

from fastapi import APIRouter

from api.schemas import HealthResponse
from services.qdrant import QdrantService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    qdrant = QdrantService()
    qdrant_ok = await qdrant.is_healthy()
    return HealthResponse(
        status="ok" if qdrant_ok else "degraded",
        version="0.1.0",
        qdrant_connected=qdrant_ok,
    )
