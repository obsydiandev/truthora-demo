"""Truthora — Claim detection via LLM (atomic claim decomposition).

Uses Llama 3.1 8B (via Groq or Ollama) to:
  1. Decompose text into atomic, verifiable claims
  2. Pin each claim to a verbatim source quote with char offsets
  3. Preserve negation particles (nie/brak/żaden / not/no / не/ні)
  4. Score each claim on 5 checkworthiness dimensions
"""

from __future__ import annotations

import logging
from typing import Any

from api.schemas import CheckworthinessScore, Claim
from services.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are Truthora — a multilingual fact-checking assistant.
Your job is to extract atomic, verifiable claims from news text.

Rules:
1. Decompose compound sentences into separate atomic claims (one fact = one claim).
2. For each claim, provide the EXACT verbatim quote from the source text and its
   character positions (char_start, char_end).
3. PRESERVE ALL negation particles verbatim (nie, brak, żaden / not, no / не, ні).
   Claims differing only in negation are DIFFERENT claims.
4. Score each claim on 5 checkworthiness dimensions (0.0 to 1.0):
   - harm_potential: Could falsehood cause harm?
   - virality_potential: Could it spread rapidly?
   - verifiability: Is it concretely verifiable?
   - specificity: Is it a factual statement (not opinion)?
   - public_interest: Does it concern public decisions?

Respond ONLY with valid JSON — an array of claim objects:
[
  {
    "claim_text": "...",
    "source_quote": "...",
    "char_start": 0,
    "char_end": 50,
    "language": "en",
    "has_negation": false,
    "checkworthiness": {
      "harm_potential": 0.5,
      "virality_potential": 0.3,
      "verifiability": 0.8,
      "specificity": 0.7,
      "public_interest": 0.4
    }
  }
]
"""

# Checkworthiness dimension weights
CW_WEIGHTS = {
    "harm_potential": 0.35,
    "virality_potential": 0.25,
    "verifiability": 0.20,
    "specificity": 0.12,
    "public_interest": 0.08,
}


def _compute_composite(scores: dict[str, float]) -> float:
    """Compute weighted composite checkworthiness score."""
    return sum(scores.get(dim, 0.0) * w for dim, w in CW_WEIGHTS.items())


class ClaimDetector:
    """Extract atomic claims from text using an LLM."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def detect_claims(
        self,
        text: str,
        language: str = "en",
    ) -> list[Claim]:
        """Detect atomic claims in the given text.

        Returns a list of Claim objects with checkworthiness scores.
        """
        prompt = (
            f"Language of the text: {language}\n\n"
            f"TEXT:\n{text}\n\n"
            "Extract all verifiable atomic claims from the text above."
        )

        try:
            raw: list[dict[str, Any]] = await self._llm.generate_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.1,
            )
        except Exception:
            logger.exception("LLM claim detection failed")
            return []

        if not isinstance(raw, list):
            logger.error("LLM returned non-list response: %s", type(raw))
            return []

        claims: list[Claim] = []
        for item in raw:
            try:
                cw = item.get("checkworthiness", {})
                composite = _compute_composite(cw)
                claim = Claim(
                    claim_id="",  # assigned later
                    claim_text=item["claim_text"],
                    source_quote=item.get("source_quote", ""),
                    char_start=item.get("char_start", 0),
                    char_end=item.get("char_end", 0),
                    language=item.get("language", language),
                    has_negation=item.get("has_negation", False),
                    checkworthiness=CheckworthinessScore(
                        harm_potential=cw.get("harm_potential", 0.0),
                        virality_potential=cw.get("virality_potential", 0.0),
                        verifiability=cw.get("verifiability", 0.0),
                        specificity=cw.get("specificity", 0.0),
                        public_interest=cw.get("public_interest", 0.0),
                        composite=composite,
                    ),
                )
                claims.append(claim)
            except Exception:
                logger.warning("Skipping malformed claim item: %s", item)

        return claims
