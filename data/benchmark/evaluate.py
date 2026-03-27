"""Benchmark evaluation script."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from api.schemas import Claim, CheckworthinessScore
    from core.matcher import ClaimMatcher
    HAS_DIRECT = True
except ImportError:
    HAS_DIRECT = False

BENCHMARK_DIR = Path(__file__).resolve().parent
GOLDEN_PAIRS_FILES = [
    ("EN", BENCHMARK_DIR / "golden_pairs_en_v0_sanity.json"),
    ("PL", BENCHMARK_DIR / "golden_pairs_pl_v0_sanity.json"),
    ("UA", BENCHMARK_DIR / "golden_pairs_ua_v0_sanity.json"),
]
GOLDEN_PAIRS_HELDOUT = BENCHMARK_DIR / "golden_pairs_heldout.json"

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


def load_heldout_pairs() -> list[dict[str, Any]]:
    """Load held-out golden pairs (LLM-generated from review_title, no claim_text leakage)."""
    if not GOLDEN_PAIRS_HELDOUT.exists():
        print(f"❌ Heldout file not found: {GOLDEN_PAIRS_HELDOUT}")
        sys.exit(1)
    with open(GOLDEN_PAIRS_HELDOUT, encoding="utf-8") as f:
        pairs = json.load(f)
    # Assign _lang_group from language field (normalise ua/uk → UA)
    for pair in pairs:
        lang = pair.get("language", "en").upper()
        if lang == "UK":
            lang = "UA"
        pair["_lang_group"] = lang
    return pairs


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


def _url_match(expected_url: str, match_url: str) -> bool:
    """Exact URL match, normalized (strip trailing slash, case-insensitive)."""
    if not expected_url or not match_url:
        return False
    return expected_url.rstrip("/").lower() == match_url.rstrip("/").lower()


def _token_overlap(a: str, b: str) -> float:
    """Jaccard token overlap between two strings (case-insensitive)."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _score_matches(
    top_k_matches: list[dict[str, Any]],
    expected_match: str,
    expected_url: str,
    k: int,
) -> tuple[bool, int, str]:
    """Check if expected match is in top-K and return (found, rank, predicted_stance)."""
    found_in_top_k = False
    rank = 0
    for i, match in enumerate(top_k_matches[:k], start=1):
        if expected_url and _url_match(expected_url, match.get("matched_url", "")):
            found_in_top_k = True
            rank = i
            break
        overlap = _token_overlap(expected_match, match.get("claim_reviewed", ""))
        if overlap >= 0.50:
            found_in_top_k = True
            rank = i
            break

    # Stance from the matched fact-check (not always rank-1)
    if found_in_top_k and rank > 0:
        predicted_stance = top_k_matches[rank - 1].get("stance", "NEI")
    else:
        predicted_stance = top_k_matches[0].get("stance", "NEI") if top_k_matches else "NEI"
    return found_in_top_k, rank, predicted_stance


async def _evaluate_pair(
    client: "httpx.AsyncClient",
    semaphore: "asyncio.Semaphore",
    api_url: str,
    pair: dict[str, Any],
    verbose: bool,
    k: int,
    force_llm: bool = False,
    nli_only: bool = False,
) -> dict[str, Any]:
    """Call /analyze for a single golden pair and score the result."""
    pair_id = pair["id"]
    expected_match = pair["expected_match"]
    expected_stance = pair["expected_stance"]
    expected_url = pair.get("expected_source_url", "")

    async with semaphore:
        try:
            resp = await client.post(
                f"{api_url}/analyze",
                json={
                    "headline": pair["claim"],
                    "force_llm": force_llm,
                    "nli_only": nli_only,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            if verbose:
                print(f"  ❌ {pair_id}: API error — {exc}")
            return {
                "id": pair_id,
                "_lang_group": pair.get("_lang_group", "?"),
                "expected_stance": expected_stance,
                "predicted_stance": "NEI",
                "found_in_top_k": False,
                "rank": 0,
                "error": str(exc),
            }

    # Flatten all matches across all detected claims
    all_matches: list[dict[str, Any]] = []
    for claim_result in data.get("claims", []):
        all_matches.extend(claim_result.get("matches", []))
    all_matches.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    top_k = all_matches[:k]

    found_in_top_k, rank, predicted_stance = _score_matches(
        top_k, expected_match, expected_url, k,
    )

    if verbose:
        hit_mark = "✅" if found_in_top_k else "❌"
        lang = pair.get("_lang_group", "?")
        print(
            f"  {hit_mark} [{lang}] {pair_id}: "
            f"rank={rank if found_in_top_k else '-'}, "
            f"stance exp={expected_stance} pred={predicted_stance}"
        )

    return {
        "id": pair_id,
        "_lang_group": pair.get("_lang_group", "?"),
        "expected_stance": expected_stance,
        "predicted_stance": predicted_stance,
        "found_in_top_k": found_in_top_k,
        "rank": rank,
    }


async def _run_pipeline_async(
    pairs: list[dict[str, Any]],
    api_url: str,
    verbose: bool,
    k: int,
    concurrency: int,
    delay: float,
    force_llm: bool = False,
    nli_only: bool = False,
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for pair in pairs:
            result = await _evaluate_pair(
                client, semaphore, api_url, pair, verbose, k,
                force_llm=force_llm, nli_only=nli_only,
            )
            results.append(result)
            if delay > 0:
                await asyncio.sleep(delay)
    return results


def run_pipeline_evaluation(
    pairs: list[dict[str, Any]],
    api_url: str = "http://localhost:8000",
    verbose: bool = False,
    k: int = 5,
    concurrency: int = 5,
    delay: float = 2.5,
    force_llm: bool = False,
    nli_only: bool = False,
) -> dict[str, Any]:
    """Run full pipeline evaluation against the live API."""
    if not HAS_HTTPX:
        print("❌ httpx is required for --run-pipeline. Install with: pip install httpx")
        sys.exit(1)

    mode_parts = []
    if force_llm:
        mode_parts.append("force-LLM")
    if nli_only:
        mode_parts.append("NLI-only stance")
    mode_desc = f" ({', '.join(mode_parts)})" if mode_parts else ""
    print(f"🚀 Evaluating {len(pairs)} pairs against {api_url}{mode_desc} (k={k}, delay={delay}s)…")
    t0 = time.perf_counter()

    pair_results = asyncio.run(
        _run_pipeline_async(pairs, api_url, verbose, k, concurrency, delay,
                            force_llm=force_llm, nli_only=nli_only)
    )

    elapsed = time.perf_counter() - t0

    # Per-language split
    by_lang: dict[str, list[dict[str, Any]]] = {}
    for r in pair_results:
        lang = r.get("_lang_group", "?")
        by_lang.setdefault(lang, []).append(r)

    def lang_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "recall_at_k": round(compute_recall_at_k(results, k), 4),
            "mrr": round(compute_mrr(results), 4),
            "stance_f1": {k2: round(v, 4) for k2, v in compute_stance_f1(results).items()},
            "n": len(results),
            "errors": sum(1 for r in results if "error" in r),
        }

    overall = lang_metrics(pair_results)
    per_language = {lang: lang_metrics(res) for lang, res in sorted(by_lang.items())}

    targets = {
        "recall_at_5": TARGET_RECALL_AT_5,
        "mrr": TARGET_MRR,
        "stance_f1": TARGET_STANCE_F1,
    }

    passed = {
        "recall_at_5": overall["recall_at_k"] >= TARGET_RECALL_AT_5,
        "mrr": overall["mrr"] >= TARGET_MRR,
        "stance_f1": overall["stance_f1"].get("macro_f1", 0.0) >= TARGET_STANCE_F1,
    }

    return {
        "meta": {
            "version": "v0.1",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "api_url": api_url,
            "k": k,
            "concurrency": concurrency,
            "elapsed_s": round(elapsed, 2),
            "total_pairs": len(pairs),
            "force_llm": force_llm,
            "nli_only": nli_only,
        },
        "targets": targets,
        "overall": overall,
        "per_language": per_language,
        "targets_passed": passed,
        "pair_results": pair_results,
    }


def run_direct_evaluation(
    pairs: list[dict[str, Any]],
    verbose: bool = False,
    k: int = 5,
    nli_only: bool = False,
    no_freshness: bool = False,
    adversarial: bool = False,
    shuffle_labels: bool = False,
    heldout: bool = False,
) -> dict[str, Any]:
    """Run evaluation directly against the matching pipeline (no LLM/API needed)."""
    if not HAS_DIRECT:
        print("❌ Direct mode requires running inside the app container.")
        sys.exit(1)

    mode_desc = "directly"
    if nli_only:
        mode_desc += " (NLI-only stance, no rating lookup)"
    if no_freshness:
        mode_desc += " (no freshness decay)"
    print(f"🚀 Evaluating {len(pairs)} pairs {mode_desc} (k={k})…")
    t0 = time.perf_counter()

    matcher = ClaimMatcher(nli_only=nli_only, no_freshness=no_freshness)
    pair_results: list[dict[str, Any]] = []

    for pair in pairs:
        pair_id = pair["id"]
        expected_match = pair["expected_match"]
        expected_stance = pair["expected_stance"]
        expected_url = pair.get("expected_source_url", "")

        lang = pair.get("language", "en")

        claim = Claim(
            claim_id=pair_id,
            claim_text=pair["claim"],
            source_quote=pair["claim"],
            char_start=0,
            char_end=len(pair["claim"]),
            language=lang,
            has_negation=False,
            checkworthiness=CheckworthinessScore(
                harm_potential=0.5,
                virality_potential=0.5,
                verifiability=0.8,
                specificity=0.7,
                public_interest=0.5,
                composite=0.6,
            ),
        )

        try:
            result = asyncio.get_event_loop().run_until_complete(matcher.match(claim, top_k=k * 2))
        except RuntimeError:
            result = asyncio.run(matcher.match(claim, top_k=k * 2))

        matches = [
            {
                "matched_url": m.matched_url,
                "claim_reviewed": m.claim_reviewed,
                "stance": m.stance.value if hasattr(m.stance, "value") else m.stance,
                "final_score": m.final_score,
            }
            for m in result.matches
        ]

        found_in_top_k, rank, predicted_stance = _score_matches(
            matches, expected_match, expected_url, k,
        )

        if verbose:
            hit_mark = "✅" if found_in_top_k else "❌"
            lang_group = pair.get("_lang_group", "?")
            print(
                f"  {hit_mark} [{lang_group}] {pair_id}: "
                f"rank={rank if found_in_top_k else '-'}, "
                f"stance exp={expected_stance} pred={predicted_stance}"
            )

        pair_results.append({
            "id": pair_id,
            "_lang_group": pair.get("_lang_group", "?"),
            "expected_stance": expected_stance,
            "predicted_stance": predicted_stance,
            "found_in_top_k": found_in_top_k,
            "rank": rank,
        })

    elapsed = time.perf_counter() - t0

    by_lang: dict[str, list[dict[str, Any]]] = {}
    for r in pair_results:
        lang_r = r.get("_lang_group", "?")
        by_lang.setdefault(lang_r, []).append(r)

    def lang_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "recall_at_k": round(compute_recall_at_k(results, k), 4),
            "mrr": round(compute_mrr(results), 4),
            "stance_f1": {k2: round(v, 4) for k2, v in compute_stance_f1(results).items()},
            "n": len(results),
            "errors": sum(1 for r in results if "error" in r),
        }

    overall = lang_metrics(pair_results)
    per_language = {lang_l: lang_metrics(res) for lang_l, res in sorted(by_lang.items())}

    targets = {
        "recall_at_5": TARGET_RECALL_AT_5,
        "mrr": TARGET_MRR,
        "stance_f1": TARGET_STANCE_F1,
    }

    passed = {
        "recall_at_5": overall["recall_at_k"] >= TARGET_RECALL_AT_5,
        "mrr": overall["mrr"] >= TARGET_MRR,
        "stance_f1": overall["stance_f1"].get("macro_f1", 0.0) >= TARGET_STANCE_F1,
    }

    return {
        "meta": {
            "version": "v0.1",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "mode": "direct" + ("_nli" if nli_only else ""),
            "k": k,
            "elapsed_s": round(elapsed, 2),
            "total_pairs": len(pairs),
            "nli_only": nli_only,
            "adversarial": adversarial,
            "shuffle_labels": shuffle_labels,
            "no_freshness": no_freshness,
            "heldout": heldout,
        },
        "targets": targets,
        "overall": overall,
        "per_language": per_language,
        "targets_passed": passed,
        "pair_results": pair_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Truthora Benchmark Evaluation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--run-pipeline", action="store_true", help="Run evaluation against live pipeline")
    parser.add_argument("--direct", action="store_true", help="Run direct evaluation (bypasses API/LLM, tests matching pipeline only)")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--k", type=int, default=5, help="Recall@K cutoff (default: 5)")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent API requests (default: 1)")
    parser.add_argument("--delay", type=float, default=2.5, help="Delay between requests in seconds (default: 2.5, avoids Groq rate limits)")
    parser.add_argument("--held-out-only", action="store_true",
        help="Evaluate only on held-out 20%% split (ids ending in _81-_100 per lang)")
    parser.add_argument("--shuffle-labels", action="store_true",
        help="Shuffle expected stances (sanity check — should yield ~random F1)")
    parser.add_argument("--nli-only", action="store_true",
        help="Skip review_rating lookup; use NLI model only for stance classification")
    parser.add_argument("--adversarial", action="store_true",
        help="Use claim_adversarial field instead of claim (realistic tabloid headlines)")
    parser.add_argument("--force-llm", action="store_true",
        help="Force LLM claim extraction in --run-pipeline (bypass headline fast-path)")
    parser.add_argument("--no-freshness", action="store_true",
        help="Disable freshness decay in scoring (all items treated as equally fresh)")
    parser.add_argument(
        "--heldout", action="store_true",
        help="Use LLM-generated heldout pairs (golden_pairs_heldout.json) — genuine held-out evaluation"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file for pipeline results (auto-generated if not specified)",
    )
    args = parser.parse_args()

    # Auto-generate output filename based on flags
    if args.output is None:
        suffix = "baseline_v01"
        if args.held_out_only:
            suffix = "baseline_v01_heldout"
        if getattr(args, 'heldout', False):
            suffix = "heldout"
        if args.shuffle_labels:
            suffix = "baseline_v01_shuffled"
        if args.held_out_only and args.shuffle_labels:
            suffix = "baseline_v01_heldout_shuffled"
        if getattr(args, 'nli_only', False):
            suffix += "_nli"
        if getattr(args, 'adversarial', False):
            suffix += "_adversarial"
        args.output = str(Path(__file__).resolve().parent / "results" / f"{suffix}.json")

    print("=" * 60)
    print("  Truthora — Golden Pairs Benchmark Evaluation")
    print("=" * 60)
    print()

    # Load pairs
    if getattr(args, 'heldout', False):
        pairs = load_heldout_pairs()
        print(f"📊 Loaded {len(pairs)} heldout golden pairs (LLM-generated, no claim_text leakage)")
    else:
        pairs = load_golden_pairs()
        print(f"📊 Loaded {len(pairs)} golden pairs")

    # Held-out split: keep only pairs with numeric suffix 81–100
    if args.held_out_only:
        def _is_held_out(pair_id: str) -> bool:
            m = re.search(r'_(\d+)$', pair_id)
            return m is not None and 81 <= int(m.group(1)) <= 100
        pairs = [p for p in pairs if _is_held_out(p["id"])]
        print(f"🔬 Held-out filter: {len(pairs)} pairs (ids *_81 – *_100)")

    # Shuffle labels sanity check
    if args.shuffle_labels:
        rng = random.Random(42)
        stances = [p["expected_stance"] for p in pairs]
        rng.shuffle(stances)
        for p, s in zip(pairs, stances):
            p["expected_stance"] = s
        print("🔀 Shuffled expected stances (sanity check mode)")

    # Adversarial mode: use claim_adversarial field if available
    if getattr(args, 'adversarial', False):
        replaced = 0
        for p in pairs:
            if p.get("claim_adversarial"):
                p["claim"] = p["claim_adversarial"]
                replaced += 1
        print(f"🎭 Adversarial mode: replaced {replaced}/{len(pairs)} claims with tabloid variants")
        if replaced == 0:
            print("   ⚠️  No claim_adversarial fields found — running with original claims")

    print()

    # Dataset validation (always run)
    summary = evaluate_golden_pairs(pairs, verbose=args.verbose)

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

    # ── Pipeline evaluation ────────────────────────────────────────────────────
    if args.run_pipeline or args.direct:
        nli_only = getattr(args, 'nli_only', False)
        force_llm = getattr(args, 'force_llm', False)

        no_freshness = getattr(args, 'no_freshness', False)

        if args.direct:
            pipeline_results = run_direct_evaluation(
                pairs=pairs,
                verbose=args.verbose,
                k=args.k,
                nli_only=nli_only,
                no_freshness=no_freshness,
                adversarial=getattr(args, 'adversarial', False),
                shuffle_labels=getattr(args, 'shuffle_labels', False),
                heldout=getattr(args, 'heldout', False),
            )
        else:
            pipeline_results = run_pipeline_evaluation(
                pairs=pairs,
                api_url=args.api_url,
                verbose=args.verbose,
                k=args.k,
                concurrency=args.concurrency,
                delay=args.delay,
                force_llm=force_llm,
                nli_only=nli_only,
            )

        overall = pipeline_results["overall"]
        per_lang = pipeline_results["per_language"]
        passed = pipeline_results["targets_passed"]
        elapsed = pipeline_results["meta"]["elapsed_s"]

        print()
        print("=" * 60)
        print("  Pipeline Results")
        print("=" * 60)
        print(f"  Evaluated in {elapsed}s")
        print()
        print(f"  Recall@{args.k}:  {overall['recall_at_k']:.4f}  "
              f"(target ≥ {TARGET_RECALL_AT_5})  {'✅' if passed['recall_at_5'] else '❌'}")
        print(f"  MRR:       {overall['mrr']:.4f}  "
              f"(target ≥ {TARGET_MRR})  {'✅' if passed['mrr'] else '❌'}")
        print(f"  Stance F1: {overall['stance_f1'].get('macro_f1', 0):.4f}  "
              f"(target ≥ {TARGET_STANCE_F1})  {'✅' if passed['stance_f1'] else '❌'}")
        print()
        print("  Per language:")
        for lang, m in per_lang.items():
            print(f"    {lang}: Recall@{args.k}={m['recall_at_k']:.4f}  "
                  f"MRR={m['mrr']:.4f}  F1={m['stance_f1'].get('macro_f1', 0):.4f}  "
                  f"(n={m['n']}, errors={m['errors']})")
        print()

        all_passed = all(passed.values())
        print("🎉 All targets met!" if all_passed else "⚠️  Some targets not yet met.")
        print()

        # Save results
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pipeline_results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved → {out_path}")

        return 0 if all_passed else 1

    print("ℹ️  Full evaluation requires running pipeline:")
    print("   1. Start services: docker-compose up")
    print("   2. Index seed data")
    print("   3. Run: python data/benchmark/evaluate.py --run-pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
