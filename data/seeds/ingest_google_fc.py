#!/usr/bin/env python3
"""Ingest real fact-checks from Google Fact Check Tools API into Qdrant."""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SEED_QUERIES = [
    # ── English: topic-targeted ───────────────────────────────────
    ("covid vaccines safety", "en"),
    ("covid vaccines infertility", "en"),
    ("covid vaccines microchip", "en"),
    ("ivermectin covid treatment", "en"),
    ("5G coronavirus", "en"),
    ("bill gates microchip vaccine", "en"),
    ("climate change hoax", "en"),
    ("election fraud 2020", "en"),
    ("ukraine war russia", "en"),
    ("ukraine grain exports", "en"),
    ("nato expansion russia", "en"),
    ("donald trump conviction", "en"),
    ("immigration crime statistics", "en"),
    ("moon landing hoax", "en"),
    ("flat earth", "en"),
    # ── English: distractors (not in golden pairs) ────────────────
    ("AI deepfake video detection", "en"),
    ("artificial intelligence job losses", "en"),
    ("bitcoin cryptocurrency scam", "en"),
    ("GMO food safety health", "en"),
    ("water fluoridation conspiracy", "en"),
    ("celebrity death hoax fake news", "en"),
    ("UFO aliens government cover up", "en"),
    ("nuclear energy safety Chernobyl", "en"),
    ("weight loss supplements fraud", "en"),
    ("sports doping athletes steroids", "en"),
    ("chemtrails conspiracy theory", "en"),
    ("glyphosate Roundup cancer", "en"),
    ("Elon Musk Twitter misinformation", "en"),
    ("lab leak Wuhan virus origin", "en"),
    ("bird flu pandemic avian influenza", "en"),
    # ── Polish: topic-targeted ────────────────────────────────────
    ("szczepionki covid", "pl"),
    ("szczepionki mRNA bezpieczeństwo", "pl"),
    ("inflacja polska 2024", "pl"),
    ("migranci polska przestępczość", "pl"),
    ("węgiel Polska energia", "pl"),
    ("OZE Polska fotowoltaika wiatr", "pl"),
    ("wybory Polska fałszerstwo", "pl"),
    ("Polska UE Polexit", "pl"),
    ("Polska fundusze europejskie", "pl"),
    ("Ukraina Polska pomoc wojskowa", "pl"),
    ("granica białoruś migranci", "pl"),
    ("dezinformacja rosyjska Polska", "pl"),
    ("KPO Krajowy Plan Odbudowy", "pl"),
    ("elektrownia jądrowa Polska", "pl"),
    # ── Polish: distractors ───────────────────────────────────────
    ("kryptowaluty bitcoin oszustwo polska", "pl"),
    ("sztuczna inteligencja deepfake", "pl"),
    ("GMO żywność Polska zdrowie", "pl"),
    ("suplementy diety niebezpieczne", "pl"),
    ("smog Polska zanieczyszczenie powietrza", "pl"),
    ("chemtrails smugi kondensacyjne samoloty", "pl"),
    ("fluoryzacja wody teoria spiskowa", "pl"),
    ("glifosat Roundup rak Polska", "pl"),
    ("ptasia grypa pandemia Polska", "pl"),
    ("piramidy finansowe amber gold", "pl"),
    # ── Ukrainian: topic-targeted ─────────────────────────────────
    ("Україна НАТО", "uk"),
    ("зерно Україна експорт", "uk"),
    ("Росія Україна дезінформація", "uk"),
    ("Крим анексія референдум", "uk"),
    ("Україна ЄС вступ кандидат", "uk"),
    ("біолабораторії Пентагон Україна", "uk"),
    ("санкції Росія ефективність", "uk"),
    ("енергетика Україна обстріли", "uk"),
    ("мобілізація Україна закон", "uk"),
    ("Зеленський опозиція ЗМІ", "uk"),
    # ── Ukrainian: distractors ────────────────────────────────────
    ("криптовалюта біткоїн шахрайство", "uk"),
    ("штучний інтелект дипфейк відео", "uk"),
    ("ГМО продукти безпека здоров'я", "uk"),
    ("хімтрейли сліди літаків змова", "uk"),
    ("пташиний грип пандемія Україна", "uk"),
    ("вакцинація діти аутизм", "uk"),
    ("5G вежі здоров'я випромінювання", "uk"),
]

BROAD_LANGUAGES = ["en", "pl", "uk"]


async def ingest() -> int:
    from services.embeddings import EmbeddingService
    from services.qdrant import QdrantService
    from services.sources.google_fc import GoogleFactCheckClient

    api_key = os.getenv("GOOGLE_FC_API_KEY", "")
    if not api_key:
        print("❌ GOOGLE_FC_API_KEY not set in environment")
        return 1

    qdrant = QdrantService()
    qdrant.ensure_collections()
    embedder = EmbeddingService()
    client = GoogleFactCheckClient(api_key=api_key)

    total = 0
    seen_urls: set[str] = set()

    def _index_item(item: dict) -> bool:
        nonlocal total
        review_url = item.get("review_url", "")
        claim_text = item.get("claim_text", "").strip()
        if not claim_text or review_url in seen_urls:
            return False
        seen_urls.add(review_url)
        payload = {
            "claim_text": claim_text,
            "source_url": review_url,
            "source_name": item.get("review_publisher", ""),
            "language": item.get("language_code", "en"),
            "review_rating": item.get("textual_rating", ""),
            "published_at": item.get("claim_date"),
            "claimant": item.get("claimant"),
            "review_title": item.get("review_title", ""),
        }
        try:
            vector = embedder.embed_single(claim_text)
            point_id = hashlib.sha256(review_url.encode()).hexdigest()[:32]
            qdrant.upsert_fact_check(point_id, vector, payload)
            total += 1
            return True
        except Exception as e:
            print(f"     ⚠️  Skipped '{claim_text[:50]}': {e}")
            return False

    # 1. Topic queries
    print("\n[1/2] Topic-based queries...")
    for query, lang in SEED_QUERIES:
        print(f"  🔍 '{query}' [{lang}]")
        try:
            results = await client.search(query, language_code=lang, page_size=10)
            added = sum(_index_item(r) for r in results)
            print(f"     +{added} new (total: {total})")
        except Exception as e:
            print(f"     ⚠️  Failed: {e}")

    # 2. Broad unpaged fetch
    print("\n[2/2] Broad unpaged fetch per language...")
    for lang in BROAD_LANGUAGES:
        print(f"  🌐 Fetching all recent [{lang}] (up to 1000)...")
        try:
            results = await client.search_all(language_code=lang, max_pages=10, page_size=100)
            added = sum(_index_item(r) for r in results)
            print(f"     +{added} new (total: {total})")
        except Exception as e:
            print(f"     ⚠️  Failed: {e}")

    print(f"\n✅ Done — {total} fact-checks indexed into Qdrant")
    return 0


def main() -> int:
    print("=" * 55)
    print("  Truthora — Ingest Google Fact Check API")
    print("=" * 55)
    return asyncio.run(ingest())


if __name__ == "__main__":
    sys.exit(main())
