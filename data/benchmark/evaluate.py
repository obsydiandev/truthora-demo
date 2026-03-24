"""Truthora — Benchmark evaluation script.

Evaluates the Truthora pipeline against Golden Pairs datasets
(EN: 100 pairs, PL: 100 pairs, UA: 55 pairs = 255 total).

Metrics:
  - Recall@5: Is the expected match in top-5 results? (target ≥ 0.74)
  - MRR: Mean Reciprocal Rank of expected match (target ≥ 0.60)
  - Stance F1: F1 score for stance classification (target ≥ 0.70)

Usage:
    python data/benchmark/evaluate.py [--verbose]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BENCHMARK_DIR = Path(__file__).resolve().parent
GOLDEN_PAIRS_FILES = [
    ("EN", BENCHMARK_DIR / "golden_pairs_en.json"),
    ("PL", BENCHMARK_DIR / "golden_pairs_pl.json"),
    ("UA", BENCHMARK_DIR / "golden_pairs_ua.json"),
]

# Target metrics
TARGET_RECALL_AT_5 = 0.74
TARGET_MRR = 0.60
TARGET_STANCE_F1 = 0.70


def load_golden_pairs() -> list[dict[str, Any]]:
    """Load all golden pairs from JSON files."""
    all_pairs: list[dict[str, Any]] = []
    for lang, filepath in GOLDEN_PAIRS_FILES:
        if not filepath.exists():
            print(f"⚠️  Warning: {filepath} not found, skipping {lang}")
            continue
        with open(filepath, encoding="utf-8") as f:
            pairs = json.load(f)
            for pair in pairs:
                pair["_lang_group"] = lang
            all_pairs.extend(pairs)
    return all_pairs


def compute_recall_at_k(results: list[dict[str, Any]], k: int = 5) -> float:
    """Compute Recall@K — fraction of pairs where expected match is in top-K."""
    if not results:
        return 0.0

    hits = sum(1 for r in results if r.get("found_in_top_k", False))
    return hits / len(results)


def compute_mrr(results: list[dict[str, Any]]) -> float:
    """Compute Mean Reciprocal Rank."""
    if not results:
        return 0.0

    rr_sum = 0.0
    for r in results:
        rank = r.get("rank", 0)
        if rank > 0:
            rr_sum += 1.0 / rank

    return rr_sum / len(results)


def compute_stance_f1(results: list[dict[str, Any]]) -> dict[str, float]:
    """Compute per-class and macro F1 for stance classification."""
    if not results:
        return {"macro_f1": 0.0}

    labels = ["SUPPORTED", "REFUTED", "NEI"]
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()

    for r in results:
        expected = r.get("expected_stance", "NEI")
        predicted = r.get("predicted_stance", "NEI")

        if predicted == expected:
            tp[expected] += 1
        else:
            fp[predicted] += 1
            fn[expected] += 1

    f1_scores: dict[str, float] = {}
    for label in labels:
        precision = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) > 0 else 0.0
        recall = tp[label] / (tp[label] + fn[label]) if (tp[label] + fn[label]) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f1_scores[label] = f1

    f1_scores["macro_f1"] = sum(f1_scores[l] for l in labels) / len(labels)
    return f1_scores


def evaluate_golden_pairs(
    pairs: list[dict[str, Any]],
    verbose: bool = False,
) -> dict[str, Any]:
    """Evaluate pipeline against golden pairs.

    This is a framework function — actual pipeline integration
    requires the embedding + matching services to be running.
    When run standalone, it reports dataset statistics and
    validates the benchmark format.
    """
    results_summary: dict[str, Any] = {
        "total_pairs": len(pairs),
        "by_language": {},
        "format_valid": True,
    }

    # Validate format
    required_keys = {"id", "claim", "expected_match", "expected_stance", "language"}
    for pair in pairs:
        if not required_keys.issubset(pair.keys()):
            missing = required_keys - set(pair.keys())
            results_summary["format_valid"] = False
            if verbose:
                print(f"❌ Missing keys in {pair.get('id', '?')}: {missing}")

    # Count by language
    lang_counts: Counter[str] = Counter()
    stance_counts: Counter[str] = Counter()
    for pair in pairs:
        lang_counts[pair.get("_lang_group", "?")] += 1
        stance_counts[pair.get("expected_stance", "?")] += 1

    results_summary["by_language"] = dict(lang_counts)
    results_summary["stance_distribution"] = dict(stance_counts)

    # Target metrics (to be filled when pipeline is integrated)
    results_summary["targets"] = {
        "recall_at_5": TARGET_RECALL_AT_5,
        "mrr": TARGET_MRR,
        "stance_f1": TARGET_STANCE_F1,
    }

    return results_summary


def main():
    parser = argparse.ArgumentParser(description="Truthora Benchmark Evaluation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("=" * 60)
    print("  Truthora — Golden Pairs Benchmark Evaluation")
    print("=" * 60)
    print()

    # Load pairs
    pairs = load_golden_pairs()
    print(f"📊 Loaded {len(pairs)} golden pairs")
    print()

    # Evaluate
    summary = evaluate_golden_pairs(pairs, verbose=args.verbose)

    # Report
    print("📋 Dataset Summary:")
    print(f"   Total pairs: {summary['total_pairs']}")
    print(f"   Format valid: {'✅' if summary['format_valid'] else '❌'}")
    print()

    print("🌐 By Language:")
    for lang, count in sorted(summary["by_language"].items()):
        print(f"   {lang}: {count} pairs")
    print()

    print("🏷️  Stance Distribution:")
    for stance, count in sorted(summary["stance_distribution"].items()):
        print(f"   {stance}: {count}")
    print()

    print("🎯 Target Metrics:")
    targets = summary["targets"]
    print(f"   Recall@5 ≥ {targets['recall_at_5']}")
    print(f"   MRR ≥ {targets['mrr']}")
    print(f"   Stance F1 ≥ {targets['stance_f1']}")
    print()

    if not summary["format_valid"]:
        print("❌ Some golden pairs have invalid format!")
        return 1

    print("✅ All golden pairs validated successfully")
    print()
    print("ℹ️  Full evaluation requires running pipeline:")
    print("   1. Start services: docker-compose up")
    print("   2. Index seed data")
    print("   3. Run: python data/benchmark/evaluate.py --run-pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
