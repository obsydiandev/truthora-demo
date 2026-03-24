"""Truthora — Text normalization: Unicode NFC + negation detection.

Ensures consistent text representation and detects negation particles
across supported languages (EN, PL, UA).
"""

from __future__ import annotations

import re
import unicodedata

from api.schemas import Claim

# Negation particles by language
NEGATION_PATTERNS: dict[str, list[str]] = {
    "en": ["not", "no", "never", "neither", "nor", "nobody", "nothing", "nowhere", "don't", "doesn't", "didn't", "won't", "wouldn't", "can't", "cannot", "isn't", "aren't", "wasn't", "weren't"],
    "pl": ["nie", "brak", "żaden", "żadna", "żadne", "nigdy", "nigdzie", "nikt", "nic", "bez"],
    "ua": ["не", "ні", "ніколи", "ніде", "ніхто", "ніщо", "без", "жоден", "жодна", "жодне"],
}

# Compile a regex for each language (word boundaries)
_NEGATION_REGEXES: dict[str, re.Pattern[str]] = {}
for _lang, _particles in NEGATION_PATTERNS.items():
    _escaped = [re.escape(p) for p in _particles]
    _NEGATION_REGEXES[_lang] = re.compile(
        r"\b(" + "|".join(_escaped) + r")\b",
        re.IGNORECASE,
    )


def normalize_text(text: str) -> str:
    """Apply Unicode NFC normalization and strip excess whitespace."""
    normalized = unicodedata.normalize("NFC", text)
    # Collapse multiple spaces/newlines
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def has_negation(text: str, language: str = "en") -> bool:
    """Check if the text contains negation particles for the given language.

    Falls back to checking all languages if the specified language is not found.
    """
    lang = language.lower()[:2]
    if lang in _NEGATION_REGEXES:
        return bool(_NEGATION_REGEXES[lang].search(text))

    # Fallback: check all languages
    return any(regex.search(text) for regex in _NEGATION_REGEXES.values())


def normalize_claims(claims: list[Claim]) -> list[Claim]:
    """Normalize claim text and detect negation for each claim."""
    for claim in claims:
        claim.claim_text = normalize_text(claim.claim_text)
        claim.source_quote = normalize_text(claim.source_quote)
        # Re-check negation after normalization
        claim.has_negation = has_negation(claim.claim_text, claim.language)
    return claims
