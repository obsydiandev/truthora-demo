# truthora-demo

Truthora is an open-source multilingual infrastructure for claim detection and fact-check matching for selected language (Englsh - for Europe area, Polish - for Poland, Ukraian - for Ukraine.
App could be self-hostable, GPU-free open for anyone wanting to use it or based their own solution on it. 

It is open for fact-checking NGOs, newsrooms, blogers and influancers. 

One of main purpose of solution is merging newest technolgy with human-in-the-loop desing.

## What it does?

## Architecture

## Quick Start

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
```

Open http://localhost:8501

## Configuration


## Data Sources


## Benchmark

Truthora ships a Golden Pairs evaluation suite (255 pairs: EN 100 / PL 100 / UA 55).

```bash
# Make sure services are running first:
docker compose up -d

# Seed the fact-check database (required for meaningful results):
docker compose exec api python3 data/seeds/seed.py
docker compose exec api python3 data/seeds/ingest_google_fc.py

# Run the benchmark — everything runs inside the container, no extra installs needed:
docker compose run --rm benchmark
```

Results are written to `data/benchmark/results/baseline_v01.json`.

| Metric | Target |
|---|---|
| Recall@5 | ≥ 0.74 |
| MRR | ≥ 0.60 |
| Stance F1 (macro) | ≥ 0.70 |

To adjust parameters:

```bash
docker compose run --rm benchmark python3 data/benchmark/evaluate.py \
  --run-pipeline --verbose \
  --api-url http://api:8000 \
  --k 10 \
  --concurrency 10 \
  --output data/benchmark/results/my_run.json
```

## License
Apache 2.0 — see LICENSE
