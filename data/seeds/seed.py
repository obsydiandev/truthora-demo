#!/usr/bin/env python3
"""Seed script for loading initial fact-checks into Qdrant."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SEEDS_DIR = Path(__file__).resolve().parent
SEED_FILE = SEEDS_DIR / "initial_fact_checks.json"

PROJECT_ROOT = SEEDS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_seed_data() -> list[dict]:
    """Load seed fact-checks from JSON file."""
    if not SEED_FILE.exists():
        print(f"❌ Seed file not found: {SEED_FILE}")
        sys.exit(1)

    with open(SEED_FILE, encoding="utf-8") as f:
        data = json.load(f)

    print(f"📦 Loaded {len(data)} seed fact-checks from {SEED_FILE.name}")
    return data


def main() -> int:
    """Seed the database with initial fact-checks."""
    print("=" * 50)
    print("  Truthora — Seed Initial Fact-Checks")
    print("=" * 50)
    print()

    entries = load_seed_data()

    try:
        from services.embeddings import EmbeddingService
        from services.qdrant import QdrantService

        qdrant = QdrantService()
        qdrant.ensure_collections()
        embedder = EmbeddingService()

        for i, entry in enumerate(entries):
            text = entry.get("claim_text", "")
            vector = embedder.embed_single(text)
            import hashlib
            source_url = entry.get("source_url", text)
            normalized_url = source_url.rstrip("/").split("?")[0].split("#")[0]
            point_id = hashlib.sha256(normalized_url.encode()).hexdigest()[:32]
            qdrant.upsert_fact_check(point_id, vector, entry)

        print(f"✅ Seeded {len(entries)} fact-checks into Qdrant")
    except ImportError as e:
        print(f"⚠️  Qdrant service not available (missing dependencies): {e}")
        print("   Install requirements first: pip install -r requirements.txt")
        print("   Or run inside Docker: docker-compose up")
        return 1
    except Exception as e:
        print(f"❌ Failed to seed database: {e}")
        print("   Make sure Qdrant is running (docker-compose up)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
