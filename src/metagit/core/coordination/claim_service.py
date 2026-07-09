#!/usr/bin/env python
"""Advisory file-path claim manager."""

from __future__ import annotations

import fnmatch
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Optional

from metagit.core.coordination.event_store import AclEventStore
from metagit.core.coordination.models import (
    ClaimCheckResult,
    ClaimConflict,
    ClaimListResult,
    FileClaim,
)
from metagit.core.coordination.paths import claims_file
from metagit.core.coordination.store import JsonListStore
from metagit.core.workspace.context_models import utc_now_iso


def patterns_overlap(left: str, right: str) -> bool:
    """Return True when two glob/prefix patterns may cover the same paths."""
    a = left.strip().lstrip("./")
    b = right.strip().lstrip("./")
    if not a or not b:
        return False
    if a == b:
        return True
    # Prefix-style: backend/auth/* overlaps backend/auth/token.py and backend/auth/**
    a_prefix = a[:-1] if a.endswith("*") else a
    b_prefix = b[:-1] if b.endswith("*") else b
    if a.endswith("*") and (b.startswith(a_prefix) or fnmatch.fnmatch(b, a)):
        return True
    if b.endswith("*") and (a.startswith(b_prefix) or fnmatch.fnmatch(a, b)):
        return True
    if fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
        return True
    # Directory containment without globs
    try:
        pa = PurePosixPath(a)
        pb = PurePosixPath(b)
        if (a in str(pb) or b in str(pa)) and (str(pb).startswith(str(pa) + "/") or str(pa).startswith(str(pb) + "/")):
            return True
    except ValueError:
        pass
    return False


class ClaimService:
    """Declare and check advisory file claims within a repository."""

    def __init__(
        self,
        session_root: str,
        *,
        now_fn: Callable[[], str] | None = None,
        event_store: AclEventStore | None = None,
    ) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())
        self._now = now_fn or utc_now_iso
        self._events = event_store or AclEventStore(self._session_root)
        self._store: JsonListStore[FileClaim] = JsonListStore(
            claims_file(self._session_root),
            key="claims",
            model=FileClaim,
        )

    def list(
        self,
        *,
        repository: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> ClaimListResult | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        if repository:
            rows = [row for row in rows if row.repository == repository]
        if agent_id:
            rows = [row for row in rows if row.agent_id == agent_id]
        if status:
            rows = [row for row in rows if row.status == status]
        return ClaimListResult(claims=rows)

    def check(
        self,
        *,
        repository: str,
        patterns: list[str],
        agent_id: Optional[str] = None,
    ) -> ClaimCheckResult | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        conflicts: list[ClaimConflict] = []
        for row in rows:
            if row.status != "active" or row.repository != repository:
                continue
            if agent_id and row.agent_id == agent_id:
                continue
            overlapping = [
                pattern for pattern in patterns if any(patterns_overlap(pattern, owned) for owned in row.patterns)
            ]
            if overlapping:
                conflicts.append(
                    ClaimConflict(
                        owner=row.agent_id,
                        files=overlapping,
                        claim_id=row.claim_id,
                    ),
                )
        concept_hints = self._concept_hints(repository=repository, patterns=patterns)
        return ClaimCheckResult(
            ok=not conflicts,
            conflicts=conflicts,
            concept_hints=concept_hints,
        )

    def _concept_hints(self, *, repository: str, patterns: list[str]) -> list[dict[str, Any]]:
        try:
            from metagit.core.semantic.service import SemanticGraphService

            result = SemanticGraphService(self._session_root).advise_claim_patterns(
                repository=repository,
                patterns=patterns,
            )
        except Exception as _:
            return []
        if isinstance(result, Exception):
            return []
        return result

    def declare(
        self,
        *,
        repository: str,
        agent_id: str,
        patterns: list[str],
        task_id: Optional[str] = None,
        allow_conflicts: bool = True,
    ) -> FileClaim | ClaimCheckResult | Exception:
        cleaned = [item.strip() for item in patterns if item.strip()]
        if not cleaned:
            return ValueError("at least one claim pattern is required")
        check = self.check(
            repository=repository,
            patterns=cleaned,
            agent_id=agent_id,
        )
        if isinstance(check, Exception):
            return check
        if check.conflicts:
            self._events.append(
                "ClaimConflict",
                {
                    "repository": repository,
                    "agent_id": agent_id,
                    "patterns": cleaned,
                    "conflicts": [c.model_dump(mode="json") for c in check.conflicts],
                },
            )
            if not allow_conflicts:
                return check

        now = self._now()
        claim = FileClaim(
            claim_id=uuid.uuid4().hex,
            repository=repository,
            agent_id=agent_id.strip(),
            patterns=cleaned,
            status="active",
            task_id=task_id,
            created_at=now,
            updated_at=now,
        )

        def _mutate(rows: list[FileClaim]) -> list[FileClaim]:
            rows.append(claim)
            return rows

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        self._events.append(
            "ClaimGranted",
            {
                "claim_id": claim.claim_id,
                "repository": repository,
                "agent_id": agent_id,
                "patterns": cleaned,
                "had_conflicts": bool(check.conflicts),
            },
            at=now,
        )
        return claim

    def release(
        self,
        *,
        claim_id: str,
        agent_id: str,
        force: bool = False,
    ) -> FileClaim | Exception:
        now = self._now()
        updated_holder: list[FileClaim] = []

        def _mutate(rows: list[FileClaim]) -> list[FileClaim]:
            idx = next((i for i, row in enumerate(rows) if row.claim_id == claim_id), None)
            if idx is None:
                raise ValueError(f"claim not found: {claim_id}")
            row = rows[idx]
            if row.agent_id != agent_id and not force:
                raise ValueError(f"claim owned by {row.agent_id}")
            updated = row.model_copy(
                update={"status": "released", "updated_at": now},
            )
            rows[idx] = updated
            updated_holder.append(updated)
            return rows

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        if not updated_holder:
            return ValueError(f"claim not found: {claim_id}")
        return updated_holder[0]


__all__ = ["ClaimService", "patterns_overlap"]
