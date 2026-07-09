#!/usr/bin/env python
"""JSON persistence for semantic concepts and ownerships."""

from __future__ import annotations

from typing import Callable

from metagit.core.coordination.store import JsonListStore
from metagit.core.semantic.models import Concept, ConceptOwnership
from metagit.core.semantic.paths import concepts_file, graph_root, ownerships_file


class SemanticGraphStore:
    """Load and save semantic graph documents under ``.metagit/graph/``."""

    def __init__(self, session_root: str) -> None:
        self._session_root = session_root
        self._concepts: JsonListStore[Concept] = JsonListStore(
            concepts_file(session_root),
            key="concepts",
            model=Concept,
        )
        self._ownerships: JsonListStore[ConceptOwnership] = JsonListStore(
            ownerships_file(session_root),
            key="ownerships",
            model=ConceptOwnership,
        )

    def ensure_dirs(self) -> None:
        """Create the semantic graph directory if needed."""
        graph_root(self._session_root).mkdir(parents=True, exist_ok=True)

    def load_concepts(self) -> list[Concept] | Exception:
        """Load concept rows from ``concepts.json``."""
        return self._concepts.load()

    def save_concepts(self, concepts: list[Concept]) -> None | Exception:
        """Save concept rows to ``concepts.json``."""
        self.ensure_dirs()
        return self._concepts.save(concepts)

    def update_concepts(
        self,
        mutator: Callable[[list[Concept]], list[Concept]],
    ) -> list[Concept] | Exception:
        """Load, mutate, and save concept rows under a file lock."""
        self.ensure_dirs()
        return self._concepts.update(mutator)

    def load_ownerships(self) -> list[ConceptOwnership] | Exception:
        """Load ownership rows from ``ownerships.json``."""
        return self._ownerships.load()

    def save_ownerships(self, ownerships: list[ConceptOwnership]) -> None | Exception:
        """Save ownership rows to ``ownerships.json``."""
        self.ensure_dirs()
        return self._ownerships.save(ownerships)

    def update_ownerships(
        self,
        mutator: Callable[[list[ConceptOwnership]], list[ConceptOwnership]],
    ) -> list[ConceptOwnership] | Exception:
        """Load, mutate, and save ownership rows under a file lock."""
        self.ensure_dirs()
        return self._ownerships.update(mutator)


__all__ = ["SemanticGraphStore"]
