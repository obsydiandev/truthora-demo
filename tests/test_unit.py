"""Unit tests for core logic and API integration."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.analyze import _compute_verdict, _detect_headline_language
from api.schemas import (
    CheckworthinessScore,
    Claim,
    ClaimResult,
    FactCheckMatch,
    FreshnessBadge,
    StanceLabel,
)
from core.normalizer import normalize_claims

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claim(claim_id: str = "c1", text: str = "test", lang: str = "en") -> Claim:
    return Claim(
        claim_id=claim_id,
        claim_text=text,
        source_quote=text,
        char_start=0,
        char_end=len(text),
        language=lang,
        checkworthiness=CheckworthinessScore(
            harm_potential=0.5, virality_potential=0.5,
            verifiability=0.8, specificity=0.7, public_interest=0.5,
            composite=0.55,
        ),
    )


def _make_match(
    stance: StanceLabel = StanceLabel.SUPPORTED,
    score: float = 0.7,
    url: str = "https://example.com/1",
    badge: FreshnessBadge = FreshnessBadge.FRESH,
) -> FactCheckMatch:
    return FactCheckMatch(
        matched_url=url,
        source_name="Test Source",
        claim_reviewed="test claim",
        stance=stance,
        similarity_score=score,
        reranker_score=score,
        nli_confidence=score,
        freshness_decay=0.9,
        freshness_badge=badge,
        final_score=score,
    )


def _make_result(
    matches: list[FactCheckMatch],
    uncertainty: float = 0.5,
) -> ClaimResult:
    return ClaimResult(
        claim=_make_claim(),
        matches=matches,
        uncertainty=uncertainty,
        uncertainty_level="MODERATE",
    )


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

class TestDetectHeadlineLanguage:
    def test_english(self):
        assert _detect_headline_language("COVID vaccine causes infertility") == "en"

    def test_polish(self):
        assert _detect_headline_language("Szczepionka powoduje bezpłodność") == "pl"
        assert _detect_headline_language("Sieć 5G nie jest zagrożeniem") == "pl"

    def test_ukrainian(self):
        assert _detect_headline_language("Вакцина COVID викликає безпліддя") == "ua"
        assert _detect_headline_language("Україна підписала угоду з ЄС") == "ua"

    def test_cyrillic_beats_polish(self):
        # If both Cyrillic and Polish chars present, Cyrillic wins (checked first)
        assert _detect_headline_language("Не ąść") == "ua"

    def test_empty_string(self):
        assert _detect_headline_language("") == "en"

    def test_numbers_only(self):
        assert _detect_headline_language("12345 67890") == "en"


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

class TestComputeVerdict:
    def test_no_results(self):
        verdict, confidence, explanation, details = _compute_verdict([])
        assert verdict == "NO_DATA"
        assert confidence == 0.0
        assert details["total"] == 0

    def test_no_matches(self):
        result = _make_result(matches=[], uncertainty=1.0)
        verdict, confidence, explanation, details = _compute_verdict([result])
        assert verdict == "NO_DATA"

    def test_clear_refuted(self):
        """4 out of 5 refuted → LIKELY_FALSE (80% > 60% threshold)."""
        matches = [
            _make_match(StanceLabel.REFUTED, url=f"https://ex.com/{i}")
            for i in range(4)
        ] + [_make_match(StanceLabel.SUPPORTED, url="https://ex.com/5")]
        result = _make_result(matches, uncertainty=0.3)
        verdict, confidence, explanation, details = _compute_verdict([result])
        assert verdict == "LIKELY_FALSE"
        assert details["refuted"] == 4
        assert details["supported"] == 1

    def test_clear_supported(self):
        """4 out of 5 supported → VERIFIED (80% > 60% threshold)."""
        matches = [
            _make_match(StanceLabel.SUPPORTED, url=f"https://ex.com/{i}")
            for i in range(4)
        ] + [_make_match(StanceLabel.NEI, url="https://ex.com/5")]
        result = _make_result(matches, uncertainty=0.3)
        verdict, confidence, _, _ = _compute_verdict([result])
        assert verdict == "VERIFIED"

    def test_conflicting_becomes_inconclusive(self):
        """2 REFUTED, 1 SUPPORTED, 2 NEI → INCONCLUSIVE (no stance > 60%)."""
        matches = [
            _make_match(StanceLabel.REFUTED, url="https://ex.com/1"),
            _make_match(StanceLabel.REFUTED, url="https://ex.com/2"),
            _make_match(StanceLabel.SUPPORTED, url="https://ex.com/3"),
            _make_match(StanceLabel.NEI, url="https://ex.com/4"),
            _make_match(StanceLabel.NEI, url="https://ex.com/5"),
        ]
        result = _make_result(matches, uncertainty=0.9)
        verdict, _, _, details = _compute_verdict([result])
        assert verdict == "INCONCLUSIVE"
        assert details["conflicting"] is True

    def test_high_uncertainty_low_confidence(self):
        """High uncertainty + low confidence → INCONCLUSIVE."""
        matches = [_make_match(StanceLabel.NEI, score=0.2, url="https://ex.com/1")]
        result = _make_result(matches, uncertainty=0.9)
        verdict, confidence, _, _ = _compute_verdict([result])
        assert verdict == "INCONCLUSIVE"

    def test_unverified_moderate_uncertainty(self):
        """No clear stance, moderate uncertainty → UNVERIFIED."""
        matches = [
            _make_match(StanceLabel.NEI, score=0.6, url="https://ex.com/1"),
            _make_match(StanceLabel.SUPPORTED, score=0.6, url="https://ex.com/2"),
        ]
        result = _make_result(matches, uncertainty=0.4)
        verdict, _, _, _ = _compute_verdict([result])
        assert verdict == "UNVERIFIED"

    def test_details_structure(self):
        matches = [
            _make_match(StanceLabel.REFUTED, score=0.8, url="https://ex.com/1",
                        badge=FreshnessBadge.OUTDATED),
            _make_match(StanceLabel.SUPPORTED, score=0.6, url="https://ex.com/2"),
        ]
        result = _make_result(matches, uncertainty=0.5)
        _, _, _, details = _compute_verdict([result])

        assert details["total"] == 2
        assert details["refuted"] == 1
        assert details["supported"] == 1
        assert details["outdated"] == 1
        assert details["quality"] in ("high", "moderate", "low")
        assert isinstance(details["avg_score"], float)
        assert isinstance(details["conflicting"], bool)

    def test_explanation_mentions_dominant_stance(self):
        matches = [
            _make_match(StanceLabel.REFUTED, url=f"https://ex.com/{i}")
            for i in range(4)
        ]
        result = _make_result(matches, uncertainty=0.2)
        _, _, explanation, _ = _compute_verdict([result])
        assert "refute" in explanation.lower()

    def test_explanation_outdated_warning(self):
        matches = [
            _make_match(StanceLabel.SUPPORTED, url="https://ex.com/1",
                        badge=FreshnessBadge.OUTDATED),
        ]
        result = _make_result(matches, uncertainty=0.3)
        _, _, explanation, _ = _compute_verdict([result])
        assert "outdated" in explanation.lower()

    def test_confidence_range(self):
        """Confidence must always be in [0, 1]."""
        for uncertainty in [0.0, 0.5, 1.0]:
            for score in [0.1, 0.5, 0.9]:
                matches = [_make_match(StanceLabel.SUPPORTED, score=score,
                                       url="https://ex.com/1")]
                result = _make_result(matches, uncertainty=uncertainty)
                _, confidence, _, _ = _compute_verdict([result])
                assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

class TestNormalizeClaims:
    def test_normalizes_text_and_detects_negation(self):
        claim = _make_claim(text="PKB  nie   wzrośnie", lang="pl")
        result = normalize_claims([claim])
        assert result[0].claim_text == "PKB nie wzrośnie"
        assert result[0].has_negation is True

    def test_no_negation(self):
        claim = _make_claim(text="PKB wzrośnie o 4%", lang="pl")
        result = normalize_claims([claim])
        assert result[0].has_negation is False

    def test_ukrainian_negation(self):
        claim = _make_claim(text="Це не правда", lang="ua")
        result = normalize_claims([claim])
        assert result[0].has_negation is True


# ---------------------------------------------------------------------------
# API integration (no external services needed)
# ---------------------------------------------------------------------------

class TestHealthAPI:
    def test_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert data["version"] == "0.1.0"

    def test_response_schema(self):
        resp = client.get("/health")
        data = resp.json()
        assert "qdrant_connected" in data
        assert isinstance(data["qdrant_connected"], bool)


class TestAnalyzeAPI:
    def test_empty_body_fails(self):
        resp = client.post("/analyze", json={})
        assert resp.status_code == 422

    def test_headline_returns_200(self):
        resp = client.post("/analyze", json={"headline": "Test claim for analysis"})
        # May fail if Qdrant/models not running, but should not 500
        assert resp.status_code in (200, 422, 503)

    def test_headline_response_has_verdict(self):
        resp = client.post("/analyze", json={"headline": "COVID vaccine is safe"})
        if resp.status_code == 200:
            data = resp.json()
            assert "verdict" in data
            assert "confidence" in data
            assert "claims" in data
            assert "processing_time_ms" in data
            assert data["verdict"] in (
                "VERIFIED", "UNVERIFIED", "LIKELY_FALSE", "INCONCLUSIVE", "NO_DATA",
            )
            assert "verdict_details" in data

    def test_polish_headline_detects_language(self):
        resp = client.post("/analyze", json={
            "headline": "Szczepionka na COVID powoduje bezpłodność"
        })
        if resp.status_code == 200:
            data = resp.json()
            assert data["language"] == "pl"

    def test_ukrainian_headline_detects_language(self):
        resp = client.post("/analyze", json={
            "headline": "Вакцина COVID викликає безпліддя"
        })
        if resp.status_code == 200:
            data = resp.json()
            assert data["language"] == "ua"


class TestClaimsAPI:
    def test_list_returns_200(self):
        resp = client.get("/claims")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestAnalyzeResponseSchema:
    def test_verdict_details_optional(self):
        """verdict_details can be None."""
        from api.schemas import AnalyzeResponse
        resp = AnalyzeResponse(
            url="https://example.com",
            processing_time_ms=100.0,
        )
        assert resp.verdict_details is None

    def test_verdict_details_dict(self):
        from api.schemas import AnalyzeResponse
        details = {"supported": 2, "refuted": 1, "nei": 0, "total": 3}
        resp = AnalyzeResponse(
            url="https://example.com",
            processing_time_ms=100.0,
            verdict_details=details,
        )
        assert resp.verdict_details["total"] == 3

    def test_all_verdict_values_accepted(self):
        from api.schemas import AnalyzeResponse
        for v in ("VERIFIED", "UNVERIFIED", "LIKELY_FALSE", "INCONCLUSIVE", "NO_DATA"):
            resp = AnalyzeResponse(
                url="https://example.com",
                processing_time_ms=50.0,
                verdict=v,
            )
            assert resp.verdict == v
