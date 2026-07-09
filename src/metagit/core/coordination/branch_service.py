#!/usr/bin/env python
"""Branch allocation manager for agent/* execution branches."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable, Optional

from git import Repo
from git.exc import GitCommandError

from metagit.core.coordination.event_store import AclEventStore
from metagit.core.coordination.models import BranchAllocation, BranchListResult
from metagit.core.coordination.paths import branches_file
from metagit.core.coordination.repo_paths import (
    build_agent_branch_name,
    resolve_repo_filesystem_path,
)
from metagit.core.coordination.store import JsonListStore
from metagit.core.workspace.context_models import utc_now_iso


class BranchService:
    """Allocate, release, archive, and cleanup agent branches."""

    def __init__(
        self,
        session_root: str,
        *,
        sync_root: str | None = None,
        definition_path: str | None = None,
        now_fn: Callable[[], str] | None = None,
        event_store: AclEventStore | None = None,
    ) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())
        self._sync_root = str(
            Path(sync_root or session_root).expanduser().resolve(),
        )
        self._definition_path = definition_path
        self._now = now_fn or utc_now_iso
        self._events = event_store or AclEventStore(self._session_root)
        self._store: JsonListStore[BranchAllocation] = JsonListStore(
            branches_file(self._session_root),
            key="branches",
            model=BranchAllocation,
        )

    def list(
        self,
        *,
        repository: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BranchListResult | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        if repository:
            rows = [row for row in rows if row.repository == repository]
        if status:
            rows = [row for row in rows if row.status == status]
        return BranchListResult(branches=rows)

    def allocate(
        self,
        *,
        repository: str,
        agent_id: str,
        task_id: str,
        description: Optional[str] = None,
        branch_name: Optional[str] = None,
        base: Optional[str] = None,
        integration_branch: Optional[str] = None,
        create_git_branch: bool = True,
    ) -> BranchAllocation | Exception:
        name = branch_name or build_agent_branch_name(task_id, description)
        if not name.startswith("agent/"):
            return ValueError(f"branch name must start with agent/: {name!r}")

        existing = self._store.load()
        if isinstance(existing, Exception):
            return existing
        for row in existing:
            if row.repository == repository and row.name == name and row.status == "allocated":
                return ValueError(
                    f"branch already allocated: {name} in {repository} (owner={row.agent_id})",
                )

        repo_path: Path | None = None
        if create_git_branch:
            resolved = resolve_repo_filesystem_path(
                session_root=self._session_root,
                sync_root=self._sync_root,
                repository=repository,
                definition_path=self._definition_path,
            )
            if isinstance(resolved, Exception):
                return resolved
            repo_path = resolved
            try:
                git_repo = Repo(str(repo_path))
                base_ref = base or git_repo.head.commit.hexsha
                if name in [ref.name for ref in git_repo.heads]:
                    # Branch exists locally; allow allocation if not tracked as active.
                    pass
                else:
                    git_repo.create_head(name, commit=base_ref)
            except (GitCommandError, OSError, ValueError) as exc:
                return Exception(f"failed to create git branch {name}: {exc}")

        now = self._now()
        allocation = BranchAllocation(
            branch_id=uuid.uuid4().hex,
            name=name,
            repository=repository,
            agent_id=agent_id.strip(),
            task_id=task_id.strip(),
            integration_branch=integration_branch,
            status="allocated",
            base_ref=base,
            created_at=now,
            updated_at=now,
        )

        def _mutate(rows: list[BranchAllocation]) -> list[BranchAllocation]:
            for row in rows:
                if row.repository == repository and row.name == name and row.status == "allocated":
                    raise ValueError(
                        f"branch already allocated: {name} in {repository}",
                    )
            rows.append(allocation)
            return rows

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        self._events.append(
            "BranchAllocated",
            {
                "branch_id": allocation.branch_id,
                "name": allocation.name,
                "repository": repository,
                "agent_id": agent_id,
                "task_id": task_id,
            },
            at=now,
        )
        return allocation

    def release(
        self,
        *,
        branch_id: Optional[str] = None,
        name: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> BranchAllocation | Exception:
        return self._set_status(
            branch_id=branch_id,
            name=name,
            repository=repository,
            status="released",
            event_type="BranchReleased",
        )

    def archive(
        self,
        *,
        branch_id: Optional[str] = None,
        name: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> BranchAllocation | Exception:
        return self._set_status(
            branch_id=branch_id,
            name=name,
            repository=repository,
            status="archived",
            event_type=None,
        )

    def cleanup(
        self,
        *,
        delete_git_branches: bool = True,
        active_lease_branches: Optional[set[tuple[str, str]]] = None,
        active_worktree_branches: Optional[set[tuple[str, str]]] = None,
    ) -> list[BranchAllocation] | Exception:
        """
        Delete local git branches for released/archived allocations with no
        active lease or worktree. Returns cleaned allocations.
        """
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        lease_keys = active_lease_branches or set()
        worktree_keys = active_worktree_branches or set()
        cleaned: list[BranchAllocation] = []
        remaining: list[BranchAllocation] = []
        for row in rows:
            key = (row.repository, row.name)
            if row.status not in {"released", "archived"}:
                remaining.append(row)
                continue
            if key in lease_keys or key in worktree_keys:
                remaining.append(row)
                continue
            if delete_git_branches:
                resolved = resolve_repo_filesystem_path(
                    session_root=self._session_root,
                    sync_root=self._sync_root,
                    repository=row.repository,
                    definition_path=self._definition_path,
                )
                if not isinstance(resolved, Exception):
                    try:
                        git_repo = Repo(str(resolved))
                        if (
                            row.name in [head.name for head in git_repo.heads]
                            and git_repo.active_branch.name != row.name
                        ):
                            git_repo.delete_head(row.name, force=True)
                    except (GitCommandError, OSError, TypeError, ValueError):
                        pass
            cleaned.append(row)
        saved = self._store.save(remaining)
        if isinstance(saved, Exception):
            return saved
        return cleaned

    def get(
        self,
        *,
        branch_id: Optional[str] = None,
        name: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> BranchAllocation | None | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        for row in rows:
            if branch_id and row.branch_id == branch_id:
                return row
            if name and repository and row.name == name and row.repository == repository:
                return row
        return None

    def _set_status(
        self,
        *,
        branch_id: Optional[str],
        name: Optional[str],
        repository: Optional[str],
        status: str,
        event_type: Optional[str],
    ) -> BranchAllocation | Exception:
        now = self._now()
        updated_holder: list[BranchAllocation] = []

        def _mutate(rows: list[BranchAllocation]) -> list[BranchAllocation]:
            idx = self._find_index(
                rows,
                branch_id=branch_id,
                name=name,
                repository=repository,
            )
            if idx is None:
                raise ValueError("branch allocation not found")
            updated = rows[idx].model_copy(
                update={"status": status, "updated_at": now},
            )
            rows[idx] = updated
            updated_holder.append(updated)
            return rows

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        if not updated_holder:
            return ValueError("branch allocation not found")
        allocation = updated_holder[0]
        if event_type:
            self._events.append(
                event_type,  # type: ignore[arg-type]
                {
                    "branch_id": allocation.branch_id,
                    "name": allocation.name,
                    "repository": allocation.repository,
                    "status": status,
                },
                at=now,
            )
        return allocation

    @staticmethod
    def _find_index(
        rows: list[BranchAllocation],
        *,
        branch_id: Optional[str],
        name: Optional[str],
        repository: Optional[str],
    ) -> int | None:
        for idx, row in enumerate(rows):
            if branch_id and row.branch_id == branch_id:
                return idx
            if name and repository and row.name == name and row.repository == repository:
                return idx
        return None


__all__ = ["BranchService"]
