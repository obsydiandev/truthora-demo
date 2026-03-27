# Truthora

> **Open-source multilingual infrastructure for claim verification and fact-check matching.**  
> English · Polish · Ukrainian · Self-hostable · GPU-free · Human-in-the-loop · Apache 2.0

Truthora helps fact-checking NGOs, newsrooms, and researchers detect checkable claims
in news articles and match them against a database of verified fact-checks. It supports
**English**, **Polish**, and **Ukrainian** — languages critical for the EU and Ukrainian
disinformation response ecosystem.

Every AI result requires human review — Truthora assists, never decides.

---

## What it does

1. **Claim Detection** — extracts checkable factual claims from a headline or article text
2. **Claim Normalization** — standardizes claims across languages for consistent matching
3. **Semantic Matching** — BGE-M3 multilingual embeddings + Qdrant vector search → top-10 candidates
4. **Reranking** — cross-encoder rescoring of top-10 candidates
5. **Freshness Scoring** — temporal decay weighting (half-life 180 days) so recent fact-checks rank higher
6. **Stance Detection** — SUPPORTED / REFUTED / NEI via ClaimReview rating-lookup (NLI bridge planned M3)
7. **Uncertainty Signalling** — Shannon entropy flags low-confidence matches for mandatory human review
8. **Streamlit UI** — journalist-facing dashboard with claim list, match scores, source links, freshness badges

> **Human-in-the-loop by design.** Stance labels are provided as signals, not verdicts.  
> Final editorial decisions remain with the journalist or fact-checker.

---

## Architecture

```
Input (headline / article text)
        │
        ▼
┌───────────────────┐
│   Detector        │  Identifies checkable claims (NLP span extraction)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Extractor       │  Extracts claim text, metadata, language
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Normalizer      │  Standardizes claim text (lowercasing, dedup)
└────────┬──────────┘
         │
         ▼
┌────────────────────────────────────┐
│   Matcher (BGE-M3 + Qdrant)        │  Multilingual semantic search → top-10
│   + Temporal Freshness Decay       │  weight(t) = exp(-0.693 × days / 180)
└────────┬───────────────────────────┘
         │
         ▼
┌───────────────────┐
│   Reranker        │  Cross-encoder rescoring of top-10 candidates
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Scorer          │  Final score + entropy-based uncertainty level
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   Knowledge Graph │  Entity linking — implemented, wired in M3
└────────┬──────────┘
         │
         ▼
┌───────────────────────────────────┐
│   Streamlit UI / FastAPI          │  Human-in-the-loop review dashboard
└───────────────────────────────────┘
```

**Infrastructure:**
- **Qdrant** — vector database for fact-check storage and semantic search
- **BGE-M3** — multilingual embedding model (~2 GB, CPU-only, lazy-loaded on first use)
- **Groq API** — LLM inference for claim extraction (configurable; Ollama supported)
- **FastAPI** — REST API (`/analyze`, `/health`)
- **Streamlit** — journalist-facing UI on port 8501

---

## Quick Start

> **⚠️ First-use: BGE-M3 model download (~2 GB)**  
> The embedding model is downloaded from Hugging Face **on first request** (lazy-loaded).  
> The first `/analyze` call or seed ingest will take a few minutes.  
> Ensure stable internet and sufficient disk space before starting.

```bash
git clone https://github.com/obsydiandev/truthora-demo
cd truthora-demo
cp .env.example .env        # fill in GROQ_API_KEY and GOOGLE_FC_API_KEY (see Configuration)

docker compose up --build

# Seed with starter fact-checks (triggers BGE-M3 download ~2 GB on first run)
docker compose exec api python3 data/seeds/seed.py

# Recommended: ingest ~500 real fact-checks from Google Fact Check Tools API
docker compose exec api python3 data/seeds/ingest_google_fc.py

# Seed golden-pair expected matches (for benchmark)
docker compose exec api python3 data/seeds/seed_golden_pairs.py

# Open the UI
open http://localhost:8501
```

---

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Groq API key for LLM claim extraction ([console.groq.com](https://console.groq.com)) |
| `GOOGLE_FC_API_KEY` | ✅ for ingestion | Google Fact Check Tools API key ([developers.google.com](https://developers.google.com/fact-check/tools/api/)) |
| `QDRANT_URL` | optional | Qdrant host (default: `http://qdrant:6333`) |
| `EMBED_MODEL` | optional | Embedding model name (default: `BAAI/bge-m3`) |
| `LLM_MODEL` | optional | Groq model (default: `llama-3.3-70b-versatile`) |

---

## Data Sources

All fact-checks come from the **Google Fact Check Tools API**, ingested via 70 topic-based
seed queries across three languages (EN, PL, UK). After deduplication (deterministic
SHA-256 IDs per `review_url`) the database holds **404 unique documents**
(EN: 185, PL: 166, UK: 53).

| Source | Language | Type |
|---|---|---|
| [Demagog](https://demagog.org.pl) | 🇵🇱 Polish | Fact-checking NGO |
| [OKO.press](https://oko.press) | 🇵🇱 Polish | Investigative journalism |
| [Konkret24 / TVN24](https://konkret24.tvn24.pl) | 🇵🇱 Polish | Newsroom fact-check desk |
| [Fakenews.pl](https://fakenews.pl) | 🇵🇱 Polish | Fact-checking NGO |
| [VoxUkraine](https://voxukraine.org) | 🇺🇦 Ukrainian | Fact-checking NGO |
| [StopFake](https://stopfake.org) | 🇺🇦 Ukrainian | Disinformation monitoring |
| [Full Fact](https://fullfact.org) | 🇬🇧 English | Fact-checking NGO (UK) |
| [Reuters Fact Check](https://reuters.com/fact-check) | 🌍 English | Newswire fact-check desk |
| [ClaimBuster](https://idir.uta.edu/claimbuster/) | 🌍 English | Research / annotated claims |

**Planned integrations (M2):** Native Demagog scraper (PL), VoxCheck scraper (UA),
IFCN ClaimReview feed (multilingual), EDMO network members (EN/EU).

> **Note on coverage:** Topic clustering and small index size inflate retrieval scores
> vs. production scale. UA has only 53 documents for 52 heldout pairs — see
> [data/benchmark/results/README.md](data/benchmark/results/README.md) for full
> methodology discussion.

---

## Benchmark

### Official Baseline — Truthora v0.1 (2026-03-27)

Primary evaluation uses **212 heldout pairs** — claims generated by LLM from
`review_title` only, with no access to indexed `claim_text`. This prevents data
leakage and provides an honest out-of-distribution (OOD) benchmark.

| Configuration | Pairs | Recall@5 | MRR | Stance F1 | Status |
|---|---|---|---|---|---|
| Heldout + rating-lookup | 212 | **0.873** | **0.739** | **0.916**\* | R@5 ✅ MRR ✅ F1 ✅ |
| Heldout + NLI-only | 212 | **0.830** | **0.676** | **0.257** | R@5 ✅ MRR ✅ F1 ❌ |

\*Stance F1 = 0.916 uses ClaimReview `review_rating` metadata (dictionary lookup),
not NLI inference. Reflects operational accuracy when structured metadata is available.

**Per-language breakdown (heldout, NLI-only):**

| Language | Recall@5 | MRR | Stance F1 | Pairs |
|---|---|---|---|---|
| EN | 0.838 | 0.667 | 0.185 | 80 |
| PL | 0.813 | 0.645 | 0.186 | 80 |
| UA | 0.846 | 0.739 | 0.306 | 52 |

**Grant targets** (post-grant, v1.1): Recall@5 ≥ 0.74, MRR ≥ 0.60, Stance F1 ≥ 0.70

> Retrieval exceeds targets across all languages. **Stance F1 = 0.257 (NLI-only)
> is below the random baseline (0.272)** — DeBERTa-v3-small provides no usable
> signal on fact-checking claim-evidence pairs. This is the core gap the grant
> addresses via Opus-MT translation bridge (M3) and expanded annotated dataset (M2).

### Known limitations (v0.1, TRL 4)

- **NLI model does not work for fact-checking domain:** `cross-encoder/nli-deberta-v3-small`
  achieves F1 = 0.257 on heldout pairs — below random (0.272). Rating-lookup masks
  this in normal operation (~66% of documents have ClaimReview ratings).
- **Knowledge Graph not wired:** `core/knowledge_graph.py` is implemented and tested
  but not connected in the matching pipeline (planned for M3).
- **No Demagog/VoxCheck scraping yet:** PL/UA data comes solely from Google FC API.
  Direct scraping planned for M2.
- **Freshness decay untested in benchmark:** All benchmarks run with `--no-freshness`.
  Temporal weighting calibration planned for M3.

### Closed-world sanity checks (v0 golden pairs)

The original 250 golden pairs (`golden_pairs_*_v0_sanity.json`) have
`expected_match` ≈ Qdrant `claim_text` (near-duplicate). They verify component-level
behaviour but overestimate real-world performance due to data overlap.

| Configuration | Recall@5 | MRR | Stance F1 | Notes |
|---|---|---|---|---|
| `--direct` (baseline) | 0.988 | 0.918 | 0.906 | Inflated — lookup stance, closed-world |
| `--direct --nli-only` | 0.964 | 0.895 | **0.333** | True NLI; F1 ≈ random |
| `--direct --adversarial` | 0.972 | 0.907 | 0.920 | Tabloid claims; retrieval robust |
| `--direct --nli-only --adversarial` | 0.920 | 0.811 | **0.351** | Hardest realistic config |
| `--direct --shuffle-labels` (sanity) | 0.988 | 0.918 | 0.272 | Random baseline ≈ 1/3 ✓ |

### Running evaluations

```bash
# Start services
docker compose up -d

# Seed the fact-check database (required for meaningful results)
docker compose exec api python3 data/seeds/seed.py
docker compose exec api python3 data/seeds/ingest_google_fc.py
docker compose exec api python3 data/seeds/seed_golden_pairs.py

# Official heldout benchmarks (primary — use these for reporting)
docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --heldout --no-freshness --output data/benchmark/results/heldout.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --heldout --nli-only --no-freshness \
  --output data/benchmark/results/heldout_nli_only.json

# Closed-world sanity checks (v0 pairs — component verification only)
docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --no-freshness --output data/benchmark/results/baseline.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --nli-only --no-freshness --output data/benchmark/results/nli_only.json

docker compose exec api python3 data/benchmark/evaluate.py \
  --direct --adversarial --no-freshness --output data/benchmark/results/adversarial.json
```

Full methodology and result interpretation: [`data/benchmark/results/README.md`](data/benchmark/results/README.md)

---

## Roadmap

| Milestone | Status | Deliverables |
|---|---|---|
| **M1** — Core pipeline | ✅ Done | BGE-M3 retrieval, reranker, scorer, Streamlit UI, heldout benchmark suite (212 pairs EN/PL/UA) |
| **M2** — Data & evaluation | 🔄 Planned | Heldout benchmark expansion (500+ pairs), Demagog + VoxCheck native scrapers, annotated NLI training dataset |
| **M3** — NLI & Knowledge Graph | 🔄 Planned | Opus-MT translation bridge, domain-adapted NLI (target F1 ≥ 0.70), Knowledge Graph wiring, freshness calibration |
| **M4** — Production | 🔄 Planned | Pilot deployments with media partners, EDMO/IFCN ClaimReview integration, Hugging Face dataset release (CC-BY) |

---

## License

Apache 2.0 — see [LICENSE](LICENSE)
