#!/usr/bin/env python
"""SemanticGraphService - declare, query, and resolve concept owners."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

from pydantic import ValidationError

from metagit.core.coordination.claim_service import ClaimService, patterns_overlap
from metagit.core.semantic.events import SemanticGraphEventStore
from metagit.core.semantic.models import (
    Concept,
    ConceptConflictHint,
    ConceptConflictsResult,
    ConceptDeclareResult,
    ConceptOwnership,
    ConceptOwnershipSource,
    ConceptOwnersResult,
    ConceptQueryResult,
    SemanticIngestHints,
    SemanticIngestResult,
    SemanticSeedResult,
)
from metagit.core.semantic.paths import ingest_hints_file
from metagit.core.semantic.seed import SEED_CATALOG
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
        now = self._now()
        try:
            concept_id = _slugify_concept(concept)
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
        except (ValueError, ValidationError) as exc:
            return exc

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

    def seed(self, *, repository: str | None = None) -> SemanticSeedResult | Exception:
        """Seed the static concept catalog and optional repository ownerships."""
        now = self._now()
        try:
            concept_rows = [
                Concept(
                    concept_id=_slugify_concept(item.concept),
                    name=item.concept,
                    aliases=[],
                    created_at=now,
                    updated_at=now,
                )
                for item in SEED_CATALOG
            ]
            ownership_rows = (
                [
                    ConceptOwnership(
                        ownership_id=uuid.uuid4().hex,
                        concept_id=_slugify_concept(item.concept),
                        repository=repository,
                        patterns=list(item.patterns),
                        source="seed",
                        created_at=now,
                        updated_at=now,
                    )
                    for item in SEED_CATALOG
                ]
                if repository is not None
                else []
            )
        except (ValueError, ValidationError) as exc:
            return exc

        concepts_added = 0

        def _add_missing_concepts(rows: list[Concept]) -> list[Concept]:
            nonlocal concepts_added
            existing_ids = {row.concept_id for row in rows}
            for concept in concept_rows:
                if concept.concept_id in existing_ids:
                    continue
                rows.append(concept)
                existing_ids.add(concept.concept_id)
                concepts_added += 1
            return rows

        saved_concepts = self._store.update_concepts(_add_missing_concepts)
        if isinstance(saved_concepts, Exception):
            return saved_concepts

        ownerships_added = 0

        def _add_missing_ownerships(rows: list[ConceptOwnership]) -> list[ConceptOwnership]:
            nonlocal ownerships_added
            existing_keys = {self._ownership_key(row) for row in rows if row.source == "seed"}
            for ownership in ownership_rows:
                key = self._ownership_key(ownership)
                if key in existing_keys:
                    continue
                rows.append(ownership)
                existing_keys.add(key)
                ownerships_added += 1
            return rows

        if ownership_rows:
            saved_ownerships = self._store.update_ownerships(_add_missing_ownerships)
            if isinstance(saved_ownerships, Exception):
                return saved_ownerships

        return SemanticSeedResult(
            concepts_added=concepts_added,
            ownerships_added=ownerships_added,
        )

    def ingest(self) -> SemanticIngestResult | Exception:
        """Ingest deterministic semantic ownership hints if present."""
        path = ingest_hints_file(self._session_root)
        if not path.is_file():
            return SemanticIngestResult(reason="no_ingest_signals")

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            hints = SemanticIngestHints.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            return exc

        if not hints.ownerships:
            return SemanticIngestResult(reason="no_ingest_signals")

        now = self._now()
        try:
            concept_rows = [
                Concept(
                    concept_id=_slugify_concept(hint.concept),
                    name=hint.concept.strip(),
                    aliases=[],
                    created_at=now,
                    updated_at=now,
                )
                for hint in hints.ownerships
            ]
            ownership_rows = [
                ConceptOwnership(
                    ownership_id=uuid.uuid4().hex,
                    concept_id=_slugify_concept(hint.concept),
                    repository=hint.repository,
                    patterns=list(hint.patterns),
                    source="ingest",
                    created_at=now,
                    updated_at=now,
                )
                for hint in hints.ownerships
            ]
        except (ValueError, ValidationError) as exc:
            return exc

        concepts_added = 0

        def _add_missing_concepts(rows: list[Concept]) -> list[Concept]:
            nonlocal concepts_added
            existing_ids = {row.concept_id for row in rows}
            for concept in concept_rows:
                if concept.concept_id in existing_ids:
                    continue
                rows.append(concept)
                existing_ids.add(concept.concept_id)
                concepts_added += 1
            return rows

        saved_concepts = self._store.update_concepts(_add_missing_concepts)
        if isinstance(saved_concepts, Exception):
            return saved_concepts

        ownerships_added = 0
        skipped = 0
        ingested_ids: list[str] = []

        def _upsert_ingest_ownerships(rows: list[ConceptOwnership]) -> list[ConceptOwnership]:
            nonlocal ownerships_added, skipped
            existing_by_key = {
                self._ownership_key(row): index for index, row in enumerate(rows) if row.source == "ingest"
            }
            for ownership in ownership_rows:
                key = self._ownership_key(ownership)
                existing_index = existing_by_key.get(key)
                if existing_index is None:
                    rows.append(ownership)
                    existing_by_key[key] = len(rows) - 1
                    ingested_ids.append(ownership.ownership_id)
                    ownerships_added += 1
                    continue
                existing = rows[existing_index]
                merged_patterns = sorted({*existing.patterns, *ownership.patterns})
                if merged_patterns == sorted(existing.patterns):
                    skipped += 1
                    continue
                rows[existing_index] = existing.model_copy(
                    update={
                        "patterns": merged_patterns,
                        "updated_at": now,
                    },
                )
            return rows

        saved_ownerships = self._store.update_ownerships(_upsert_ingest_ownerships)
        if isinstance(saved_ownerships, Exception):
            return saved_ownerships

        if ownerships_added:
            self._events.append(
                "ConceptIngested",
                {
                    "added": ownerships_added,
                    "concepts_added": concepts_added,
                    "ownership_ids": ingested_ids,
                },
                at=now,
            )

        return SemanticIngestResult(
            added=ownerships_added,
            skipped=skipped,
            concepts_added=concepts_added,
            reason=None if ownerships_added else "no_ingest_signals",
        )

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

    def conflicts(self, repository: str) -> ConceptConflictsResult | Exception:
        concepts = self._store.load_concepts()
        if isinstance(concepts, Exception):
            return concepts
        ownerships = self._store.load_ownerships()
        if isinstance(ownerships, Exception):
            return ownerships
        claims = ClaimService(self._session_root).list(
            repository=repository,
            status="active",
        )
        if isinstance(claims, Exception):
            return claims

        concept_names = {row.concept_id: row.name for row in concepts}
        hints: list[ConceptConflictHint] = []
        normalized_repo = repository.strip()
        for concept_id in {row.concept_id for row in ownerships if row.repository == normalized_repo}:
            concept_ownerships = [
                row for row in ownerships if row.repository == normalized_repo and row.concept_id == concept_id
            ]
            overlapping_patterns: set[str] = set()
            claim_ids: set[str] = set()
            agent_ids: set[str] = set()
            for claim in claims.claims:
                matched_claim_patterns = [
                    claim_pattern
                    for claim_pattern in claim.patterns
                    if any(
                        patterns_overlap(claim_pattern, ownership_pattern)
                        for ownership in concept_ownerships
                        for ownership_pattern in ownership.patterns
                    )
                ]
                if not matched_claim_patterns:
                    continue
                overlapping_patterns.update(matched_claim_patterns)
                claim_ids.add(claim.claim_id)
                agent_ids.add(claim.agent_id)
            if len(agent_ids) < 2:
                continue
            hints.append(
                ConceptConflictHint(
                    concept_id=concept_id,
                    concept_name=concept_names.get(concept_id, concept_id),
                    repository=normalized_repo,
                    overlapping_patterns=sorted(overlapping_patterns),
                    claim_ids=sorted(claim_ids),
                    agent_ids=sorted(agent_ids),
                ),
            )

        result = ConceptConflictsResult(repository=normalized_repo, hints=hints)
        if hints:
            self._events.append(
                "ConceptConflictHint",
                {
                    "repository": normalized_repo,
                    "hints": [hint.model_dump(mode="json") for hint in hints],
                },
                at=self._now(),
            )
        return result

    def advise_claim_patterns(
        self,
        repository: str,
        patterns: list[str],
    ) -> list[dict[str, Any]] | Exception:
        """Return advisory concept hints for claim patterns in a repository."""
        concepts = self._store.load_concepts()
        if isinstance(concepts, Exception):
            return concepts
        ownerships = self._store.load_ownerships()
        if isinstance(ownerships, Exception):
            return ownerships

        concept_names = {row.concept_id: row.name for row in concepts}
        normalized_repo = repository.strip()
        hints: list[dict[str, Any]] = []
        for ownership in ownerships:
            if ownership.repository != normalized_repo:
                continue
            overlapping_patterns = sorted(
                {
                    claim_pattern
                    for claim_pattern in patterns
                    if any(
                        patterns_overlap(claim_pattern, ownership_pattern) for ownership_pattern in ownership.patterns
                    )
                },
            )
            if not overlapping_patterns:
                continue
            hints.append(
                {
                    "concept_id": ownership.concept_id,
                    "concept_name": concept_names.get(ownership.concept_id, ownership.concept_id),
                    "repository": normalized_repo,
                    "ownership_id": ownership.ownership_id,
                    "overlapping_patterns": overlapping_patterns,
                },
            )
        return hints

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

    @staticmethod
    def _ownership_key(row: ConceptOwnership) -> tuple[str, str, ConceptOwnershipSource]:
        return (row.concept_id, row.repository, row.source)


__all__ = ["SemanticGraphService"]
