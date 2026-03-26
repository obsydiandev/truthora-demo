# truthora-demo

Truthora is an open-source multilingual infrastructure for claim detection and fact-check matching for selected language (Englsh - for Europe area, Polish - for Poland, Ukraian - for Ukraine.
App could be self-hostable, GPU-free open for anyone wanting to use it or based their own solution on it. 

It is open for fact-checking NGOs, newsrooms, blogers and influancers. 

One of main purpose of solution is merging newest technolgy with human-in-the-loop desing.

## What it does?
Main purpose is to answer the question if the main claims from input heading or article are true or they are a fake news.

## Architecture

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

## Data Sources



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

Results are written to `data/benchmark/results/baseline_v01.json`.

| Metric | Current | Target |
|---|---|---|
| Recall@5 | **0.9960** ✅ | ≥ 0.74 |
| MRR | **0.9467** ✅ | ≥ 0.60 |
| Stance F1 (macro) | **0.8656** ✅ | ≥ 0.70 |

| Language | Recall@5 | MRR | Stance F1 | Pairs |
|---|---|---|---|---|
| EN | 0.9900 | 0.9300 | 0.7498 | 100 |
| PL | 1.0000 | 0.9467 | 0.8674 | 100 |
| UA | 1.0000 | 0.9800 | 0.9587 | 50 |

> **Note:** The benchmark runs in `--direct` mode by default, which bypasses
> the LLM (Groq/Ollama) and tests the matching pipeline directly
> (BGE-M3 → Qdrant → BGE-Reranker → NLI). Use `--run-pipeline` for
> full end-to-end evaluation (requires a running API with Groq/Ollama).
> NLI stance classification uses `cross-encoder/nli-deberta-v3-small` and
> reranking uses `BAAI/bge-reranker-v2-m3` (~1.3 GB combined, downloaded on
> first request and cached in the `hf_cache` volume).

> **Reproducibility note:** Benchmark results depend on the contents of the Qdrant database
> at the time of evaluation. Results shown above were measured on **564 fact-checks
> (EN: 307 / PL: 199 / UK: 55)** indexed on 2026-03-26 via `ingest_google_fc.py`.
> Re-running after a fresh ingest may yield slightly different metrics as the Google
> Fact Check API returns a varying number of documents over time.
> For reproducible results, use a fixed database snapshot.


To adjust parameters:

```bash
# Direct mode (no LLM needed):
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --direct --verbose \
  --k 10 \
  --output data/benchmark/results/my_run.json

# Full pipeline mode (requires running API + Groq/Ollama):
docker compose --profile benchmark run --rm benchmark python3 data/benchmark/evaluate.py \
  --run-pipeline --verbose \
  --api-url http://api:8000 \
  --k 10 \
  --delay 2.5 \
  --output data/benchmark/results/my_run.json
```

## License
Apache 2.0 — see LICENSE
