#!/usr/bin/env python
"""Local JSON file state backend with locking and content-hash tokens."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from metagit.core.context.models import (
    ApprovalRequest,
    HandoffItem,
    Objective,
    WorkspaceEventsResult,
)
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.state.base import BackendBundle, StateToken
from metagit.core.state.errors import StateConflictError


def _token_for_bytes(raw: bytes) -> StateToken:
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


def _token_for_path(path: Path) -> StateToken:
    if not path.is_file():
        return None
    try:
        return _token_for_bytes(path.read_bytes())
    except OSError:
        return None


class LocalFileBackend:
    """Filesystem-backed objectives, handoffs, approvals, and events."""

    def __init__(self, workspace_root: str) -> None:
        root = str(Path(workspace_root).expanduser().resolve())
        session = SessionStore(workspace_root=root)
        self._workspace_root = root
        self._objectives_path = Path(session.sessions_dir) / "objectives.json"
        self._handoffs_path = Path(session.sessions_dir) / "handoffs.json"
        self._approvals_path = Path(root) / ".metagit" / "approvals" / "pending.json"

    @property
    def objectives_path(self) -> Path:
        return self._objectives_path

    @property
    def handoffs_path(self) -> Path:
        return self._handoffs_path

    @property
    def approvals_path(self) -> Path:
        return self._approvals_path

    def load_objectives(self) -> tuple[list[Objective], StateToken]:
        payload = self._read_json(self._objectives_path)
        token = _token_for_path(self._objectives_path)
        if not payload:
            return [], token
        raw_list = payload.get("objectives")
        if not isinstance(raw_list, list):
            return [], token
        rows: list[Objective] = []
        for item in raw_list:
            if isinstance(item, dict):
                rows.append(Objective.model_validate(item))
        return rows, token

    def save_objectives(
        self,
        objectives: list[Objective],
        *,
        expected: StateToken,
    ) -> StateToken:
        payload = {
            "objectives": [objective.model_dump(mode="json") for objective in objectives],
        }
        return self._write_json(self._objectives_path, payload=payload, expected=expected)

    def load_handoffs(self) -> tuple[list[HandoffItem], StateToken]:
        payload = self._read_json(self._handoffs_path)
        token = _token_for_path(self._handoffs_path)
        if not payload:
            return [], token
        raw_list = payload.get("handoffs")
        if not isinstance(raw_list, list):
            return [], token
        rows: list[HandoffItem] = []
        for item in raw_list:
            if isinstance(item, dict):
                rows.append(HandoffItem.model_validate(item))
        return rows, token

    def save_handoffs(
        self,
        handoffs: list[HandoffItem],
        *,
        expected: StateToken,
    ) -> StateToken:
        payload = {"handoffs": [row.model_dump(mode="json") for row in handoffs]}
        return self._write_json(self._handoffs_path, payload=payload, expected=expected)

    def append_handoff(self, item: HandoffItem) -> HandoffItem:
        with self._file_lock(self._handoffs_path):
            rows, _ = self.load_handoffs()
            rows.append(item)
            payload = {"handoffs": [row.model_dump(mode="json") for row in rows]}
            self._write_json_locked(
                self._handoffs_path,
                payload=payload,
                expected=None,
                skip_cas=True,
            )
        return item

    def load_requests(self) -> tuple[list[ApprovalRequest], StateToken]:
        payload = self._read_json(self._approvals_path)
        token = _token_for_path(self._approvals_path)
        if not payload:
            return [], token
        raw_list = payload.get("requests")
        if not isinstance(raw_list, list):
            return [], token
        rows: list[ApprovalRequest] = []
        for item in raw_list:
            if isinstance(item, dict):
                with contextlib.suppress(Exception):
                    rows.append(ApprovalRequest.model_validate(item))
        return rows, token

    def save_requests(
        self,
        requests: list[ApprovalRequest],
        *,
        expected: StateToken,
    ) -> StateToken:
        self._ensure_approvals_dir()
        payload = {"requests": [req.model_dump(mode="json") for req in requests]}
        return self._write_json(self._approvals_path, payload=payload, expected=expected)

    def list_events(self, *, since: str | None = None) -> WorkspaceEventsResult:
        from metagit.core.context.event_service import WorkspaceEventService

        return WorkspaceEventService(workspace_root=self._workspace_root).list_events(since=since)

    def _ensure_approvals_dir(self) -> None:
        parent = self._approvals_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(parent, 0o700)

    def _ensure_sessions_dir(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        SessionStore(workspace_root=self._workspace_root).ensure_dirs()

    def _read_json(self, path: Path) -> Optional[dict[str, Any]]:
        if not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(
        self,
        path: Path,
        *,
        payload: dict[str, Any],
        expected: StateToken,
        skip_cas: bool = False,
    ) -> StateToken:
        if path == self._approvals_path:
            self._ensure_approvals_dir()
        else:
            self._ensure_sessions_dir(path)
        with self._file_lock(path):
            return self._write_json_locked(
                path,
                payload=payload,
                expected=expected,
                skip_cas=skip_cas,
            )

    def _write_json_locked(
        self,
        path: Path,
        *,
        payload: dict[str, Any],
        expected: StateToken,
        skip_cas: bool = False,
    ) -> StateToken:
        current = _token_for_path(path)
        if not skip_cas and current != expected:
            raise StateConflictError(
                f"state conflict for {path.name}: expected token {expected!r}, found {current!r}",
            )
        serialized = json.dumps(payload, indent=2) + "\n"
        path.write_text(serialized, encoding="utf-8")
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)
        return _token_for_bytes(serialized.encode("utf-8"))

    @contextlib.contextmanager
    def _file_lock(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            with contextlib.suppress(OSError, AttributeError):
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                with contextlib.suppress(OSError, AttributeError):
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class _LocalObjectiveAdapter:
    def __init__(self, backend: LocalFileBackend) -> None:
        self._backend = backend

    @property
    def path(self) -> Path:
        return self._backend.objectives_path

    def load(self) -> tuple[list[Objective], StateToken]:
        return self._backend.load_objectives()

    def save(
        self,
        objectives: list[Objective],
        *,
        expected: StateToken,
    ) -> StateToken:
        return self._backend.save_objectives(objectives, expected=expected)


class _LocalHandoffAdapter:
    def __init__(self, backend: LocalFileBackend) -> None:
        self._backend = backend

    @property
    def path(self) -> Path:
        return self._backend.handoffs_path

    def load(self) -> tuple[list[HandoffItem], StateToken]:
        return self._backend.load_handoffs()

    def save(
        self,
        handoffs: list[HandoffItem],
        *,
        expected: StateToken,
    ) -> StateToken:
        return self._backend.save_handoffs(handoffs, expected=expected)

    def append(self, item: HandoffItem) -> HandoffItem:
        return self._backend.append_handoff(item)


class _LocalApprovalAdapter:
    def __init__(self, backend: LocalFileBackend) -> None:
        self._backend = backend

    @property
    def path(self) -> Path:
        return self._backend.approvals_path

    def load(self) -> tuple[list[ApprovalRequest], StateToken]:
        return self._backend.load_requests()

    def save(
        self,
        requests: list[ApprovalRequest],
        *,
        expected: StateToken,
    ) -> StateToken:
        return self._backend.save_requests(requests, expected=expected)


class _LocalEventsAdapter:
    def __init__(self, backend: LocalFileBackend) -> None:
        self._backend = backend

    def list_events(self, *, since: str | None = None) -> WorkspaceEventsResult:
        return self._backend.list_events(since=since)


def local_bundle(workspace_root: str) -> BackendBundle:
    """Construct a local backend bundle for one workspace root."""
    backend = LocalFileBackend(workspace_root=workspace_root)
    return BackendBundle(
        objectives_backend=_LocalObjectiveAdapter(backend),
        handoffs_backend=_LocalHandoffAdapter(backend),
        approvals_backend=_LocalApprovalAdapter(backend),
        events_backend=_LocalEventsAdapter(backend),
    )


__all__ = ["LocalFileBackend", "local_bundle"]
