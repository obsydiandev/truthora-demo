"""Google Fact Check Tools API client."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GOOGLE_FC_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class GoogleFactCheckClient:
    """Client for Google Fact Check Tools API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("GOOGLE_FC_API_KEY", "")

    async def search(
        self,
        query: str,
        language_code: str = "en",
        max_age_days: int | None = None,
        page_size: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for fact-checks related to a claim text.

        Returns a list of ClaimReview-style results with keys:
          - claim_text, claimant, claim_date
          - review_title, review_url, review_publisher
          - textual_rating, rating_value
          - language_code
        """
        if not self._api_key:
            logger.warning("GOOGLE_FC_API_KEY not set — skipping Google FC search")
            return []

        params: dict[str, Any] = {
            "key": self._api_key,
            "query": query,
            "languageCode": language_code,
            "pageSize": page_size,
        }
        if max_age_days is not None:
            params["maxAgeDays"] = max_age_days

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(GOOGLE_FC_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Google FC API HTTP error: %s", e.response.status_code)
            return []
        except Exception:
            logger.exception("Google FC API request failed")
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("claims", []):
            claim_review = item.get("claimReview", [{}])[0] if item.get("claimReview") else {}
            publisher = claim_review.get("publisher", {})
            results.append({
                "claim_text": item.get("text", ""),
                "claimant": item.get("claimant"),
                "claim_date": item.get("claimDate"),
                "review_title": claim_review.get("title", ""),
                "review_url": claim_review.get("url", ""),
                "review_publisher": publisher.get("name", ""),
                "textual_rating": claim_review.get("textualRating", ""),
                "language_code": claim_review.get("languageCode", language_code),
            })

        return results

    async def search_all(
        self,
        language_code: str = "en",
        max_pages: int = 10,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all recent fact-checks without a topic filter, using pagination.

        Uses empty query to get the latest fact-checks across all topics.
        max_pages × page_size = total results (default: 10 × 100 = 1000).
        """
        if not self._api_key:
            logger.warning("GOOGLE_FC_API_KEY not set — skipping Google FC search")
            return []

        all_results: list[dict[str, Any]] = []
        page_token: str | None = None

        for _ in range(max_pages):
            params: dict[str, Any] = {
                "key": self._api_key,
                "languageCode": language_code,
                "pageSize": page_size,
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(GOOGLE_FC_API_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("Google FC API HTTP error: %s", e.response.status_code)
                break
            except Exception:
                logger.exception("Google FC API request failed")
                break

            for item in data.get("claims", []):
                claim_review = item.get("claimReview", [{}])[0] if item.get("claimReview") else {}
                publisher = claim_review.get("publisher", {})
                all_results.append({
                    "claim_text": item.get("text", ""),
                    "claimant": item.get("claimant"),
                    "claim_date": item.get("claimDate"),
                    "review_title": claim_review.get("title", ""),
                    "review_url": claim_review.get("url", ""),
                    "review_publisher": publisher.get("name", ""),
                    "textual_rating": claim_review.get("textualRating", ""),
                    "language_code": claim_review.get("languageCode", language_code),
                })

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_results
