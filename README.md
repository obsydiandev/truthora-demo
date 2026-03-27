# truthora-demo

Truthora is an open-source multilingual infrastructure for claim detection and fact-check matching for selected languages (English - for Europe area, Polish - for Poland, Ukrainian - for Ukraine).
App could be self-hostable, GPU-free, open for anyone wanting to use it or base their own solution on it. 

It is open for fact-checking NGOs, newsrooms, bloggers and influencers. 

One of main purposes of this solution is merging newest technology with human-in-the-loop design.

## What it does?
Main purpose is to answer the question if the main claims from input heading or article are true or they are a fake news.

## Architecture
Truthora is built with a modular, asynchronous architecture to ensure scalability on commodity hardware.

mermaid
graph TD
    A[News Stream: RSS/GDELT] --> B[FastAPI Ingestion]
    B --> C{Task Queue: Celery}
    C --> D[Claim Extractor: Llama 3.1 via Ollama]
    D --> E[Semantic Search: Qdrant Vector DB]
    E --> F[Stance Detector: DeBERTa-v3 + Opus-MT]
    F --> G[Uncertainty Scorer: Shannon Entropy]
    G --> H[Human-in-the-loop UI: Streamlit]
    H --> I[Verified Audit Log]

## Quick Start


> **⚠️ First-use note — model download (~2 GB)**
> The **BGE-M3** multilingual embedding model (~2 GB) is downloaded from Hugging Face
> **on first request** to the API (lazy-loaded, not at build time).
> The first `/analyze` call or seed ingest will trigger the download and may take a few minutes.
> The model is then cached in the container's filesystem for the lifetime of the container.
> Make sure you have a stable internet connection and enough disk space before starting.

```bash
git clone https://github.com/obsydiandev/truthora-demo
cd truthora-demo
cp .env.example .env        # fill in GROQ_API_KEY and GOOGLE_FC_API_KEY (see Configuration below)


docker compose up --build
docker compose exec api python3 data/seeds/seed.py           # triggers BGE-M3 download (~2 GB) on first run
docker compose exec api python3 data/seeds/ingest_google_fc.py  # pull ~500 real fact-checks (recommended)
docker compose exec api python3 data/seeds/seed_golden_pairs.py  # seed golden-pair expected matches
```

## Data Source

All fact-checks in the Qdrant index come from the **Google Fact Check Tools API**,
ingested via 70 topic-based seed queries across three languages (EN, PL, UK).
After deduplication (deterministic SHA-256 IDs per `review_url`) the database
holds **404 unique documents** (EN: 185, PL: 166, UK: 53).

This data sourcing strategy directly affects benchmark results:

- **Topic clustering:** Seed queries were chosen to cover the same topic
  clusters as the golden pairs (vaccines, elections, climate, war in Ukraine, etc.).
  This means very few off-topic distractors exist — retrieval Recall is high
  by design, not because the model generalises well to open-domain queries.
- **UA coverage gap:** Ukrainian has only 53 documents for 50 golden pairs
  (96% target ratio), making retrieval almost trivial. EN and PL have a
  healthier ratio (~1.8× and ~1.7× docs-per-pair respectively), but still
  far below a production-scale index.
- **Temporal skew:** The Google FC API returns mostly recent fact-checks
  (2022–2025). Older claims or niche topics are underrepresented, which
  limits generalisability conclusions.

A production deployment would require continuous ingestion from RSS feeds
and GDELT (already scaffolded in `services/sources/`) to scale the index
to tens of thousands of documents and reduce the target-ratio inflation.

## Benchmark

Truthora ships a Golden Pairs evaluation suite (250 curated pairs: EN 100 / PL 100 / UA 50).
Each pair has an `expected_source_url` pointing to a real fact-check in the Qdrant database.

```bash
# Make sure services are running first:
docker compose up -d

# Seed the fact-check database (required for meaningful results):
docker compose exec api python3 data/seeds/seed.py
docker compose exec api python3 data/seeds/ingest_google_fc.py
docker compose exec api python3 data/seeds/seed_golden_pairs.py

# Run the benchmark (direct mode — bypasses LLM, tests matching pipeline):
docker compose --profile benchmark run --rm benchmark
```

The benchmark has multiple modes and diagnostic flags that isolate different
components of the pipeline.

### Mode 1: Direct matching (`--direct`)

Bypasses the LLM entirely and feeds the raw claim text straight into
BGE-M3 → Qdrant → BGE-Reranker → stance resolution. This measures
**retrieval and reranking** in isolation.

| Metric | baseline_v03 | Target |
|---|---|---|
| Recall@5 | **0.988** | ≥ 0.74 |
| MRR | **0.918** | ≥ 0.60 |
| Stance F1 (macro) | **0.906** | ≥ 0.70 |

| Language | Recall@5 | MRR | Stance F1 | Pairs |
|---|---|---|---|---|
| EN | 0.980 | 0.887 | 0.811 | 100 |
| PL | 0.990 | 0.922 | 0.931 | 100 |
| UA | 1.000 | 0.970 | 0.980 | 50 |

> **⚠️ Important caveats about direct mode metrics:**
>
> These numbers are **inflated** by several compounding factors
> and should **not** be interpreted as production-ready performance:
>
> 1. **Small database (404 fact-checks):** The Qdrant index holds
>    404 deduplicated documents seeded via targeted queries that mirror the
>    golden pairs topic clusters (plus distractor topics). With so few
>    distractors, near-perfect Recall is expected by design.
>    UA is especially easy (52 docs for 50 pairs — 96% target ratio).
>
> 2. **Stance is lookup-based, not NLI:** The `_resolve_stance()` function
>    resolves stance primarily via a `_RATING_MAP` string lookup on the
>    fact-check's `review_rating` field. Since golden pairs' `expected_stance`
>    was derived from the same `review_rating` values during curation, the
>    shuffle sanity check confirms this: shuffling stances drops F1 from
>    **0.91 → 0.27** (measured), proving the metric measures dictionary
>    consistency, not NLI inference.
>
> 3. **Claim–match lexical overlap:** Many golden pair claims are close
>    paraphrases of the indexed `claim_text`, artificially boosting embedding
>    similarity.
>
> 4. **EN stance imbalance:** EN has 54 REFUTED / 37 NEI / 9 SUPPORTED —
>    SUPPORTED class metrics are unreliable with only 9 samples.
>
> To get a more realistic picture, use the diagnostic flags described below.

### Mode 2: Full end-to-end pipeline (`--run-pipeline`)

Exercises the complete product path through the live API:
**LLM claim extraction → translation → BGE-M3 → Qdrant → Reranker → NLI → LLM stance synthesis**.
Each step introduces independent error.

> **Note:** In current code, the API fast-path skips the LLM for inputs
> ≤ 500 chars (most golden pair claims). Use `--force-llm` to test the true
> end-to-end pipeline. Without it, pipeline mode produces results nearly
> identical to direct mode.

No validated pipeline results are available yet. Running the true
end-to-end pipeline (with `--force-llm`) is expected to show significant
degradation, revealing the **open research gaps** this project addresses:

- **LLM claim extraction** reformulates claims in ways that shift embedding space
- **Translation noise** in PL/UA paths compounds retrieval errors
- **LLM stance synthesis** can override the NLI signal unreliably

### Diagnostic flags

The evaluation script supports flags that stress-test individual components:

```bash
# NLI-only stance: skip rating lookup, force DeBERTa NLI for all stance decisions
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --direct --nli-only --no-freshness --output data/benchmark/results/nli_only.json

# Adversarial claims: use tabloid/social-media paraphrases instead of clean claims
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --direct --adversarial --no-freshness --output data/benchmark/results/adversarial.json

# Both: the hardest realistic test
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --direct --nli-only --adversarial --no-freshness --output data/benchmark/results/hard_mode.json

# True end-to-end pipeline (forces LLM even for short claims):
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --run-pipeline --force-llm --nli-only --no-freshness \
  --api-url http://api:8000 --delay 2.5 \
  --output data/benchmark/results/pipeline_real.json
```

### Measured impact of diagnostic flags

All configurations evaluated on 250 golden pairs against a 404-document
deduplicated Qdrant index (with `--no-freshness` to disable freshness decay bias).

| Configuration | Recall@5 | MRR | Stance F1 | Notes |
|---|---|---|---|---|
| `--direct` (baseline_v03) | 0.988 | 0.918 | 0.906 | Inflated — see caveats above |
| `--direct --nli-only` | 0.964 | 0.895 | **0.333** | True NLI stance; F1 drops 63% |
| `--direct --adversarial` | 0.972 | 0.907 | 0.920 | Tabloid claims; retrieval dips slightly |
| `--direct --nli-only --adversarial` | 0.920 | 0.811 | **0.351** | Hardest realistic config |
| `--direct --shuffle-labels` (sanity) | 0.988 | 0.918 | 0.272 | Random baseline ≈ 1/3 ✓ |
| `--run-pipeline --force-llm` | — | — | — | Pending (requires working LLM) |

**Key findings:**

1. **Retrieval is strong:** BGE-M3 + Reranker achieves Recall@5 ≥ 0.92
   across all configurations including adversarial claims. This component
   works well even in a small-corpus setting.

2. **Stance detection is the bottleneck:** When forced to use actual NLI
   inference (DeBERTa-v3-small) instead of the `_RATING_MAP` shortcut,
   Stance F1 collapses from 0.91 → 0.33 — barely above the 0.27 random
   baseline. The current NLI model lacks the multilingual reasoning capacity
   to classify stance reliably.

3. **Adversarial claims test retrieval robustness:** Tabloid-style
   paraphrases reduce Recall@5 by ~2 pp and MRR by ~7 pp, showing the
   embedding model handles lexical variation well but with room to improve.

4. **The real gap is stance F1 ≥ 0.70 with NLI-only:** Closing this gap —
   particularly in a GPU-free, self-hosted, multilingual setting — is the
   core research contribution this project proposes.

### Running custom evaluations

```bash
# Direct mode (no LLM needed):
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --direct --no-freshness --verbose \
  --k 10 \
  --output data/benchmark/results/my_run.json

# Full pipeline mode (requires running API + Groq/Ollama):
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --run-pipeline --no-freshness --verbose \
  --api-url http://api:8000 \
  --k 10 \
  --delay 2.5 \
  --output data/benchmark/results/my_run.json
```

## License
Apache 2.0 — see LICENSE
