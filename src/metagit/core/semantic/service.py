#!/usr/bin/env python
"""SemanticGraphService - declare, query, and resolve concept owners."""

from __future__ import annotations

import re
import uuid
from typing import Callable

from metagit.core.coordination.claim_service import patterns_overlap
from metagit.core.semantic.events import SemanticGraphEventStore
from metagit.core.semantic.models import (
    Concept,
    ConceptDeclareResult,
    ConceptOwnership,
    ConceptOwnershipSource,
    ConceptOwnersResult,
    ConceptQueryResult,
)
from metagit.core.semantic.store import SemanticGraphStore
from metagit.core.workspace.context_models import utc_now_iso

_SLUG_DROP_RE = re.compile(r"[^a-z0-9._-]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _slugify_concept(value: str) -> str:
    """Return a stable concept id from a human concept name."""
    spaced = _WHITESPACE_RE.sub("-", value.strip().lower())
    slug = _SLUG_DROP_RE.sub("", spaced).strip("-._")
    if not slug:
        raise ValueError("concept must produce a non-empty concept_id")
    return slug


class SemanticGraphService:
    """Declare and query semantic concept ownership within a session root."""

    def __init__(
        self,
        session_root: str,
        *,
        store: SemanticGraphStore | None = None,
        event_store: SemanticGraphEventStore | None = None,
        now_fn: Callable[[], str] | None = None,
    ) -> None:
        self._session_root = session_root
        self._store = store or SemanticGraphStore(session_root)
        self._events = event_store or SemanticGraphEventStore(session_root)
        self._now = now_fn or utc_now_iso

    def declare(
        self,
        concept: str,
        repository: str,
        patterns: list[str],
        *,
        symbol_hints: list[str] | None = None,
        source: ConceptOwnershipSource = "manual",
    ) -> ConceptDeclareResult | Exception:
        try:
            concept_id = _slugify_concept(concept)
        except ValueError as exc:
            return exc

        now = self._now()
        concept_row = Concept(
            concept_id=concept_id,
            name=concept.strip(),
            aliases=[],
            created_at=now,
            updated_at=now,
        )
        ownership = ConceptOwnership(
            ownership_id=uuid.uuid4().hex,
            concept_id=concept_id,
            repository=repository,
            patterns=list(patterns),
            symbol_hints=list(symbol_hints or []),
            source=source,
            created_at=now,
            updated_at=now,
        )

        saved_concepts = self._store.update_concepts(
            lambda rows: self._upsert_concept(rows, concept_row, now=now),
        )
        if isinstance(saved_concepts, Exception):
            return saved_concepts

        saved_ownerships = self._store.update_ownerships(lambda rows: [*rows, ownership])
        if isinstance(saved_ownerships, Exception):
            return saved_ownerships

        self._events.append(
            "ConceptDeclared",
            {
                "concept_id": concept_id,
                "repository": ownership.repository,
                "patterns": ownership.patterns,
                "ownership_id": ownership.ownership_id,
                "source": ownership.source,
            },
            at=now,
        )
        return ConceptDeclareResult(concept=concept_row, ownership=ownership)

    def query(self, concept: str) -> ConceptQueryResult | Exception:
        concepts = self._store.load_concepts()
        if isinstance(concepts, Exception):
            return concepts
        ownerships = self._store.load_ownerships()
        if isinstance(ownerships, Exception):
            return ownerships

        needle = concept.strip().lower()
        found = next((row for row in concepts if self._matches_concept(row, needle)), None)
        if found is None:
            return ConceptQueryResult(concept=None, ownerships=[])
        return ConceptQueryResult(
            concept=found,
            ownerships=[row for row in ownerships if row.concept_id == found.concept_id],
        )

    def owners(self, path: str, repository: str) -> ConceptOwnersResult | Exception:
        concepts = self._store.load_concepts()
        if isinstance(concepts, Exception):
            return concepts
        ownerships = self._store.load_ownerships()
        if isinstance(ownerships, Exception):
            return ownerships

        normalized_path = path.strip().lstrip("./")
        normalized_repo = repository.strip()
        matched_ownerships = [
            row
            for row in ownerships
            if row.repository == normalized_repo
            and any(patterns_overlap(normalized_path, pattern) for pattern in row.patterns)
        ]
        concept_ids = {row.concept_id for row in matched_ownerships}
        matched_concepts = [row for row in concepts if row.concept_id in concept_ids]
        return ConceptOwnersResult(
            path=normalized_path,
            repository=normalized_repo,
            concepts=matched_concepts,
            ownerships=matched_ownerships,
        )

    @staticmethod
    def _matches_concept(row: Concept, needle: str) -> bool:
        if row.concept_id.lower() == needle or row.name.lower() == needle:
            return True
        return any(alias.lower() == needle for alias in row.aliases)

    @staticmethod
    def _upsert_concept(rows: list[Concept], concept: Concept, *, now: str) -> list[Concept]:
        for index, row in enumerate(rows):
            if row.concept_id == concept.concept_id:
                rows[index] = row.model_copy(
                    update={
                        "name": concept.name,
                        "updated_at": now,
                    },
                )
                return rows
        rows.append(concept)
        return rows


__all__ = ["SemanticGraphService"]
