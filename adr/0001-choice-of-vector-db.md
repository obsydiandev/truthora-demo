# ADR-0001: Choice of Vector Database — Qdrant

**Status:** Accepted  
**Date:** 2026-03-26  
**Author:** Truthora Core  
**Milestone:** M1 — Production Hardening  

---

## Context

Truthora requires a vector database to store and retrieve semantic embeddings of fact-check claims. The retrieval step is the core of the matching pipeline: given an extracted claim, the system must find the top-K semantically similar fact-checks from an index of potentially tens of thousands of entries.

The choice of vector database directly impacts:
- Deployment model (self-hosted vs. cloud-only)
- Memory footprint on commodity VPS hardware (4 vCPU / 4–8 GB RAM, no GPU)
- Filtering capabilities (by language, date, source, confidence tier)
- Operational complexity for end-user organizations (NGOs, newsrooms)
- License compatibility with Apache 2.0 project distribution

Evaluation was conducted against four candidates during v0.1 development:
Qdrant, Weaviate, Milvus, and pgvector (PostgreSQL extension).

---

## Decision Drivers

1. **Self-hostability** — must run on a standard VPS without managed cloud dependency
2. **Memory efficiency** — target host: 4 GB RAM, shared with the NLI model
3. **Filtering support** — must filter by `language`, `date_range`, `source_domain`
4. **Python-native client** — tight integration with FastAPI async stack
5. **License** — Apache 2.0 compatible
6. **Operational simplicity** — single Docker container, no external dependencies

---

## Options Considered

### Option A: Qdrant ✅ CHOSEN
- **License:** Apache 2.0
- **Deployment:** Single Docker container (`qdrant/qdrant`)
- **Memory:** ~150 MB base; ~1.5 GB for 100K BGE-M3 vectors (1024-dim, float32)
- **Filtering:** Native payload filtering (JSON fields, range, geo, nested)
- **Client:** `qdrant-client` async Python library, well-maintained
- **Quantization:** Built-in scalar (INT8) and binary quantization — critical for VPS RAM budget
- **Strengths:** Rust core (performance), HNSW index, gRPC + REST, active development
- **Weaknesses:** Newer project than Milvus; smaller enterprise ecosystem

### Option B: Weaviate
- **License:** BSD-3-Clause (compatible but modules are proprietary)
- **Deployment:** Docker, but default config pulls external modules
- **Memory:** Higher baseline (~400 MB+), heavier for small deployments
- **Filtering:** GraphQL-based, expressive but verbose
- **Concern:** Some key modules (e.g., text2vec-openai) encourage cloud dependency — counter to Truthora's local-first principle

### Option C: Milvus
- **License:** Apache 2.0
- **Deployment:** Requires etcd + MinIO as dependencies — 3-container setup minimum
- **Memory:** ~1 GB+ for the stack alone, exceeds budget for 4 GB VPS
- **Filtering:** Mature and powerful
- **Concern:** Operational overhead too high for NGO self-hosting scenario

### Option D: pgvector (PostgreSQL extension)
- **License:** PostgreSQL License (permissive)
- **Deployment:** Single container, familiar ops model
- **Memory:** Efficient, shares PostgreSQL instance
- **Filtering:** Full SQL — most flexible
- **Concern:** No native HNSW quantization; sequential scan performance degrades beyond ~100K vectors without tuning; no built-in async Python client matching qdrant-client ergonomics
- **Suitable as fallback** if Qdrant introduces breaking license changes

---

## Decision

**Qdrant** is selected as the primary vector store for Truthora v1.0 and v1.1.

Rationale:
- Single-container deployment aligns with the "zero-configuration" Docker target (M1)
- Built-in scalar quantization reduces memory from ~6 GB to ~1.5 GB for 100K vectors — fits within 4 GB VPS budget alongside the NLI model
- Native payload filtering enables language-scoped retrieval without application-layer post-filtering
- Apache 2.0 license is fully compatible with Truthora's distribution model
- `qdrant-client` async API integrates cleanly with FastAPI without blocking the event loop

---

## Consequences

**Positive:**
- Single `docker-compose.yml` entry; no additional infrastructure services
- Memory budget maintained: Qdrant + DeBERTa-ONNX + FastAPI fits within 4 GB RAM
- Payload filters enable `language=pl` scoped retrieval — critical for cross-lingual pipeline (M3)
- Built-in snapshot API enables index backup/restore for pilot deployments (M4)

**Negative / risks:**
- Qdrant is younger than Milvus; API stability across major versions requires monitoring
- If Qdrant changes license (unlikely but possible), pgvector is the documented fallback

**Neutral:**
- BGE-M3 embeddings (1024-dim) stored as float32 by default; INT8 quantization enabled in production config to reduce RAM by ~4×

---

## Related ADRs

- ADR-0002: Choice of Embedding Model (BGE-M3 vs. multilingual-e5) — *planned M1*
- ADR-0003: Ollama as Default LLM Backend — *planned M1*
- ADR-0004: ClaimReview JSON-LD as Output Format — *planned M1*
- ADR-0005: ONNX Runtime for CPU Inference — *planned M3*
- ADR-0006: Opus-MT as Cross-lingual NLI Bridge — *planned M3*

---

## References

- Qdrant documentation: https://qdrant.tech/documentation/
- Qdrant quantization guide: https://qdrant.tech/documentation/guides/quantization/
- BGE-M3 model card: https://huggingface.co/BAAI/bge-m3
- Truthora v0.1 benchmark: `data/benchmark/baseline_v01.json`
