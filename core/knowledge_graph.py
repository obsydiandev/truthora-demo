"""Truthora — Knowledge Graph verification via spaCy NER + DBpedia SPARQL.

Implements Layer 3 of the pipeline:
  1. Extract named entities from claim text using spaCy (PER/ORG/GPE)
  2. Query DBpedia via one-hop SPARQL to verify entity facts
  3. Return: KG_FOUND (triples) | KG_NOT_FOUND | KG_MISMATCH ⚠️

KG_NOT_FOUND does not block the pipeline — it's informational only.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from api.schemas import KGSignal

logger = logging.getLogger(__name__)

DBPEDIA_SPARQL_URL = "https://dbpedia.org/sparql"
SPARQL_TIMEOUT = 10

# spaCy model — lazy loaded
_nlp = None


def _get_nlp():
    """Lazy-load spaCy model for NER."""
    global _nlp
    if _nlp is not None:
        return _nlp

    try:
        import spacy

        _nlp = spacy.load("xx_ent_wiki_sm")
        logger.info("spaCy NER model loaded: xx_ent_wiki_sm")
    except OSError:
        logger.warning(
            "spaCy model 'xx_ent_wiki_sm' not installed. "
            "Install with: python -m spacy download xx_ent_wiki_sm"
        )
        _nlp = None
    except Exception:
        logger.exception("Failed to load spaCy NER model")
        _nlp = None

    return _nlp


@dataclass
class Entity:
    """A named entity extracted from claim text."""

    text: str
    label: str  # PER, ORG, GPE


@dataclass
class KGTriple:
    """A knowledge graph triple from DBpedia."""

    subject: str
    predicate: str
    obj: str


@dataclass
class KGResult:
    """Result of Knowledge Graph verification for a claim."""

    signal: KGSignal
    entities: list[Entity] = field(default_factory=list)
    triples: list[KGTriple] = field(default_factory=list)
    details: str = ""


def extract_entities(text: str) -> list[Entity]:
    """Extract named entities (PER/ORG/GPE) from claim text using spaCy.

    Returns an empty list if spaCy model is not available.
    """
    nlp = _get_nlp()
    if nlp is None:
        return []

    doc = nlp(text)
    entities: list[Entity] = []
    seen: set[str] = set()

    for ent in doc.ents:
        if ent.label_ in ("PER", "ORG", "GPE") and ent.text not in seen:
            entities.append(Entity(text=ent.text, label=ent.label_))
            seen.add(ent.text)

    return entities


def _entity_to_dbpedia_uri(entity_text: str) -> str:
    """Convert entity text to a DBpedia resource URI.

    Replaces spaces with underscores for DBpedia resource naming convention.
    """
    cleaned = entity_text.strip().replace(" ", "_")
    # Remove characters that aren't word chars or underscores (preserve Unicode letters)
    cleaned = re.sub(r"[^\w_]", "", cleaned, flags=re.UNICODE)
    return f"http://dbpedia.org/resource/{cleaned}"


def _build_one_hop_query(entity_uri: str) -> str:
    """Build a one-hop SPARQL query to retrieve triples about an entity."""
    return f"""
    SELECT ?predicate ?object
    WHERE {{
        <{entity_uri}> ?predicate ?object .
        FILTER(
            ?predicate = <http://dbpedia.org/ontology/office> ||
            ?predicate = <http://dbpedia.org/ontology/country> ||
            ?predicate = <http://dbpedia.org/ontology/birthPlace> ||
            ?predicate = <http://dbpedia.org/ontology/deathPlace> ||
            ?predicate = <http://dbpedia.org/ontology/leader> ||
            ?predicate = <http://dbpedia.org/ontology/capital> ||
            ?predicate = <http://dbpedia.org/ontology/populationTotal> ||
            ?predicate = <http://dbpedia.org/ontology/foundingDate> ||
            ?predicate = <http://dbpedia.org/ontology/dissolutionDate> ||
            ?predicate = <http://dbpedia.org/ontology/president> ||
            ?predicate = <http://dbpedia.org/ontology/primeMinister> ||
            ?predicate = <http://dbpedia.org/property/title> ||
            ?predicate = <http://dbpedia.org/property/office> ||
            ?predicate = <http://www.w3.org/2000/01/rdf-schema#label>
        )
    }}
    LIMIT 20
    """


async def query_dbpedia(entity_text: str) -> list[KGTriple]:
    """Query DBpedia SPARQL endpoint for triples about an entity.

    Returns a list of KGTriple objects. Returns empty list on failure.
    """
    entity_uri = _entity_to_dbpedia_uri(entity_text)
    sparql = _build_one_hop_query(entity_uri)

    try:
        async with httpx.AsyncClient(timeout=SPARQL_TIMEOUT) as client:
            resp = await client.get(
                DBPEDIA_SPARQL_URL,
                params={
                    "query": sparql,
                    "format": "application/sparql-results+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("DBpedia SPARQL HTTP error for '%s': %s", entity_text, e.response.status_code)
        return []
    except Exception:
        logger.exception("DBpedia SPARQL query failed for '%s'", entity_text)
        return []

    triples: list[KGTriple] = []
    for binding in data.get("results", {}).get("bindings", []):
        predicate = binding.get("predicate", {}).get("value", "")
        obj = binding.get("object", {}).get("value", "")
        if predicate and obj:
            # Extract short predicate name
            pred_short = predicate.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            # Extract short object name for URIs
            obj_short = obj.rsplit("/", 1)[-1] if obj.startswith("http") else obj
            triples.append(KGTriple(
                subject=entity_text,
                predicate=pred_short,
                obj=obj_short,
            ))

    return triples


async def verify_claim_kg(claim_text: str) -> KGResult:
    """Verify a claim against Knowledge Graph (DBpedia).

    Pipeline:
      1. Extract entities (PER/ORG/GPE) via spaCy NER
      2. For each entity, perform one-hop SPARQL query
      3. Return aggregated signal: KG_FOUND / KG_NOT_FOUND / KG_MISMATCH

    KG_NOT_FOUND does not block the pipeline.
    """
    entities = extract_entities(claim_text)

    if not entities:
        return KGResult(
            signal=KGSignal.KG_NOT_FOUND,
            details="No named entities found in claim text",
        )

    all_triples: list[KGTriple] = []
    for entity in entities:
        triples = await query_dbpedia(entity.text)
        all_triples.extend(triples)

    if not all_triples:
        return KGResult(
            signal=KGSignal.KG_NOT_FOUND,
            entities=entities,
            details=f"No DBpedia triples found for entities: {[e.text for e in entities]}",
        )

    # Check for mismatches — basic heuristic:
    # Look for office/title triples that might contradict the claim
    claim_lower = claim_text.lower()
    has_mismatch = False
    mismatch_details: list[str] = []

    for triple in all_triples:
        pred_lower = triple.predicate.lower()
        # Check if claim mentions a role/office that contradicts KG
        if pred_lower in ("office", "title", "president", "primeminister"):
            obj_readable = triple.obj.replace("_", " ").lower()
            # If claim mentions a different role for same entity
            subject_lower = triple.subject.lower()
            if subject_lower in claim_lower:
                # Check common role words
                role_words = ["president", "prime minister", "minister", "mayor", "ceo", "director",
                              "prezydent", "premier", "burmistrz", "президент", "прем'єр"]
                for role in role_words:
                    if role in claim_lower and role not in obj_readable:
                        has_mismatch = True
                        mismatch_details.append(
                            f"KG: {triple.subject} → {triple.predicate} → {triple.obj}"
                        )

    if has_mismatch:
        return KGResult(
            signal=KGSignal.KG_MISMATCH,
            entities=entities,
            triples=all_triples,
            details=f"⚠️ Potential mismatch: {'; '.join(mismatch_details)}",
        )

    return KGResult(
        signal=KGSignal.KG_FOUND,
        entities=entities,
        triples=all_triples,
        details=f"Found {len(all_triples)} triples for {len(entities)} entities",
    )


def kg_signal_to_score(signal: KGSignal) -> float:
    """Convert KG signal to a numeric score for the scoring pipeline.

    KG_FOUND:     1.0 (strong positive signal)
    KG_NOT_FOUND: 0.5 (neutral — no info)
    KG_MISMATCH:  0.0 (negative signal — potential contradiction)
    """
    if signal == KGSignal.KG_FOUND:
        return 1.0
    elif signal == KGSignal.KG_NOT_FOUND:
        return 0.5
    else:  # KG_MISMATCH
        return 0.0
