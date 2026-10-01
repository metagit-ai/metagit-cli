#!/usr/bin/env python
"""Git worktree manager for isolated agent checkouts."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from git import Repo
from git.exc import GitCommandError

from metagit.core.coordination.event_store import AclEventStore
from metagit.core.coordination.lease_service import LeaseService
from metagit.core.coordination.manifest_service import AgentManifestService
from metagit.core.coordination.models import (
    AgentExecutionManifest,
    WorktreeGcResult,
    WorktreeGcSkip,
    WorktreeListResult,
    WorktreeRecord,
    WorktreeStatusResult,
)
from metagit.core.coordination.paths import worktree_checkout_path, worktrees_file
from metagit.core.coordination.repo_lock_service import RepoLockRegistry
from metagit.core.coordination.repo_paths import (
    parse_repository_ref,
    resolve_repo_filesystem_path,
)
from metagit.core.coordination.store import JsonListStore
from metagit.core.workspace.context_models import utc_now_iso


class WorktreeService:
    """Create, destroy, gc, and status agent worktrees."""

    def __init__(
        self,
        session_root: str,
        *,
        sync_root: str | None = None,
        definition_path: str | None = None,
        worktrees_path: str | None = None,
        lease_service: LeaseService | None = None,
        now_fn: Callable[[], str] | None = None,
        event_store: AclEventStore | None = None,
        repo_lock: RepoLockRegistry | None = None,
        manifest_service: AgentManifestService | None = None,
    ) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())
        self._sync_root = str(Path(sync_root or session_root).expanduser().resolve())
        self._definition_path = definition_path
        self._worktrees_path = worktrees_path
        self._now = now_fn or utc_now_iso
        self._events = event_store or AclEventStore(self._session_root)
        self._repo_lock = repo_lock or RepoLockRegistry(
            self._session_root,
            now_fn=self._now,
        )
        self._leases = lease_service or LeaseService(
            self._session_root,
            sync_root=self._sync_root,
            definition_path=self._definition_path,
            now_fn=self._now,
            event_store=self._events,
            repo_lock=self._repo_lock,
        )
        self._manifests = manifest_service or AgentManifestService(self._session_root)
        self._store: JsonListStore[WorktreeRecord] = JsonListStore(
            worktrees_file(self._session_root),
            key="worktrees",
            model=WorktreeRecord,
        )

    def list(
        self,
        *,
        repository: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> WorktreeListResult | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        if repository:
            rows = [row for row in rows if row.repository == repository]
        if agent_id:
            rows = [row for row in rows if row.agent_id == agent_id]
        if status:
            rows = [row for row in rows if row.status == status]
        return WorktreeListResult(worktrees=rows)

    def create(
        self,
        *,
        repository: str,
        agent_id: str,
        task_id: str,
        branch: str,
        lease_id: Optional[str] = None,
        integration_branch: Optional[str] = None,
        claims: Optional[list[str]] = None,
        dependencies: Optional[list[str]] = None,
        context_budget: Optional[int] = None,
        completion_requirements: Optional[list[str]] = None,
    ) -> WorktreeRecord | Exception:
        lease = None
        if lease_id:
            listed = self._leases.list(agent_id=agent_id)
            if isinstance(listed, Exception):
                return listed
            lease = next(
                (item for item in listed.leases if item.lease_id == lease_id),
                None,
            )
            if lease is None:
                return ValueError(f"lease not found: {lease_id}")
        else:
            lease = self._leases.get_active(
                repository=repository,
                branch=branch,
                agent_id=agent_id,
            )
            if isinstance(lease, Exception):
                return lease
        if lease is None or lease.status != "active":
            return ValueError(
                "active lease required for worktree create "
                f"(repository={repository}, branch={branch}, agent_id={agent_id})",
            )
        if lease.branch != branch or lease.repository != repository:
            return ValueError("lease does not match repository/branch")

        existing = self._store.load()
        if isinstance(existing, Exception):
            return existing
        for row in existing:
            if row.status == "active" and row.agent_id == agent_id and row.repository == repository:
                return ValueError(
                    f"agent {agent_id} already has an active worktree for {repository}",
                )

        parsed = parse_repository_ref(repository)
        if isinstance(parsed, Exception):
            return parsed
        project_name, repo_name = parsed
        checkout = worktree_checkout_path(
            self._session_root,
            agent_id,
            project_name,
            repo_name,
            worktrees_path=self._worktrees_path,
        )
        if checkout.exists():
            return ValueError(f"worktree path already exists: {checkout}")

        repo_path = resolve_repo_filesystem_path(
            session_root=self._session_root,
            sync_root=self._sync_root,
            repository=repository,
            definition_path=self._definition_path,
        )
        if isinstance(repo_path, Exception):
            return repo_path
        try:
            git_repo = Repo(str(repo_path))
            checkout.parent.mkdir(parents=True, exist_ok=True)
            git_repo.git.worktree("add", str(checkout), branch)
        except (GitCommandError, OSError, ValueError) as exc:
            return Exception(f"failed to create worktree: {exc}")

        now = self._now()
        record = WorktreeRecord(
            worktree_id=uuid.uuid4().hex,
            path=str(checkout),
            repository=repository,
            branch=branch,
            agent_id=agent_id,
            task_id=task_id,
            lease_id=lease.lease_id,
            status="active",
            created_at=now,
            updated_at=now,
        )

        def _mutate(rows: list[WorktreeRecord]) -> list[WorktreeRecord]:
            for row in rows:
                if row.status == "active" and row.agent_id == agent_id and row.repository == repository:
                    raise ValueError(
                        f"agent {agent_id} already has an active worktree for {repository}",
                    )
            rows.append(record)
            return rows

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            shutil.rmtree(checkout, ignore_errors=True)
            return result

        manifest = AgentExecutionManifest(
            agent_id=agent_id,
            task_id=task_id,
            branch=branch,
            worktree=str(checkout),
            repositories=[repository],
            claims=list(claims or []),
            dependencies=list(dependencies or []),
            integration_branch=integration_branch,
            context_budget=context_budget,
            completion_requirements=list(completion_requirements or []),
            lease_id=lease.lease_id,
            created_at=now,
        )
        written = self._manifests.write(manifest)
        if isinstance(written, Exception):
            return written
        self._manifests.write_into_worktree(checkout, manifest)
        self._repo_lock.register(repository, agent_id)
        self._events.append(
            "WorktreeCreated",
            {
                "worktree_id": record.worktree_id,
                "path": record.path,
                "repository": repository,
                "branch": branch,
                "agent_id": agent_id,
                "lease_id": lease.lease_id,
            },
            at=now,
        )
        self._events.append(
            "AgentStarted",
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "worktree_id": record.worktree_id,
                "repository": repository,
            },
            at=now,
        )
        return record

    def destroy(
        self,
        *,
        worktree_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        repository: Optional[str] = None,
        force: bool = False,
    ) -> WorktreeRecord | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        target = None
        for row in rows:
            if worktree_id and row.worktree_id == worktree_id:
                target = row
                break
            if (
                agent_id
                and repository
                and row.agent_id == agent_id
                and row.repository == repository
                and row.status == "active"
            ):
                target = row
                break
        if target is None:
            return ValueError("worktree not found")

        if not force:
            reasons = _preservation_reasons(target.path)
            if reasons:
                detail = "; ".join(reasons)
                return ValueError(
                    f"refusing to destroy worktree {target.worktree_id} at {target.path}: {detail}. "
                    "Pass --force to remove it anyway.",
                )

        # The policy check above is the safety gate. git worktree remove still
        # needs --force to drop metagit's own .metagit-agent.json and ignored files.
        removed = self._remove_git_worktree(target.path, force=True)
        if isinstance(removed, Exception):
            return removed
        now = self._now()
        updated_holder: list[WorktreeRecord] = []

        def _mutate(current: list[WorktreeRecord]) -> list[WorktreeRecord]:
            for idx, row in enumerate(current):
                if row.worktree_id == target.worktree_id:
                    updated = row.model_copy(
                        update={"status": "destroyed", "updated_at": now},
                    )
                    current[idx] = updated
                    updated_holder.append(updated)
                    return current
            raise ValueError("worktree not found")

        result = self._store.update(_mutate)
        if isinstance(result, Exception):
            return result
        record = updated_holder[0]
        self._repo_lock.deregister(record.repository, record.agent_id)
        self._events.append(
            "WorktreeDestroyed",
            {
                "worktree_id": record.worktree_id,
                "path": record.path,
                "repository": record.repository,
                "agent_id": record.agent_id,
            },
            at=now,
        )
        return record

    def gc(self, *, force: bool = False, dry_run: bool = False) -> WorktreeGcResult | Exception:
        """Destroy active records whose lease expired or path is missing.

        Skips a checkout that still has uncommitted changes, untracked
        non-ignored files, or unpushed commits unless ``force`` is set.
        ``dry_run`` reports the same decisions and changes nothing.
        """
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        lease_list = self._leases.list()
        if isinstance(lease_list, Exception):
            return lease_list
        active_lease_ids = {item.lease_id for item in lease_list.leases if item.status == "active"}
        destroyed: list[WorktreeRecord] = []
        skipped: list[WorktreeGcSkip] = []
        for row in rows:
            if row.status != "active":
                continue
            path_missing = not Path(row.path).exists()
            lease_gone = row.lease_id not in active_lease_ids
            if not path_missing and not lease_gone:
                continue
            reasons = [] if path_missing else _preservation_reasons(row.path)
            if reasons and not force:
                detail = "; ".join(reasons)
                skipped.append(
                    WorktreeGcSkip(
                        worktree_id=row.worktree_id,
                        path=row.path,
                        reasons=reasons,
                        message=(f"skipped {row.worktree_id}: {detail}. Pass --force to remove it anyway."),
                    ),
                )
                continue
            if dry_run:
                destroyed.append(row)
                continue
            result = self.destroy(worktree_id=row.worktree_id, force=force or bool(reasons))
            if isinstance(result, Exception):
                skipped.append(
                    WorktreeGcSkip(
                        worktree_id=row.worktree_id,
                        path=row.path,
                        reasons=[str(result)],
                        message=str(result),
                    ),
                )
                continue
            destroyed.append(result)
        return WorktreeGcResult(dry_run=dry_run, destroyed=destroyed, skipped=skipped)

    def status(
        self,
        *,
        worktree_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> WorktreeStatusResult | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        selected = [
            row
            for row in rows
            if row.status == "active"
            and (not worktree_id or row.worktree_id == worktree_id)
            and (not agent_id or row.agent_id == agent_id)
        ]
        summaries: list[dict[str, Any]] = []
        for row in selected:
            summary: dict[str, Any] = {
                "worktree_id": row.worktree_id,
                "path": row.path,
                "repository": row.repository,
                "branch": row.branch,
                "agent_id": row.agent_id,
                "exists": Path(row.path).is_dir(),
            }
            if Path(row.path).is_dir():
                try:
                    repo = Repo(row.path)
                    summary["dirty"] = repo.is_dirty(untracked_files=True)
                    summary["active_branch"] = repo.active_branch.name if not repo.head.is_detached else None
                    summary["untracked"] = list(repo.untracked_files)[:20]
                except (GitCommandError, OSError, ValueError) as exc:
                    summary["error"] = str(exc)
            summaries.append(summary)
        return WorktreeStatusResult(worktrees=summaries)

    def active_branch_keys(self) -> set[tuple[str, str]] | Exception:
        rows = self._store.load()
        if isinstance(rows, Exception):
            return rows
        return {(row.repository, row.branch) for row in rows if row.status == "active"}

    def manifest(self, agent_id: str) -> AgentExecutionManifest | Exception:
        return self._manifests.show(agent_id)

    def _remove_git_worktree(self, path: str, *, force: bool) -> None | Exception:
        checkout = Path(path)
        if not checkout.exists():
            return None
        try:
            linked = Repo(str(checkout))
            git_dir = Path(linked.git.rev_parse("--git-common-dir"))
            if not git_dir.is_absolute():
                git_dir = (checkout / git_dir).resolve()
            main_root = git_dir.parent
            main_repo = Repo(str(main_root))
            args = ["remove", "--force", str(checkout)] if force else ["remove", str(checkout)]
            main_repo.git.worktree(*args)
            return None
        except (GitCommandError, OSError, ValueError) as exc:
            if not force:
                return Exception(
                    f"refusing to destroy worktree at {path}: {exc}. Pass --force to remove it anyway.",
                )
        shutil.rmtree(checkout, ignore_errors=True)
        return None


def _preservation_reasons(path: str) -> list[str]:
    """Reasons a checkout should not be deleted. Empty when it is safe."""
    checkout = Path(path)
    if not checkout.exists():
        return []
    try:
        repo = Repo(str(checkout))
    except (GitCommandError, OSError, ValueError) as exc:
        return [f"could not inspect worktree ({exc})"]
    reasons: list[str] = []
    if repo.is_dirty(untracked_files=False):
        reasons.append("uncommitted changes")
    # `.metagit-agent.json` is written by worktree create. It is coordination
    # metadata, not user work, and must not block gc of an otherwise clean tree.
    untracked = [name for name in repo.untracked_files if name != ".metagit-agent.json"]
    if untracked:
        shown = ", ".join(untracked[:8])
        reasons.append(f"untracked files: {shown}")
    unpushed = _unpushed_commit_count(repo)
    if unpushed:
        reasons.append(f"{unpushed} unpushed commit(s)")
    return reasons


def _unpushed_commit_count(repo: Repo) -> int:
    """Commits on HEAD that are not on any remote.

    A repository with no remotes returns 0. Removing the worktree keeps the
    branch, and there is no remote those commits could be missing from.
    """
    try:
        if not list(repo.remotes):
            return 0
    except (GitCommandError, OSError, ValueError):
        return 0
    try:
        count = repo.git.rev_list("--count", "@{upstream}..HEAD")
        return int(count)
    except (GitCommandError, ValueError):
        pass
    try:
        count = repo.git.rev_list("--count", "HEAD", "--not", "--remotes")
        return int(count)
    except (GitCommandError, ValueError):
        return 0


__all__ = ["WorktreeService"]
