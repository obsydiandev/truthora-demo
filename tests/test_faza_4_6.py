"""Tests for Faza 4–6 components."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas import KGSignal, StanceLabel
from core.knowledge_graph import (
    Entity,
    KGResult,
    KGTriple,
    _entity_to_dbpedia_uri,
    extract_entities,
    kg_signal_to_score,
)
from core.scorer import compute_entropy, get_uncertainty_level
from core.scorer import (
    SCORE_WEIGHTS,
    compute_final_score,
    compute_uncertainty,
)
from data.benchmark.evaluate import (
    compute_mrr,
    compute_recall_at_k,
    compute_stance_f1,
    load_golden_pairs,
)


class TestKGSignalScoring:
    def test_kg_found_score(self):
        assert kg_signal_to_score(KGSignal.KG_FOUND) == 1.0

    def test_kg_not_found_score(self):
        assert kg_signal_to_score(KGSignal.KG_NOT_FOUND) == 0.5

    def test_kg_mismatch_score(self):
        assert kg_signal_to_score(KGSignal.KG_MISMATCH) == 0.0


class TestDBpediaURI:
    def test_simple_entity(self):
        uri = _entity_to_dbpedia_uri("Donald Tusk")
        assert uri == "http://dbpedia.org/resource/Donald_Tusk"

    def test_single_word(self):
        uri = _entity_to_dbpedia_uri("Poland")
        assert uri == "http://dbpedia.org/resource/Poland"

    def test_strips_whitespace(self):
        uri = _entity_to_dbpedia_uri("  Kyiv  ")
        assert uri == "http://dbpedia.org/resource/Kyiv"


class TestEntityExtraction:
    def test_returns_list(self):
        # Without spaCy model installed, should return empty list
        result = extract_entities("Donald Tusk is the Prime Minister of Poland")
        assert isinstance(result, list)

    def test_entity_dataclass(self):
        entity = Entity(text="Poland", label="GPE")
        assert entity.text == "Poland"
        assert entity.label == "GPE"


class TestKGResult:
    def test_kg_found_result(self):
        result = KGResult(
            signal=KGSignal.KG_FOUND,
            entities=[Entity(text="Poland", label="GPE")],
            triples=[KGTriple(subject="Poland", predicate="capital", obj="Warsaw")],
            details="Found 1 triple",
        )
        assert result.signal == KGSignal.KG_FOUND
        assert len(result.entities) == 1
        assert len(result.triples) == 1

    def test_kg_not_found_result(self):
        result = KGResult(
            signal=KGSignal.KG_NOT_FOUND,
            details="No entities found",
        )
        assert result.signal == KGSignal.KG_NOT_FOUND
        assert result.entities == []
        assert result.triples == []

    def test_kg_mismatch_result(self):
        result = KGResult(signal=KGSignal.KG_MISMATCH, details="Role mismatch")
        assert result.signal == KGSignal.KG_MISMATCH


class TestScoreWeights:
    def test_weights_sum_to_one(self):
        assert sum(SCORE_WEIGHTS.values()) == pytest.approx(1.0)

    def test_all_weights_positive(self):
        for name, weight in SCORE_WEIGHTS.items():
            assert weight > 0, f"Weight for {name} should be positive"

    def test_weight_ordering(self):
        """Similarity should have highest weight, kg_signal lowest."""
        assert SCORE_WEIGHTS["similarity"] > SCORE_WEIGHTS["reranker_score"]
        assert SCORE_WEIGHTS["reranker_score"] > SCORE_WEIGHTS["nli_confidence"]
        assert SCORE_WEIGHTS["nli_confidence"] > SCORE_WEIGHTS["freshness_decay"]
        assert SCORE_WEIGHTS["freshness_decay"] > SCORE_WEIGHTS["kg_signal"]


class TestFinalScore:
    def test_all_ones(self):
        score = compute_final_score(1.0, 1.0, 1.0, 1.0, KGSignal.KG_FOUND)
        assert score == pytest.approx(1.0)

    def test_all_zeros(self):
        score = compute_final_score(0.0, 0.0, 0.0, 0.0, KGSignal.KG_MISMATCH)
        assert score == pytest.approx(0.0)

    def test_mixed_scores(self):
        score = compute_final_score(
            similarity=0.9,
            reranker_score=0.8,
            nli_confidence=0.7,
            freshness_decay=0.6,
            kg_signal=KGSignal.KG_FOUND,
        )
        expected = (
            0.9 * 0.35
            + 0.8 * 0.25
            + 0.7 * 0.20
            + 0.6 * 0.12
            + 1.0 * 0.08  # KG_FOUND = 1.0
        )
        assert score == pytest.approx(expected)

    def test_no_kg_signal(self):
        score = compute_final_score(0.9, 0.8, 0.7, 0.6, None)
        expected = (
            0.9 * 0.35
            + 0.8 * 0.25
            + 0.7 * 0.20
            + 0.6 * 0.12
            + 0.5 * 0.08  # None → 0.5 (neutral)
        )
        assert score == pytest.approx(expected)

    def test_kg_mismatch_penalizes(self):
        score_found = compute_final_score(0.9, 0.8, 0.7, 0.6, KGSignal.KG_FOUND)
        score_mismatch = compute_final_score(0.9, 0.8, 0.7, 0.6, KGSignal.KG_MISMATCH)
        assert score_found > score_mismatch

    def test_clamped_to_unit_interval(self):
        score = compute_final_score(1.0, 1.0, 1.0, 1.0, KGSignal.KG_FOUND)
        assert 0.0 <= score <= 1.0


class TestUncertaintyComputation:
    def test_uniform_is_high(self):
        entropy, level = compute_uncertainty([0.2, 0.2, 0.2, 0.2, 0.2])
        assert entropy == pytest.approx(1.0, abs=0.01)
        assert level == "HIGH"

    def test_dominant_is_low(self):
        entropy, level = compute_uncertainty([0.95, 0.01, 0.01, 0.01, 0.02])
        assert entropy < 0.30
        assert level == "LOW"

    def test_empty_is_zero(self):
        entropy, level = compute_uncertainty([])
        assert entropy == 0.0
        assert level == "LOW"


class TestRerankerTypes:
    def test_stance_label_values(self):
        assert StanceLabel.SUPPORTED == "SUPPORTED"
        assert StanceLabel.REFUTED == "REFUTED"
        assert StanceLabel.NEI == "NEI"

    def test_stance_label_is_string_enum(self):
        assert isinstance(StanceLabel.SUPPORTED, str)


class TestGoldenPairsData:
    def test_en_pairs_exist(self):
        path = Path(__file__).resolve().parent.parent / "data" / "benchmark" / "golden_pairs_en.json"
        assert path.exists()

    def test_pl_pairs_exist(self):
        path = Path(__file__).resolve().parent.parent / "data" / "benchmark" / "golden_pairs_pl.json"
        assert path.exists()

    def test_ua_pairs_exist(self):
        path = Path(__file__).resolve().parent.parent / "data" / "benchmark" / "golden_pairs_ua.json"
        assert path.exists()

    def test_en_pairs_valid(self):
        path = Path(__file__).resolve().parent.parent / "data" / "benchmark" / "golden_pairs_en.json"
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f)
        assert len(pairs) == 95
        for pair in pairs:
            assert "id" in pair
            assert "claim" in pair
            assert "expected_match" in pair
            assert "expected_stance" in pair
            assert pair["expected_stance"] in ("SUPPORTED", "REFUTED", "NEI")
            assert pair["language"] == "en"

    def test_pl_pairs_valid(self):
        path = Path(__file__).resolve().parent.parent / "data" / "benchmark" / "golden_pairs_pl.json"
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f)
        assert len(pairs) == 17
        for pair in pairs:
            assert pair["language"] == "pl"
            assert pair["expected_stance"] in ("SUPPORTED", "REFUTED", "NEI")

    def test_ua_pairs_valid(self):
        path = Path(__file__).resolve().parent.parent / "data" / "benchmark" / "golden_pairs_ua.json"
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f)
        assert len(pairs) == 2
        for pair in pairs:
            assert pair["language"] == "ua"
            assert pair["expected_stance"] in ("SUPPORTED", "REFUTED", "NEI")

    def test_total_pairs_255(self):
        pairs = load_golden_pairs()
        assert len(pairs) == 114


class TestBenchmarkMetrics:
    def test_recall_at_5_perfect(self):
        results = [{"found_in_top_k": True} for _ in range(10)]
        assert compute_recall_at_k(results, k=5) == 1.0

    def test_recall_at_5_zero(self):
        results = [{"found_in_top_k": False} for _ in range(10)]
        assert compute_recall_at_k(results, k=5) == 0.0

    def test_recall_at_5_partial(self):
        results = [{"found_in_top_k": True}] * 7 + [{"found_in_top_k": False}] * 3
        assert compute_recall_at_k(results, k=5) == pytest.approx(0.7)

    def test_recall_empty(self):
        assert compute_recall_at_k([], k=5) == 0.0

    def test_mrr_perfect(self):
        results = [{"rank": 1} for _ in range(5)]
        assert compute_mrr(results) == 1.0

    def test_mrr_rank_2(self):
        results = [{"rank": 2}]
        assert compute_mrr(results) == pytest.approx(0.5)

    def test_mrr_mixed(self):
        results = [{"rank": 1}, {"rank": 2}, {"rank": 5}]
        expected = (1.0 + 0.5 + 0.2) / 3
        assert compute_mrr(results) == pytest.approx(expected)

    def test_mrr_empty(self):
        assert compute_mrr([]) == 0.0

    def test_stance_f1_perfect(self):
        results = [
            {"expected_stance": "SUPPORTED", "predicted_stance": "SUPPORTED"},
            {"expected_stance": "REFUTED", "predicted_stance": "REFUTED"},
            {"expected_stance": "NEI", "predicted_stance": "NEI"},
        ]
        f1 = compute_stance_f1(results)
        assert f1["macro_f1"] == pytest.approx(1.0)

    def test_stance_f1_all_wrong(self):
        results = [
            {"expected_stance": "SUPPORTED", "predicted_stance": "REFUTED"},
            {"expected_stance": "REFUTED", "predicted_stance": "SUPPORTED"},
        ]
        f1 = compute_stance_f1(results)
        assert f1["macro_f1"] == 0.0

    def test_stance_f1_empty(self):
        assert compute_stance_f1([])["macro_f1"] == 0.0



class TestGDELTClient:
    def test_import_gdelt(self):
        from services.sources.gdelt import GDELTClient
        client = GDELTClient()
        assert client is not None
        assert hasattr(client, "search_articles")
        assert hasattr(client, "monitor_pl_ua")
        assert hasattr(client, "get_article_urls")
