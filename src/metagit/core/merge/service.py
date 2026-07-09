#!/usr/bin/env python
"""Service layer for enqueueing and integrating RFC-0011 merge requests."""

from __future__ import annotations

import os
import re
import uuid

from metagit.core.merge.events import MergeEventStore
from metagit.core.merge.git_ops import attempt_merge
from metagit.core.merge.models import MergeConflict, MergeRequest
from metagit.core.merge.store import MergeStore
from metagit.core.workspace.context_models import utc_now_iso


class MergeOrchestrator:
    """Coordinate local merge queue records and GitPython merge attempts."""

    def __init__(self, session_root: str) -> None:
        self._session_root = session_root
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

        result = attempt_merge(request.repo_path, request.source_branch, request.target_branch)
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
            request.status = "succeeded"
            request.commit_sha = result.commit_sha
            request.conflict = None
            request.acl_commands = []
            request.updated_at = utc_now_iso()
            saved = self.store.save(request)
            if isinstance(saved, Exception):
                return saved
            event = self._events.append("MergeSucceeded", self._event_payload(request))
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


__all__ = ["MergeOrchestrator"]
