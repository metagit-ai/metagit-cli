#!/usr/bin/env python
"""Persist workspace handoffs under the resolved sessions directory."""

from __future__ import annotations

from pathlib import Path

from metagit.core.context.models import HandoffItem
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.state.base import HandoffBackend, StateToken
from metagit.core.state.resolver import resolve_backend


class HandoffStore:
    """Read and write handoff queue JSON."""

    def __init__(
        self,
        workspace_root: str,
        backend: HandoffBackend | None = None,
    ) -> None:
        self._backend = backend or resolve_backend(workspace_root).handoffs()
        self._token: StateToken = None
        adapter_path = getattr(self._backend, "path", None)
        if isinstance(adapter_path, Path):
            self._path = adapter_path
        else:
            session = SessionStore(workspace_root=workspace_root)
            self._path = Path(session.sessions_dir) / "handoffs.json"

    @property
    def path(self) -> Path:
        return self._path

    def load_handoffs(self) -> list[HandoffItem]:
        rows, token = self._backend.load()
        self._token = token
        return rows

    def save_handoffs(self, rows: list[HandoffItem]) -> None:
        self._token = self._backend.save(rows, expected=self._token)

    def append_handoff(self, item: HandoffItem) -> HandoffItem:
        appended = self._backend.append(item)
        _, token = self._backend.load()
        self._token = token
        return appended
