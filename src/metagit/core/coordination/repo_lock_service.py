#!/usr/bin/env python
"""Advisory per-repository agent presence registry."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from metagit.core.coordination.models import RepoAgentPresence
from metagit.core.coordination.paths import presence_file
from metagit.core.coordination.store import JsonListStore
from metagit.core.workspace.context_models import utc_now_iso


class RepoLockRegistry:
    """Track which agents are active in a repository (advisory, not exclusive)."""

    def __init__(
        self,
        session_root: str,
        *,
        now_fn: Callable[[], str] | None = None,
    ) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())
        self._now = now_fn or utc_now_iso
        self._store: JsonListStore[RepoAgentPresence] = JsonListStore(
            presence_file(self._session_root),
            key="presence",
            model=RepoAgentPresence,
        )

    def list(
        self,
        *,
        repository: Optional[str] = None,
    ) -> list[RepoAgentPresence] | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        if repository:
            rows = [row for row in rows if row.repository == repository]
        return rows

    def register(self, repository: str, agent_id: str) -> RepoAgentPresence | Exception:
        now = self._now()
        agent = agent_id.strip()
        updated_holder: list[RepoAgentPresence] = []

        def _mutate(rows: list[RepoAgentPresence]) -> list[RepoAgentPresence]:
            for idx, row in enumerate(rows):
                if row.repository == repository:
                    agents = list(row.agent_ids)
                    if agent not in agents:
                        agents.append(agent)
                    updated = row.model_copy(
                        update={"agent_ids": agents, "updated_at": now},
                    )
                    rows[idx] = updated
                    updated_holder.append(updated)
                    return rows
            created = RepoAgentPresence(
                repository=repository,
                agent_ids=[agent],
                updated_at=now,
            )
            rows.append(created)
            updated_holder.append(created)
            return rows

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        return updated_holder[0]

    def deregister(
        self,
        repository: str,
        agent_id: str,
    ) -> RepoAgentPresence | None | Exception:
        now = self._now()
        agent = agent_id.strip()
        updated_holder: list[RepoAgentPresence | None] = []

        def _mutate(rows: list[RepoAgentPresence]) -> list[RepoAgentPresence]:
            remaining: list[RepoAgentPresence] = []
            found: RepoAgentPresence | None = None
            for row in rows:
                if row.repository != repository:
                    remaining.append(row)
                    continue
                agents = [item for item in row.agent_ids if item != agent]
                if agents:
                    updated = row.model_copy(
                        update={"agent_ids": agents, "updated_at": now},
                    )
                    remaining.append(updated)
                    found = updated
                else:
                    found = None
            updated_holder.append(found)
            return remaining

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        return updated_holder[0] if updated_holder else None


__all__ = ["RepoLockRegistry"]
