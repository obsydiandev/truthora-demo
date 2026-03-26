#!/usr/bin/env python3
"""One-off script to find overlaps between initial_fact_checks.json and golden pairs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "seeds" / "initial_fact_checks.json") as f:
    seeds = json.load(f)

pairs = []
for fname in ["golden_pairs_en.json", "golden_pairs_pl.json", "golden_pairs_ua.json"]:
    p = ROOT / "benchmark" / fname
    if p.exists():
        with open(p) as f:
            pairs.extend(json.load(f))

gp_urls = {p.get("expected_source_url", "").rstrip("/").lower() for p in pairs}
gp_matches = {p.get("expected_match", "").strip().lower() for p in pairs}
gp_claims = {p.get("claim", "").strip().lower() for p in pairs}

print("=== initial_fact_checks entries overlapping with golden pairs ===")
overlapping_indices = []
for i, s in enumerate(seeds):
    url = s.get("source_url", "").rstrip("/").lower()
    text = s.get("claim_text", "").strip().lower()
    url_hit = url in gp_urls if url else False
    text_hit = text in gp_matches or text in gp_claims
    if url_hit or text_hit:
        overlapping_indices.append(i)
        print(f"  [{i}] URL={url_hit} TEXT={text_hit}: {s.get('claim_text', '')[:80]}")

print(f"\nTotal seeds: {len(seeds)}, overlapping: {len(overlapping_indices)}")
print(f"Indices to remove: {overlapping_indices}")
