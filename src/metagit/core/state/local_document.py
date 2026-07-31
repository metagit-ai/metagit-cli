#!/usr/bin/env python
"""Filesystem DocumentStore with legacy paths for coordination documents."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.state.base import StateToken
from metagit.core.state.document import DocumentRef, StateRecord
from metagit.core.state.errors import StateConflictError
from metagit.core.state.plane import (
    KEY_DOCUMENT,
    NS_COORD_APPROVALS,
    NS_COORD_EVENTS,
    NS_COORD_HANDOFFS,
    NS_COORD_OBJECTIVES,
    derive_workspace_id,
)

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]


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


class LocalDocumentStore:
    """Store state documents as locked JSON files below one workspace root."""

    def __init__(
        self,
        workspace_root: str,
        *,
        org_id: str = "_",
        workspace_id: str | None = None,
    ) -> None:
        self._workspace_root = str(Path(workspace_root).expanduser().resolve())
        self._org_id = org_id
        self._workspace_id = workspace_id or derive_workspace_id(self._workspace_root)
        self._session_store = SessionStore(workspace_root=self._workspace_root)

    def ref_for(self, namespace: str, key: str) -> DocumentRef:
        """Build a document reference using this store's identity."""
        return DocumentRef(
            org_id=self._org_id,
            workspace_id=self._workspace_id,
            namespace=namespace,
            key=key,
        )

    def get(self, ref: DocumentRef) -> StateRecord | None:
        path = self._path_for(ref.namespace, ref.key)
        body = self._read_json(path)
        if body is None:
            return None
        return StateRecord(ref=ref, body=body, token=_token_for_path(path))

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken:
        path = self._path_for(ref.namespace, ref.key)
        with self._file_lock(path):
            return self._write_json_locked(path, body=body, expected=expected)

    def append(self, ref: DocumentRef, item: dict[str, Any]) -> dict[str, Any]:
        path = self._path_for(ref.namespace, ref.key)
        envelope = "handoffs" if ref.namespace == NS_COORD_HANDOFFS and ref.key == KEY_DOCUMENT else "items"
        with self._file_lock(path):
            body = self._read_json(path) or {envelope: []}
            raw_items = body.get(envelope)
            items = list(raw_items) if isinstance(raw_items, list) else []
            items.append(dict(item))
            body[envelope] = items
            self._write_json_locked(path, body=body, expected=None, skip_cas=True)
        return dict(item)

    def list_prefix(
        self,
        org_id: str,
        workspace_id: str,
        namespace: str,
        *,
        prefix: str = "",
        limit: int = 100,
    ) -> list[DocumentRef]:
        if limit <= 0:
            return []
        keys: set[str] = set()
        legacy_path = self._legacy_path(namespace, KEY_DOCUMENT)
        if legacy_path is not None and legacy_path.is_file():
            keys.add(KEY_DOCUMENT)
        namespace_dir = Path(self._workspace_root) / ".metagit" / "state" / namespace
        if namespace_dir.is_dir():
            keys.update(path.stem for path in namespace_dir.glob("*.json"))
        return [
            DocumentRef(
                org_id=org_id,
                workspace_id=workspace_id,
                namespace=namespace,
                key=key,
            )
            for key in sorted(keys)
            if not prefix or key.startswith(prefix)
        ][:limit]

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None:
        path = self._path_for(ref.namespace, ref.key)
        with self._file_lock(path):
            current = _token_for_path(path)
            if current is None or current != expected:
                raise StateConflictError(f"state conflict deleting {ref.namespace}/{ref.key}")
            path.unlink()

    def describe(self) -> dict[str, Any]:
        return {
            "backend": "local",
            "org_id": self._org_id,
            "workspace_id": self._workspace_id,
            "workspace_root": self._workspace_root,
        }

    def _path_for(self, namespace: str, key: str) -> Path:
        legacy_path = self._legacy_path(namespace, key)
        if legacy_path is not None:
            return legacy_path
        return Path(self._workspace_root) / ".metagit" / "state" / namespace / f"{key}.json"

    def _legacy_path(self, namespace: str, key: str) -> Path | None:
        if key != KEY_DOCUMENT:
            return None
        sessions_dir = Path(self._session_store.sessions_dir)
        paths = {
            NS_COORD_OBJECTIVES: sessions_dir / "objectives.json",
            NS_COORD_HANDOFFS: sessions_dir / "handoffs.json",
            NS_COORD_APPROVALS: (Path(self._workspace_root) / ".metagit" / "approvals" / "pending.json"),
            NS_COORD_EVENTS: sessions_dir / "events.json",
        }
        return paths.get(namespace)

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json_locked(
        self,
        path: Path,
        *,
        body: dict[str, Any],
        expected: StateToken,
        skip_cas: bool = False,
    ) -> StateToken:
        current = _token_for_path(path)
        if not skip_cas and current != expected:
            raise StateConflictError(f"state conflict for {path.name}: expected token {expected!r}, found {current!r}")
        serialized = json.dumps(body, indent=2) + "\n"
        raw = serialized.encode("utf-8")
        path.write_bytes(raw)
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)
        return _token_for_bytes(raw)

    def _file_lock(self, path: Path) -> AbstractContextManager[None]:
        return _locked_path(path)


@contextlib.contextmanager
def _locked_path(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(path.parent, 0o700)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as handle:
        with contextlib.suppress(OSError, AttributeError):
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            with contextlib.suppress(OSError, AttributeError):
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["LocalDocumentStore"]
