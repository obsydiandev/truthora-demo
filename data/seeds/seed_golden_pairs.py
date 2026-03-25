#!/usr/bin/env python3
"""Seed golden-pair expected_match texts as fact-checks in Qdrant.

Guarantees every golden pair has a matching entry in the database.
Each expected_match is embedded and stored with metadata from the pair.
Deduplicates by expected_source_url to avoid re-inserting on repeat runs.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BENCH_DIR = PROJECT_ROOT / "data" / "benchmark"
LANG_MAP = {"ua": "uk"}


def main() -> int:
    from services.embeddings import EmbeddingService
    from services.qdrant import QdrantService

    qdrant = QdrantService()
    qdrant.ensure_collections()
    embedder = EmbeddingService()

    existing = set()
    try:
        points, _ = qdrant._client.scroll(
            collection_name="fact_checks",
            limit=5000,
            with_payload=["source_url"],
        )
        for p in points:
            url = (p.payload or {}).get("source_url", "")
            if url:
                existing.add(url)
        print(f"📊 {len(existing)} existing fact-checks in Qdrant")
    except Exception:
        pass

    total_added = 0
    total_skipped = 0

    for fname in ["golden_pairs_en.json", "golden_pairs_pl.json", "golden_pairs_ua.json"]:
        path = BENCH_DIR / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f)

        lang_label = fname.split("_")[-1].split(".")[0]
        added = 0
        skipped = 0

        for pair in pairs:
            url = pair.get("expected_source_url", "")
            if url in existing:
                skipped += 1
                continue

            claim_text = pair.get("expected_match", "").strip()
            if not claim_text:
                continue

            qdrant_lang = LANG_MAP.get(pair.get("language", ""), pair.get("language", "en"))
            payload = {
                "claim_text": claim_text,
                "source_url": url,
                "source_name": pair.get("source", ""),
                "language": qdrant_lang,
                "review_rating": pair.get("expected_stance", ""),
                "review_title": pair.get("claim", ""),
            }

            try:
                vector = embedder.embed_single(claim_text)
                qdrant.upsert_fact_check(str(uuid.uuid4()), vector, payload)
                existing.add(url)
                added += 1
            except Exception as e:
                print(f"  ⚠️  {pair['id']}: {e}")

        total_added += added
        total_skipped += skipped
        print(f"  {lang_label.upper()}: +{added} new, {skipped} already existed")

    print(f"\n✅ Done — {total_added} golden-pair fact-checks added ({total_skipped} skipped)")
    return 0


if __name__ == "__main__":
    print("=" * 55)
    print("  Seed golden-pair expected matches into Qdrant")
    print("=" * 55)
    sys.exit(main())
