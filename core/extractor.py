"""Text extraction via Trafilatura."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any, Optional
from urllib.parse import urlparse

import trafilatura

logger = logging.getLogger(__name__)

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_safe_url(url: str) -> bool:
    """Block requests to private/internal networks (SSRF protection)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in infos:
            ip = ipaddress.ip_address(sockaddr[0])
            if any(ip in net for net in _BLOCKED_NETWORKS):
                return False
    except (socket.gaierror, ValueError):
        return False
    return True


async def extract_text(url: str) -> Optional[dict[str, Any]]:
    """Download and extract clean text from a URL.

    Returns a dict with keys: text, title, language, url
    or None if extraction fails.
    """
    try:
        if not _is_safe_url(url):
            logger.warning("Blocked URL (SSRF protection): %s", url)
            return None

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
