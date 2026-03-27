#!/usr/bin/env python3
"""Validate golden-pair coverage against fact-checks already in Qdrant.

Checks that every golden pair's expected_source_url exists in the database
(ingested via ingest_google_fc.py or seed.py).  Does NOT insert any data —
the benchmark must rely on organically ingested fact-checks to avoid
data-leakage bias.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BENCH_DIR = PROJECT_ROOT / "data" / "benchmark"
LANG_MAP = {"ua": "uk"}


def main() -> int:
    from services.qdrant import QdrantService

    qdrant = QdrantService()
    qdrant.ensure_collections()

    # Collect all source URLs currently in Qdrant
    existing: set[str] = set()
    try:
        points, _ = qdrant._client.scroll(
            collection_name="fact_checks",
            limit=10000,
            with_payload=["source_url"],
        )
        for p in points:
            url = (p.payload or {}).get("source_url", "")
            if url:
                existing.add(url.rstrip("/").lower())
        print(f"📊 {len(existing)} fact-checks currently in Qdrant")
    except Exception as exc:
        print(f"❌ Could not read Qdrant: {exc}")
        return 1

    total_found = 0
    total_missing = 0
    missing_pairs: list[dict[str, str]] = []

    for fname in ["golden_pairs_en_v0_sanity.json", "golden_pairs_pl_v0_sanity.json", "golden_pairs_ua_v0_sanity.json"]:
        path = BENCH_DIR / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            pairs = json.load(f)

        lang_label = fname.split("_")[-1].split(".")[0].upper()
        found = 0
        missing = 0

        for pair in pairs:
            url = pair.get("expected_source_url", "").rstrip("/").lower()
            if url and url in existing:
                found += 1
            else:
                missing += 1
                missing_pairs.append({"id": pair["id"], "url": pair.get("expected_source_url", "")})

        total_found += found
        total_missing += missing
        status = "✅" if missing == 0 else "⚠️"
        print(f"  {status} {lang_label}: {found}/{found + missing} pairs have matching fact-checks")

    if missing_pairs:
        print(f"\n⚠️  {total_missing} golden pairs have NO matching fact-check in Qdrant:")
        for mp in missing_pairs[:20]:
            print(f"     {mp['id']}: {mp['url']}")
        if len(missing_pairs) > 20:
            print(f"     … and {len(missing_pairs) - 20} more")
        print("\n   These pairs will fail Recall in the benchmark.")
        print("   Run ingest_google_fc.py first, or update the golden pair URLs.")
    else:
        print(f"\n✅ All {total_found} golden pairs have matching fact-checks in the database.")

    return 0


if __name__ == "__main__":
    print("=" * 55)
    print("  Validate golden-pair coverage in Qdrant")
    print("=" * 55)
    sys.exit(main())
