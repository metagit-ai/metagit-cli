#!/usr/bin/env python
"""Service layer for enqueueing and integrating RFC-0011 merge requests."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import PurePosixPath

from git import GitCommandError, Repo

from metagit.core.coordination.repo_paths import canonical_repository_ref, resolve_repo_filesystem_path
from metagit.core.merge.events import MergeEventStore
from metagit.core.merge.git_ops import attempt_merge, detached_worktree, ensure_branch
from metagit.core.merge.models import (
    MergeConflict,
    MergeRequest,
    MergeRollupConflict,
    MergeRollupFailure,
    MergeRollupResult,
    MergeValidation,
)
from metagit.core.merge.store import MergeStore
from metagit.core.merge.validators import run_validators
from metagit.core.workspace.context_models import utc_now_iso


class MergeOrchestrator:
    """Coordinate local merge queue records and GitPython merge attempts."""

    def __init__(
        self,
        session_root: str,
        validators: list[str] | None = None,
        regenerate: dict[str, str] | None = None,
    ) -> None:
        self._session_root = session_root
        self._validators = list(validators or [])
        self._regenerate = dict(regenerate or {})
        self.store = MergeStore(session_root)
        self._events = MergeEventStore(session_root)

    def enqueue(
        self,
        repository: str,
        source_branch: str,
        target_branch: str,
        *,
        node_id: str | None = None,
        agent_id: str | None = None,
        repo_path: str | None = None,
    ) -> MergeRequest | Exception:
        resolved_path = self._resolve_repo_path(repository, repo_path)
        if isinstance(resolved_path, Exception):
            return resolved_path
        now = utc_now_iso()
        request = MergeRequest(
            merge_id=self._merge_id(repository, source_branch, target_branch),
            repository=repository,
            source_branch=source_branch,
            target_branch=target_branch,
            status="queued",
            repo_path=resolved_path,
            node_id=node_id,
            agent_id=agent_id,
            created_at=now,
            updated_at=now,
        )
        saved = self.store.save(request)
        if isinstance(saved, Exception):
            return saved
        event = self._events.append("MergeEnqueued", self._event_payload(request))
        if isinstance(event, Exception):
            return event
        return request

    def integrate(self, merge_id: str) -> MergeRequest | Exception:
        request = self.store.load(merge_id)
        if isinstance(request, Exception):
            return request
        if not request.repo_path:
            return ValueError(f"repo_path is required for merge request: {merge_id}")

        request.status = "running"
        request.updated_at = utc_now_iso()
        request.error_message = None
        saved = self.store.save(request)
        if isinstance(saved, Exception):
            return saved

        result = attempt_merge(
            request.repo_path,
            request.source_branch,
            request.target_branch,
            regenerate=self._regenerate,
        )
        if isinstance(result, Exception):
            request.status = "failed"
            request.error_message = str(result)
            request.updated_at = utc_now_iso()
            saved = self.store.save(request)
            if isinstance(saved, Exception):
                return saved
            event = self._events.append("MergeFailed", self._event_payload(request))
            return event if isinstance(event, Exception) else request

        if result.ok:
            validation = self._validate_merged_tree(request.repo_path, result.commit_sha)
            request.status = "succeeded"
            request.commit_sha = result.commit_sha
            request.conflict = None
            request.validation = validation
            request.acl_commands = []
            request.error_message = None
            if not validation.ok:
                request.status = "validation_failed"
                request.error_message = "merge validators failed"
            request.updated_at = utc_now_iso()
            saved = self.store.save(request)
            if isinstance(saved, Exception):
                return saved
            event_type = "MergeSucceeded" if validation.ok else "MergeValidationFailed"
            event = self._events.append(event_type, self._event_payload(request))
            return event if isinstance(event, Exception) else request

        conflict = result.conflict
        if conflict is None:
            request.status = "failed"
            request.error_message = "merge attempt failed without conflict details"
            event_type = "MergeFailed"
        else:
            request.status = "conflict"
            request.conflict = MergeConflict(
                files=conflict.files,
                message=conflict.message,
                dispatch_hint=f"Dispatch a merge-resolution agent for {request.repository}.",
            )
            request.acl_commands = self._acl_commands(request)
            event_type = "ConflictDetected"
        request.updated_at = utc_now_iso()
        saved = self.store.save(request)
        if isinstance(saved, Exception):
            return saved
        event = self._events.append(event_type, self._event_payload(request))
        return event if isinstance(event, Exception) else request

    def retry(self, merge_id: str) -> MergeRequest | Exception:
        request = self.store.load(merge_id)
        if isinstance(request, Exception):
            return request
        if request.status not in {"failed", "conflict", "validation_failed"}:
            return ValueError(f"merge request is not retryable: {merge_id}")
        request.status = "queued"
        request.conflict = None
        request.error_message = None
        request.acl_commands = []
        request.updated_at = utc_now_iso()
        saved = self.store.save(request)
        if isinstance(saved, Exception):
            return saved
        return self.integrate(merge_id)

    def run_validators(self, repo_path: str) -> MergeValidation:
        """Run configured merge validators for a repository path."""
        return run_validators(repo_path, self._validators)

    def _validate_merged_tree(self, repo_path: str, commit_sha: str | None) -> MergeValidation:
        """Run validators against the merge commit, not the caller's checkout.

        Empty validator lists do not need a tree. Configured commands run in a
        detached worktree of ``commit_sha`` so they see the merge result.
        """
        if not self._validators or not commit_sha:
            return self.run_validators(repo_path)
        with detached_worktree(repo_path, commit_sha) as checkout:
            return self.run_validators(checkout)

    def promote(self, merge_id: str, into_branch: str) -> MergeRequest | Exception:
        """Promote a successful integration branch into another branch."""
        request = self.store.load(merge_id)
        if isinstance(request, Exception):
            return request
        if not request.repo_path:
            return ValueError(f"repo_path is required for merge request: {merge_id}")
        if request.status == "validation_failed":
            return ValueError("validation failed; promote blocked")
        if request.status != "succeeded":
            return ValueError(f"merge request is not promotable: {request.status}")
        if request.validation is None:
            request.validation = self.run_validators(request.repo_path)
            request.updated_at = utc_now_iso()
            saved = self.store.save(request)
            if isinstance(saved, Exception):
                return saved
        if not request.validation.ok:
            request.status = "validation_failed"
            request.error_message = "merge validators failed"
            request.updated_at = utc_now_iso()
            saved = self.store.save(request)
            if isinstance(saved, Exception):
                return saved
            event = self._events.append("MergeValidationFailed", self._event_payload(request))
            if isinstance(event, Exception):
                return event
            return ValueError("validation failed; promote blocked")

        result = attempt_merge(
            request.repo_path,
            request.target_branch,
            into_branch,
            regenerate=self._regenerate,
        )
        if isinstance(result, Exception):
            return result
        if not result.ok:
            message = "promote merge failed"
            if result.conflict is not None:
                message = result.conflict.message
            return ValueError(message)
        request.commit_sha = result.commit_sha
        request.updated_at = utc_now_iso()
        saved = self.store.save(request)
        if isinstance(saved, Exception):
            return saved
        event = self._events.append(
            "MergePromoted",
            self._event_payload(request) | {"promoted_into": into_branch},
        )
        return event if isinstance(event, Exception) else request

    def rollup(
        self,
        repository: str,
        into: str,
        base: str,
        branches: list[str],
        *,
        repo_path: str | None = None,
    ) -> MergeRollupResult | Exception:
        """Merge branches into ``into`` in order, rebuilding mapped generated files.

        Creates ``into`` from ``base`` when it is missing, without checking it out.
        Skips a branch already contained in ``into``. Stops at the first conflict
        or git error. Does not push.
        """
        resolved = self._resolve_repo_path(repository, repo_path)
        if isinstance(resolved, Exception):
            return resolved
        created = ensure_branch(resolved, into, base)
        if isinstance(created, Exception):
            return created
        try:
            repo = Repo(resolved)
            names = [head.name for head in repo.heads]
        except (GitCommandError, OSError, ValueError) as exc:
            return Exception(f"failed to read branches in {resolved}: {exc}")
        selected = _expand_branch_tokens(names, branches)
        if isinstance(selected, Exception):
            return selected
        caller_head = repo.head.commit.hexsha
        caller_branch = None if repo.head.is_detached else repo.active_branch.name
        summary = MergeRollupResult(into=into)
        for branch in selected:
            if _is_ancestor(repo, branch, into):
                summary.skipped.append(branch)
                continue
            result = attempt_merge(resolved, branch, into, regenerate=self._regenerate)
            if isinstance(result, Exception):
                summary.failed.append(MergeRollupFailure(branch=branch, into=into, message=str(result)))
                break
            if not result.ok:
                conflict = result.conflict
                summary.conflicted.append(
                    MergeRollupConflict(
                        branch=branch,
                        into=into,
                        files=list(conflict.files) if conflict is not None else ["unknown"],
                        message=conflict.message if conflict is not None else "merge failed",
                    ),
                )
                break
            validation = self._validate_merged_tree(resolved, result.commit_sha)
            if not validation.ok:
                summary.failed.append(
                    MergeRollupFailure(
                        branch=branch,
                        into=into,
                        message="merge validators failed",
                    ),
                )
                break
            summary.merged.append(branch)
        fresh = Repo(resolved)
        moved_head = fresh.head.commit.hexsha != caller_head
        moved_branch = caller_branch is not None and (
            fresh.head.is_detached or fresh.active_branch.name != caller_branch
        )
        if moved_head or moved_branch:
            return Exception(f"rollup moved the checkout at {resolved}")
        return summary

    def status(self, repository: str | None = None) -> list[MergeRequest] | Exception:
        rows = self.store.list_merges()
        if isinstance(rows, Exception):
            return rows
        if repository is None:
            return rows
        return [row for row in rows if row.repository == repository]

    def _resolve_repo_path(self, repository: str, repo_path: str | None) -> str | Exception:
        if repo_path:
            return repo_path
        if canonical_repository_ref(repository) == ".":
            resolved = resolve_repo_filesystem_path(
                session_root=self._session_root,
                sync_root=self._session_root,
                repository=".",
                definition_path=os.path.join(self._session_root, ".metagit.yml"),
            )
            if isinstance(resolved, Exception):
                return resolved
            return str(resolved)
        parts = repository.split("/")
        if len(parts) != 2:
            return ValueError("repository must be project/repo")
        project_name, repo_name = parts
        candidates = [
            os.path.join(self._session_root, project_name, repo_name),
            os.path.join(self._session_root, repo_name),
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return ValueError("repo_path is required when repository cannot be resolved")

    def _merge_id(self, repository: str, source_branch: str, target_branch: str) -> str:
        raw = f"{repository}-{source_branch}-into-{target_branch}"
        slug = re.sub(r"[^\w.-]+", "-", raw).strip("-")
        return f"{slug}-{uuid.uuid4().hex[:8]}"

    def _acl_commands(self, request: MergeRequest) -> list[str]:
        agent = request.agent_id or "merge-agent"
        commands = [
            f"metagit branch allocate --purpose merge-resolution --base {request.target_branch}",
            f"metagit lease acquire --branch {request.target_branch} --agent {agent}",
            f"metagit worktree create --branch {request.target_branch}",
        ]
        if request.conflict is not None:
            commands.extend(f"metagit claim declare --path {path} --agent {agent}" for path in request.conflict.files)
        return commands

    def _event_payload(self, request: MergeRequest) -> dict:
        payload = {
            "merge_id": request.merge_id,
            "repository": request.repository,
            "source_branch": request.source_branch,
            "target_branch": request.target_branch,
            "status": request.status,
        }
        if request.node_id:
            payload["node_id"] = request.node_id
        if request.agent_id:
            payload["agent_id"] = request.agent_id
        if request.commit_sha:
            payload["commit_sha"] = request.commit_sha
        if request.conflict is not None:
            payload["conflict"] = request.conflict.model_dump(mode="json")
        return payload


def _expand_branch_tokens(names: list[str], tokens: list[str]) -> list[str] | Exception:
    selected: list[str] = []
    known = set(names)
    for token in tokens:
        parts = [part.strip() for part in token.split(",") if part.strip()]
        for part in parts:
            if any(char in part for char in "*?[]"):
                matched = sorted(name for name in names if PurePosixPath(name).match(part))
                if not matched:
                    return ValueError(f"no branches matched {part!r}")
                selected.extend(matched)
                continue
            if part not in known:
                return ValueError(f"branch not found: {part}")
            selected.append(part)
    return selected


def _is_ancestor(repo: Repo, branch: str, into: str) -> bool:
    try:
        repo.git.merge_base("--is-ancestor", branch, into)
    except GitCommandError:
        return False
    return True


__all__ = ["MergeOrchestrator"]
