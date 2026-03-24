"""Truthora — Text extraction via Trafilatura.

Wraps Trafilatura to extract clean text from a URL,
returning the article body, title, and detected language.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import trafilatura

logger = logging.getLogger(__name__)


async def extract_text(url: str) -> Optional[dict[str, Any]]:
    """Download and extract clean text from a URL.

    Returns a dict with keys: text, title, language, url
    or None if extraction fails.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            logger.warning("Could not download URL: %s", url)
            return None

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=False,
            deduplicate=True,
        )
        if not text:
            logger.warning("No text extracted from URL: %s", url)
            return None

        metadata = trafilatura.extract(
            downloaded,
            output_format="json",
            include_comments=False,
        )

        title = None
        language = None
        if metadata:
            import json

            try:
                meta_dict = json.loads(metadata)
                title = meta_dict.get("title")
                language = meta_dict.get("language")
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "text": text,
            "title": title,
            "language": language,
            "url": url,
        }
    except Exception:
        logger.exception("Error extracting text from %s", url)
        return None
