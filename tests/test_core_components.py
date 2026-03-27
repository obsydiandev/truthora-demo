"""Unit tests for core components: normalizer, scorer, freshness, schemas, API endpoints."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import (
    CheckworthinessScore,
    Claim,
    ClaimResult,
    FactCheckMatch,
    FreshnessBadge,
    HealthResponse,
    StanceLabel,
)
from core.detector import CW_WEIGHTS, _compute_composite
from core.matcher import (
    compute_freshness_decay,
    get_freshness_badge,
)
from core.normalizer import has_negation, normalize_text
from core.scorer import compute_entropy, get_uncertainty_level


class TestNormalizeText:
    def test_unicode_nfc(self):
        # Combining characters should be normalized
        text = "cafe\u0301"  # café with combining accent
        result = normalize_text(text)
        assert result == "caf\u00e9"  # NFC: single character é

    def test_collapses_whitespace(self):
        result = normalize_text("  hello   world  \n  foo  ")
        assert result == "hello world foo"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_preserves_polish_chars(self):
        text = "żółć ąęśćńźżó"
        result = normalize_text(text)
        assert "żółć" in result


class TestNegationDetection:
    def test_english_negation(self):
        assert has_negation("The GDP did not grow", "en") is True
        assert has_negation("There is no evidence", "en") is True

    def test_english_no_negation(self):
        assert has_negation("The GDP grew by 4%", "en") is False

    def test_polish_negation(self):
        assert has_negation("PKB nie wzrośnie o 4%", "pl") is True
        assert has_negation("Brak dowodów na wzrost", "pl") is True
        assert has_negation("Żaden ekspert tego nie potwierdził", "pl") is True

    def test_polish_no_negation(self):
        assert has_negation("PKB wzrośnie o 4%", "pl") is False

    def test_ukrainian_negation(self):
        assert has_negation("ВВП не зросте на 4%", "ua") is True
        assert has_negation("Ні один експерт не підтвердив", "ua") is True

    def test_ukrainian_no_negation(self):
        assert has_negation("ВВП зросте на 4%", "ua") is False

    def test_fallback_all_languages(self):
        # Unknown language should check all
        assert has_negation("nie dotyczy", "xx") is True


class TestCheckworthiness:
    def test_composite_score_computation(self):
        scores = {
            "harm_potential": 1.0,
            "virality_potential": 1.0,
            "verifiability": 1.0,
            "specificity": 1.0,
            "public_interest": 1.0,
        }
        composite = _compute_composite(scores)
        assert composite == pytest.approx(1.0)

    def test_composite_score_zero(self):
        scores = {
            "harm_potential": 0.0,
            "virality_potential": 0.0,
            "verifiability": 0.0,
            "specificity": 0.0,
            "public_interest": 0.0,
        }
        composite = _compute_composite(scores)
        assert composite == pytest.approx(0.0)

    def test_composite_score_weighted(self):
        scores = {
            "harm_potential": 0.8,
            "virality_potential": 0.6,
            "verifiability": 0.9,
            "specificity": 0.5,
            "public_interest": 0.3,
        }
        expected = (0.8 * 0.35 + 0.6 * 0.25 + 0.9 * 0.20 + 0.5 * 0.12 + 0.3 * 0.08)
        composite = _compute_composite(scores)
        assert composite == pytest.approx(expected)

    def test_weights_sum_to_one(self):
        assert sum(CW_WEIGHTS.values()) == pytest.approx(1.0)


class TestFreshnessDecay:
    def test_very_recent(self):
        now = datetime.now(timezone.utc).isoformat()
        decay = compute_freshness_decay(now)
        assert decay > 0.95  # Very close to 1.0

    def test_180_days_half(self):
        past = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
        decay = compute_freshness_decay(past)
        assert decay == pytest.approx(0.5, abs=0.05)

    def test_360_days_quarter(self):
        past = (datetime.now(timezone.utc) - timedelta(days=360)).isoformat()
        decay = compute_freshness_decay(past)
        assert decay == pytest.approx(0.25, abs=0.05)

    def test_none_returns_default(self):
        decay = compute_freshness_decay(None)
        assert decay == 0.5

    def test_invalid_string(self):
        decay = compute_freshness_decay("not-a-date")
        assert decay == 0.5


class TestFreshnessBadge:
    def test_fresh(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        assert get_freshness_badge(recent) == FreshnessBadge.FRESH

    def test_aging(self):
        months_ago = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        assert get_freshness_badge(months_ago) == FreshnessBadge.AGING

    def test_outdated(self):
        old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        assert get_freshness_badge(old) == FreshnessBadge.OUTDATED

    def test_none(self):
        assert get_freshness_badge(None) == FreshnessBadge.AGING


class TestEntropy:
    def test_single_dominant(self):
        # One strong match = low entropy
        scores = [0.95, 0.1, 0.05, 0.02, 0.01]
        entropy = compute_entropy(scores)
        assert entropy < 0.70  # Should be low to moderate

    def test_uniform_distribution(self):
        # All equal = maximum entropy
        scores = [0.2, 0.2, 0.2, 0.2, 0.2]
        entropy = compute_entropy(scores)
        assert entropy == pytest.approx(1.0, abs=0.01)

    def test_empty_scores(self):
        assert compute_entropy([]) == 0.0

    def test_single_score(self):
        assert compute_entropy([0.9]) == 0.0

    def test_two_scores(self):
        entropy = compute_entropy([0.9, 0.1])
        assert 0.0 < entropy < 1.0

    def test_zero_scores(self):
        assert compute_entropy([0.0, 0.0, 0.0]) == 1.0


class TestUncertaintyLevel:
    def test_low(self):
        assert get_uncertainty_level(0.1) == "LOW"
        assert get_uncertainty_level(0.29) == "LOW"

    def test_moderate(self):
        assert get_uncertainty_level(0.30) == "MODERATE"
        assert get_uncertainty_level(0.50) == "MODERATE"
        assert get_uncertainty_level(0.70) == "MODERATE"

    def test_high(self):
        assert get_uncertainty_level(0.71) == "HIGH"
        assert get_uncertainty_level(1.0) == "HIGH"


class TestSchemas:
    def test_claim_schema(self):
        claim = Claim(
            claim_id="test123",
            claim_text="GDP grew by 4%",
            source_quote="...GDP grew by 4%...",
            char_start=10,
            char_end=25,
            language="en",
            checkworthiness=CheckworthinessScore(
                harm_potential=0.5,
                virality_potential=0.3,
                verifiability=0.8,
                specificity=0.6,
                public_interest=0.4,
                composite=0.52,
            ),
        )
        assert claim.claim_id == "test123"
        assert claim.has_negation is False

    def test_fact_check_match_schema(self):
        match = FactCheckMatch(
            matched_url="https://example.com/fc",
            source_name="Full Fact",
            claim_reviewed="GDP grew by 4%",
            stance=StanceLabel.SUPPORTED,
            similarity_score=0.91,
            freshness_decay=0.85,
            freshness_badge=FreshnessBadge.FRESH,
            final_score=0.77,
        )
        assert match.stance == StanceLabel.SUPPORTED

    def test_claim_result_schema(self):
        claim = Claim(
            claim_id="abc",
            claim_text="test",
            source_quote="test",
            char_start=0,
            char_end=4,
            language="en",
            checkworthiness=CheckworthinessScore(
                harm_potential=0.0,
                virality_potential=0.0,
                verifiability=0.0,
                specificity=0.0,
                public_interest=0.0,
                composite=0.0,
            ),
        )
        result = ClaimResult(
            claim=claim,
            matches=[],
            uncertainty=0.5,
            uncertainty_level="MODERATE",
        )
        assert result.uncertainty == 0.5


class TestRSSConfig:
    def test_rss_feeds_json_valid(self):
        feeds_path = Path(__file__).resolve().parent.parent / "data" / "rss_feeds.json"
        with open(feeds_path, encoding="utf-8") as f:
            feeds = json.load(f)
        assert isinstance(feeds, list)
        assert len(feeds) >= 8

        for feed in feeds:
            assert "name" in feed
            assert "url" in feed
            assert "country" in feed
            assert "language" in feed
            assert feed["url"].startswith("http")

    def test_seed_fact_checks_valid(self):
        seeds_path = Path(__file__).resolve().parent.parent / "data" / "seeds" / "initial_fact_checks.json"
        with open(seeds_path, encoding="utf-8") as f:
            seeds = json.load(f)
        assert isinstance(seeds, list)

        for seed in seeds:
            assert "claim_text" in seed
            assert "source_url" in seed
            assert "source_name" in seed


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "0.1.0"
        # Qdrant may or may not be running in test env
        assert "qdrant_connected" in data


class TestAnalyzeEndpoint:
    def test_analyze_requires_url(self):
        response = client.post("/analyze", json={})
        assert response.status_code == 422  # Validation error

    def test_analyze_invalid_url(self):
        response = client.post("/analyze", json={"url": "not-a-url"})
        assert response.status_code == 422


class TestClaimsEndpoint:
    def test_list_claims_returns_200(self):
        response = client.get("/claims")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
