#!/usr/bin/env python
"""Branch lease manager (distinct from handoff claim TTL leases)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from metagit.core.coordination.branch_service import BranchService
from metagit.core.coordination.event_store import AclEventStore
from metagit.core.coordination.models import Lease, LeaseListResult
from metagit.core.coordination.paths import leases_file
from metagit.core.coordination.repo_lock_service import RepoLockRegistry
from metagit.core.coordination.store import JsonListStore
from metagit.core.coordination.ttl import parse_ttl_seconds
from metagit.core.workspace.context_models import utc_now_iso

DEFAULT_LEASE_TTL = "30m"


class LeaseService:
    """Acquire, renew, release, and list ACL branch leases."""

    def __init__(
        self,
        session_root: str,
        *,
        sync_root: str | None = None,
        definition_path: str | None = None,
        branch_service: BranchService | None = None,
        now_fn: Callable[[], str] | None = None,
        clock_fn: Callable[[], datetime] | None = None,
        event_store: AclEventStore | None = None,
        repo_lock: RepoLockRegistry | None = None,
    ) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())
        self._sync_root = str(Path(sync_root or session_root).expanduser().resolve())
        self._definition_path = definition_path
        self._now = now_fn or utc_now_iso
        self._clock = clock_fn or (lambda: datetime.now(timezone.utc))
        self._events = event_store or AclEventStore(self._session_root)
        self._branches = branch_service or BranchService(
            self._session_root,
            sync_root=self._sync_root,
            definition_path=self._definition_path,
            now_fn=self._now,
            event_store=self._events,
        )
        self._repo_lock = repo_lock or RepoLockRegistry(self._session_root, now_fn=self._now)
        self._store: JsonListStore[Lease] = JsonListStore(
            leases_file(self._session_root),
            key="leases",
            model=Lease,
        )

    def list(
        self,
        *,
        repository: Optional[str] = None,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> LeaseListResult | Exception:
        rows = self._expire_leases()
        if isinstance(rows, Exception):
            return rows
        if repository:
            rows = [row for row in rows if row.repository == repository]
        if status:
            rows = [row for row in rows if row.status == status]
        if agent_id:
            rows = [row for row in rows if row.agent_id == agent_id]
        presence = self._repo_lock.list(repository=repository)
        if isinstance(presence, Exception):
            return presence
        return LeaseListResult(leases=rows, presence=presence)

    def acquire(
        self,
        *,
        repository: str,
        agent_id: str,
        task_id: str,
        branch: Optional[str] = None,
        branch_id: Optional[str] = None,
        ttl: str = DEFAULT_LEASE_TTL,
        allocate_if_missing: bool = False,
        description: Optional[str] = None,
        integration_branch: Optional[str] = None,
        base: Optional[str] = None,
    ) -> Lease | Exception:
        rows = self._expire_leases()
        if isinstance(rows, Exception):
            return rows

        allocation = None
        if branch_id:
            allocation = self._branches.get(branch_id=branch_id)
        elif branch:
            allocation = self._branches.get(name=branch, repository=repository)
        if isinstance(allocation, Exception):
            return allocation

        if allocation is None and allocate_if_missing:
            allocation = self._branches.allocate(
                repository=repository,
                agent_id=agent_id,
                task_id=task_id,
                description=description,
                branch_name=branch,
                base=base,
                integration_branch=integration_branch,
            )
            if isinstance(allocation, Exception):
                return allocation
        if allocation is None:
            return ValueError(
                "branch allocation required; pass --branch/--branch-id or --allocate",
            )
        if allocation.status != "allocated":
            return ValueError(
                f"branch {allocation.name} is not allocated (status={allocation.status})",
            )
        if allocation.repository != repository:
            return ValueError("repository does not match branch allocation")

        for row in rows:
            if (
                row.status == "active"
                and row.repository == repository
                and row.branch == allocation.name
                and row.agent_id != agent_id
            ):
                return ValueError(
                    f"branch already leased by {row.agent_id} (lease_id={row.lease_id})",
                )
            if (
                row.status == "active"
                and row.repository == repository
                and row.branch == allocation.name
                and row.agent_id == agent_id
            ):
                # Renew in place for same owner.
                return self.renew(lease_id=row.lease_id, agent_id=agent_id, ttl=ttl)

        try:
            ttl_seconds = parse_ttl_seconds(ttl)
        except ValueError as exc:
            return exc

        now_dt = self._clock()
        created = self._now()
        expires = (now_dt + timedelta(seconds=ttl_seconds)).isoformat()
        lease = Lease(
            lease_id=uuid.uuid4().hex,
            branch=allocation.name,
            repository=repository,
            agent_id=agent_id.strip(),
            task_id=task_id.strip(),
            created=created,
            expires=expires,
            status="active",
            branch_id=allocation.branch_id,
        )

        def _mutate(current: list[Lease]) -> list[Lease]:
            for row in current:
                if (
                    row.status == "active"
                    and row.repository == repository
                    and row.branch == allocation.name
                    and row.agent_id != agent_id
                ):
                    raise ValueError(
                        f"branch already leased by {row.agent_id}",
                    )
            current.append(lease)
            return current

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result

        registered = self._repo_lock.register(repository, agent_id)
        if isinstance(registered, Exception):
            return registered

        self._events.append(
            "LeaseGranted",
            {
                "lease_id": lease.lease_id,
                "branch": lease.branch,
                "repository": repository,
                "agent_id": agent_id,
                "task_id": task_id,
                "expires": expires,
            },
            at=created,
        )
        return lease

    def renew(
        self,
        *,
        lease_id: str,
        agent_id: str,
        ttl: str = DEFAULT_LEASE_TTL,
        force: bool = False,
    ) -> Lease | Exception:
        rows = self._expire_leases()
        if isinstance(rows, Exception):
            return rows
        try:
            ttl_seconds = parse_ttl_seconds(ttl)
        except ValueError as exc:
            return exc
        now_dt = self._clock()
        expires = (now_dt + timedelta(seconds=ttl_seconds)).isoformat()
        now = self._now()
        updated_holder: list[Lease] = []

        def _mutate(current: list[Lease]) -> list[Lease]:
            idx = next((i for i, row in enumerate(current) if row.lease_id == lease_id), None)
            if idx is None:
                raise ValueError(f"lease not found: {lease_id}")
            row = current[idx]
            if row.status != "active":
                raise ValueError(f"lease is not active: {row.status}")
            if row.agent_id != agent_id and not force:
                raise ValueError(f"lease owned by {row.agent_id}")
            updated = row.model_copy(update={"expires": expires})
            current[idx] = updated
            updated_holder.append(updated)
            return current

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        if not updated_holder:
            return ValueError(f"lease not found: {lease_id}")
        _ = now
        return updated_holder[0]

    def release(
        self,
        *,
        lease_id: str,
        agent_id: str,
        force: bool = False,
        release_branch: bool = False,
    ) -> Lease | Exception:
        rows = self._expire_leases()
        if isinstance(rows, Exception):
            return rows
        now = self._now()
        updated_holder: list[Lease] = []

        def _mutate(current: list[Lease]) -> list[Lease]:
            idx = next((i for i, row in enumerate(current) if row.lease_id == lease_id), None)
            if idx is None:
                raise ValueError(f"lease not found: {lease_id}")
            row = current[idx]
            if row.agent_id != agent_id and not force:
                raise ValueError(f"lease owned by {row.agent_id}")
            updated = row.model_copy(update={"status": "released"})
            current[idx] = updated
            updated_holder.append(updated)
            return current

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        if not updated_holder:
            return ValueError(f"lease not found: {lease_id}")
        lease = updated_holder[0]
        self._repo_lock.deregister(lease.repository, lease.agent_id)
        # Spec event vocabulary has LeaseGranted/LeaseExpired (no LeaseReleased).
        self._events.append(
            "LeaseExpired",
            {
                "lease_id": lease.lease_id,
                "branch": lease.branch,
                "repository": lease.repository,
                "agent_id": lease.agent_id,
                "reason": "released",
            },
            at=now,
        )
        if release_branch:
            self._branches.release(
                branch_id=lease.branch_id,
                name=lease.branch,
                repository=lease.repository,
            )
        return lease

    def active_branch_keys(self) -> set[tuple[str, str]] | Exception:
        rows = self._expire_leases()
        if isinstance(rows, Exception):
            return rows
        return {(row.repository, row.branch) for row in rows if row.status == "active"}

    def get_active(
        self,
        *,
        repository: str,
        branch: str,
        agent_id: str,
    ) -> Lease | None | Exception:
        rows = self._expire_leases()
        if isinstance(rows, Exception):
            return rows
        for row in rows:
            if (
                row.status == "active"
                and row.repository == repository
                and row.branch == branch
                and row.agent_id == agent_id
            ):
                return row
        return None

    def _expire_leases(self) -> list[Lease] | Exception:
        loaded = self._store.load()
        if isinstance(loaded, Exception):
            return loaded
        now_dt = self._clock()
        changed = False
        updated: list[Lease] = []
        for row in loaded:
            if row.status != "active":
                updated.append(row)
                continue
            try:
                expires = datetime.fromisoformat(row.expires.replace("Z", "+00:00"))
            except ValueError:
                updated.append(row)
                continue
            if expires > now_dt:
                updated.append(row)
                continue
            expired = row.model_copy(update={"status": "expired"})
            updated.append(expired)
            changed = True
            self._events.append(
                "LeaseExpired",
                {
                    "lease_id": row.lease_id,
                    "branch": row.branch,
                    "repository": row.repository,
                    "agent_id": row.agent_id,
                    "reason": "expired",
                },
            )
            self._repo_lock.deregister(row.repository, row.agent_id)
        if changed:
            saved = self._store.save(updated)
            if isinstance(saved, Exception):
                return saved
        return updated


__all__ = ["DEFAULT_LEASE_TTL", "LeaseService"]
