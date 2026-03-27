# Benchmark Results

## Official Baseline — Truthora v0.1 (2026-03-27)

Primary evaluation uses **heldout pairs** (212 LLM-generated claims from
`review_title` only — no `claim_text` leakage). This is the honest OOD
benchmark referenced in the grant application.

| File | Pairs | R@5 | MRR | Stance F1 | What it measures |
|---|---|---|---|---|---|
| `heldout.json` | 212 | 0.873 | 0.739 | 0.916* | OOD retrieval + rating-lookup stance |
| `heldout_nli_only.json` | 212 | 0.830 | 0.676 | 0.257 | OOD retrieval + true NLI (no lookup) |

\*Stance F1 = 0.916 uses rating-lookup (structured `review_rating` metadata from
ClaimReview), not NLI inference. NLI-only F1 ≈ 0.33 — see below.

**Grant targets** (post-grant, v1.1): Recall@5 ≥ 0.74, MRR ≥ 0.60, Stance F1 ≥ 0.70

---

## Closed-World Sanity Checks (v0 golden pairs)

These use the original 250 pairs where `expected_match` = Qdrant `claim_text`.
They verify component-level behavior but overestimate real-world performance
due to data overlap. Renamed to `*_v0_sanity.json`.

| File | Flags | What it tests |
|---|---|---|
| `baseline.json` | `--direct --no-freshness` | Default pipeline: BGE-M3 retrieval → Reranker → rating-lookup stance. Upper bound (stance is dictionary lookup). |
| `nli_only.json` | `--direct --nli-only --no-freshness` | Stance resolved solely by DeBERTa-v3-small NLI — no rating lookup. Measures true NLI capability. |
| `adversarial.json` | `--direct --adversarial --no-freshness` | Tabloid/social-media style claim paraphrases. Tests retrieval robustness to lexical variation. |
| `hard_mode.json` | `--direct --nli-only --adversarial --no-freshness` | NLI-only + adversarial — hardest realistic configuration. |
| `shuffle_sanity.json` | `--direct --shuffle-labels --no-freshness` | Shuffled expected stances. Sanity check — F1 should be ≈ 0.33 (random). |

### Key finding: NLI gap

| Configuration | Stance Macro F1 | Interpretation |
|---|---|---|
| Rating lookup (baseline) | 0.903 | Structured metadata works |
| NLI-only (DeBERTa) | 0.333 | Near-random — NLI model fails on fact-checking domain |
| Shuffle sanity | 0.272 | Random baseline |

**This NLI gap is the core problem the grant addresses** via Opus-MT
translation bridge (M3) and expanded annotated dataset (M2).

## JSON structure

```
{
  "meta": {              // run configuration
    "mode": "direct",
    "k": 5,
    "nli_only": false,
    "adversarial": false,
    "shuffle_labels": false,
    "no_freshness": true,
    "golden_pairs_count": 250,
    "timestamp": "..."
  },
  "targets": {           // pass/fail thresholds
    "recall_at_k": 0.74,
    "mrr": 0.6,
    "stance_f1": 0.7
  },
  "overall": {           // aggregate metrics
    "recall_at_k": 0.988,
    "mrr": 0.918,
    "stance_f1": {
      "SUPPORTED": ...,
      "REFUTED": ...,
      "NEI": ...,
      "macro_f1": 0.906
    },
    "n": 250,
    "errors": 0
  },
  "per_language": {      // same structure per language
    "EN": { ... },
    "PL": { ... },
    "UA": { ... }
  },
  "targets_passed": true,
  "pair_results": [ ... ] // per-pair detail (claim, matched URL, scores, etc.)
}
```

## How to interpret

- **Recall@k**: Fraction of pairs where the expected fact-check appeared in the
  top-k results. High values (>0.95) are expected given the small, topic-clustered DB.
- **MRR** (Mean Reciprocal Rank): Average of 1/rank for the expected match.
  MRR = 1.0 means every match was rank-1.
- **Stance F1** (macro): Average F1 across SUPPORTED / REFUTED / NEI classes.
  - In `baseline` this is inflated by the rating-lookup shortcut.
  - In `nli_only` this reflects actual NLI model performance.
  - Compare `nli_only` F1 against `shuffle_sanity` F1 — if they are close,
    the NLI model is near random.

## Regenerating results

```bash
# Official heldout benchmarks (primary — use these for reporting)
docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --heldout --no-freshness --output data/benchmark/results/heldout.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --heldout --nli-only --no-freshness --output data/benchmark/results/heldout_nli_only.json

# Closed-world sanity checks (v0 pairs — component verification only)
docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --no-freshness --output data/benchmark/results/baseline.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --nli-only --no-freshness --output data/benchmark/results/nli_only.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --adversarial --no-freshness --output data/benchmark/results/adversarial.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --nli-only --adversarial --no-freshness --output data/benchmark/results/hard_mode.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --shuffle-labels --no-freshness --output data/benchmark/results/shuffle_sanity.json
```
