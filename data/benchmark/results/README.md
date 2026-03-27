# Benchmark Results

Each JSON file stores one full evaluation run of the 250 golden-pair suite
(EN 100 / PL 100 / UA 50) against the deduplicated Qdrant index (404 docs).

## Files

| File | Flags | What it tests |
|---|---|---|
| `baseline.json` | `--direct --no-freshness` | Default pipeline: BGE-M3 retrieval → Reranker → rating-lookup stance. Establishes the upper bound (stance is a dictionary lookup, not inference). |
| `nli_only.json` | `--direct --nli-only --no-freshness` | Same retrieval, but stance resolved solely by DeBERTa-v3-small NLI — no rating lookup. Measures true NLI capability. |
| `adversarial.json` | `--direct --adversarial --no-freshness` | Uses tabloid/social-media style claim paraphrases instead of clean claims. Tests retrieval robustness to lexical variation. |
| `hard_mode.json` | `--direct --nli-only --adversarial --no-freshness` | Combines NLI-only + adversarial claims — the hardest realistic configuration. |
| `shuffle_sanity.json` | `--direct --shuffle-labels --no-freshness` | Golden-pair expected stances are randomly shuffled before scoring. Sanity check — F1 should be ≈ 0.33 (random). |

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
