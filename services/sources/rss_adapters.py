"""Truthora — RSS feed adapters for regional fact-checkers.

Uses feedparser to poll fact-check articles from RSS feeds:
  - Demagog PL, Konkret24 (Poland)
  - StopFake UA, VoxCheck UA, Texty UA (Ukraine)
  - EFCSN, Full Fact, Reuters FC (Europe / Global)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser

logger = logging.getLogger(__name__)

# Default path to the RSS feeds JSON configuration
DEFAULT_FEEDS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "rss_feeds.json"


class RSSAdapter:
    """Adapter for fetching and parsing fact-check RSS feeds."""

    def __init__(self, feeds_path: str | Path | None = None) -> None:
        self._feeds_path = Path(feeds_path) if feeds_path else DEFAULT_FEEDS_PATH
        self._feeds: list[dict[str, Any]] = self._load_feeds()

    def _load_feeds(self) -> list[dict[str, Any]]:
        """Load the RSS feed configuration from JSON."""
        if not self._feeds_path.exists():
            logger.warning("RSS feeds config not found: %s", self._feeds_path)
            return []
        with open(self._feeds_path, encoding="utf-8") as f:
            return json.load(f)

    @property
    def feeds(self) -> list[dict[str, Any]]:
        return self._feeds

    def fetch_feed(self, feed_url: str) -> list[dict[str, Any]]:
        """Fetch and parse a single RSS feed.

        Returns a list of article entries with keys:
          - title, link, published, summary, source_name, source_country
        """
        try:
            parsed = feedparser.parse(feed_url)
        except Exception:
            logger.exception("Failed to fetch RSS feed: %s", feed_url)
            return []

        entries: list[dict[str, Any]] = []
        for entry in parsed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except Exception:
                    pass

            entries.append({
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": published,
                "summary": getattr(entry, "summary", ""),
            })

        return entries

    def fetch_all(self) -> list[dict[str, Any]]:
        """Fetch all configured RSS feeds and return combined entries.

        Each entry is annotated with source_name and source_country.
        """
        all_entries: list[dict[str, Any]] = []
        for feed_cfg in self._feeds:
            url = feed_cfg.get("url", "")
            name = feed_cfg.get("name", "Unknown")
            country = feed_cfg.get("country", "")
            language = feed_cfg.get("language", "en")

            logger.info("Fetching RSS: %s (%s)", name, url)
            entries = self.fetch_feed(url)

            for entry in entries:
                entry["source_name"] = name
                entry["source_country"] = country
                entry["source_language"] = language

            all_entries.extend(entries)

        logger.info("Fetched %d total RSS entries from %d feeds", len(all_entries), len(self._feeds))
        return all_entries
