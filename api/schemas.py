"""Pydantic schemas for API request/response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class StanceLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    NEI = "NEI"


class KGSignal(str, Enum):
    KG_FOUND = "KG_FOUND"
    KG_NOT_FOUND = "KG_NOT_FOUND"
    KG_MISMATCH = "KG_MISMATCH"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    FLAG = "flag"


class FreshnessBadge(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    OUTDATED = "outdated"


class CheckworthinessScore(BaseModel):
    harm_potential: float = Field(ge=0, le=1, description="Risk of harm if false (weight: 0.35)")
    virality_potential: float = Field(ge=0, le=1, description="Spread potential (weight: 0.25)")
    verifiability: float = Field(ge=0, le=1, description="Can be fact-checked (weight: 0.20)")
    specificity: float = Field(ge=0, le=1, description="Factual, not opinion (weight: 0.12)")
    public_interest: float = Field(ge=0, le=1, description="Public decision relevance (weight: 0.08)")
    composite: float = Field(ge=0, le=1, description="Weighted composite score")


class Claim(BaseModel):
    claim_id: str
    claim_text: str
    source_quote: str = Field(description="Verbatim quote from source text")
    char_start: int = Field(ge=0, description="Start character position in source")
    char_end: int = Field(ge=0, description="End character position in source")
    language: str = Field(description="Detected language code (en/pl/ua)")
    checkworthiness: CheckworthinessScore
    has_negation: bool = Field(default=False, description="Contains negation particle")


class FactCheckMatch(BaseModel):
    matched_url: str
    source_name: str
    claim_reviewed: str
    stance: StanceLabel
    similarity_score: float = Field(ge=0, le=1)
    reranker_score: Optional[float] = Field(default=None, ge=0, le=1)
    nli_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    freshness_decay: float = Field(ge=0, le=1)
    freshness_badge: FreshnessBadge
    kg_signal: Optional[KGSignal] = None
    final_score: float = Field(ge=0, le=1)
    published_at: Optional[datetime] = None


class ClaimResult(BaseModel):
    claim: Claim
    matches: list[FactCheckMatch] = Field(default_factory=list)
    uncertainty: float = Field(ge=0, le=1, description="Entropy-based uncertainty (0-1)")
    uncertainty_level: str = Field(description="LOW / MODERATE / HIGH")


class AnalyzeRequest(BaseModel):
    url: Optional[HttpUrl] = None
    headline: Optional[str] = Field(default=None, description="Headline or plain text to analyze instead of fetching a URL")


class AnalyzeResponse(BaseModel):
    url: str
    title: Optional[str] = None
    language: Optional[str] = None
    claims: list[ClaimResult] = Field(default_factory=list)
    processing_time_ms: float
    verdict: Optional[str] = None  # VERIFIED / UNVERIFIED / LIKELY_FALSE / NO_DATA
    confidence: Optional[float] = None  # 0-1


class ClaimReviewRequest(BaseModel):
    action: ReviewAction
    note: Optional[str] = None


class ClaimReviewResponse(BaseModel):
    claim_id: str
    action: ReviewAction
    note: Optional[str] = None
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    qdrant_connected: bool
