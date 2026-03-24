"""GDELT BigQuery client for real-time news monitoring."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMEOUT = 15


class GDELTClient:
    """Client for GDELT Project real-time news monitoring.

    Uses the GDELT DOC 2.0 API for article discovery.
    Returns URLs that can be processed by Trafilatura.
    """

    def __init__(self) -> None:
        self._base_url = GDELT_DOC_API_URL

    async def search_articles(
        self,
        query: str,
        source_country: str | None = None,
        source_language: str | None = None,
        max_records: int = 25,
        timespan: str = "15min",
    ) -> list[dict[str, Any]]:
        """Search GDELT for recent news articles matching a query.

        Args:
            query: Search terms
            source_country: Filter by country code (e.g., 'PL', 'UA')
            source_language: Filter by language (e.g., 'Polish', 'Ukrainian')
            max_records: Maximum articles to return (default 25)
            timespan: Time window (e.g., '15min', '1h', '24h')

        Returns:
            List of article dicts with keys: url, title, source, language,
            country, seendate, domain, socialimage
        """
        params: dict[str, Any] = {
            "query": query,
            "mode": "artlist",
            "maxrecords": str(max_records),
            "timespan": timespan,
            "format": "json",
            "sort": "datedesc",
        }

        if source_country:
            params["query"] += f" sourcecountry:{source_country}"
        if source_language:
            params["query"] += f" sourcelang:{source_language}"

        try:
            async with httpx.AsyncClient(timeout=GDELT_TIMEOUT) as client:
                resp = await client.get(self._base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("GDELT API HTTP error: %s", e.response.status_code)
            return []
        except Exception:
            logger.exception("GDELT API request failed")
            return []

        articles: list[dict[str, Any]] = []
        for item in data.get("articles", []):
            articles.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "language": item.get("language", ""),
                "country": item.get("sourcecountry", ""),
                "seendate": item.get("seendate", ""),
                "domain": item.get("domain", ""),
                "socialimage": item.get("socialimage", ""),
            })

        logger.info("GDELT returned %d articles for query: %s", len(articles), query)
        return articles

    async def monitor_pl_ua(
        self,
        keywords: list[str] | None = None,
        timespan: str = "15min",
        max_per_country: int = 25,
    ) -> dict[str, list[dict[str, Any]]]:
        """Monitor Polish and Ukrainian news streams.

        Args:
            keywords: Optional filter keywords (default: broad monitoring)
            timespan: Time window for monitoring
            max_per_country: Max articles per country

        Returns:
            Dict with keys 'PL' and 'UA', each containing article lists
        """
        if keywords is None:
            keywords = [""]  # Broad monitoring

        query = " OR ".join(keywords) if keywords else ""

        results: dict[str, list[dict[str, Any]]] = {"PL": [], "UA": []}

        # Polish news
        pl_articles = await self.search_articles(
            query=query,
            source_country="PL",
            source_language="Polish",
            max_records=max_per_country,
            timespan=timespan,
        )
        results["PL"] = pl_articles

        # Ukrainian news
        ua_articles = await self.search_articles(
            query=query,
            source_country="UA",
            source_language="Ukrainian",
            max_records=max_per_country,
            timespan=timespan,
        )
        results["UA"] = ua_articles

        logger.info(
            "GDELT PL/UA monitoring: %d PL articles, %d UA articles",
            len(results["PL"]),
            len(results["UA"]),
        )
        return results

    async def get_article_urls(
        self,
        query: str = "",
        countries: list[str] | None = None,
        timespan: str = "1h",
        max_records: int = 50,
    ) -> list[str]:
        """Get article URLs for processing by Trafilatura.

        Convenience method that returns just URLs (no metadata).
        """
        if countries is None:
            countries = ["PL", "UA"]

        urls: list[str] = []
        for country in countries:
            articles = await self.search_articles(
                query=query,
                source_country=country,
                max_records=max_records // len(countries),
                timespan=timespan,
            )
            urls.extend(a["url"] for a in articles if a.get("url"))

        return urls
