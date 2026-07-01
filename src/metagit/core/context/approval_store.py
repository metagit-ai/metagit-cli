#!/usr/bin/env python
"""
Persist approval queue JSON under ``<workspace_root>/.metagit/approvals/pending.json``.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from metagit.core.context.models import ApprovalRequest
from metagit.core.state.base import ApprovalBackend, StateToken
from metagit.core.state.resolver import resolve_backend


class ApprovalStore:
    """Load and save approval rows as a single JSON document."""

    def __init__(
        self,
        workspace_root: str,
        backend: ApprovalBackend | None = None,
    ) -> None:
        root = str(Path(workspace_root).expanduser().resolve())
        self._backend = backend or resolve_backend(root).approvals()
        self._token: StateToken = None
        adapter_path = getattr(self._backend, "path", None)
        if isinstance(adapter_path, Path):
            self._path = adapter_path
        else:
            self._path = Path(root) / ".metagit" / "approvals" / "pending.json"

    @property
    def path(self) -> Path:
        """Absolute path to the queue file."""
        return self._path

    def ensure_dirs(self) -> None:
        """Create approvals directory with restrictive permissions when possible."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(self._path.parent, 0o700)

    def load_requests(self) -> list[ApprovalRequest]:
        """Return stored requests, or an empty list when missing or invalid."""
        rows, token = self._backend.load()
        self._token = token
        return rows

    def save_requests(self, requests: list[ApprovalRequest]) -> None:
        """Persist all requests, replacing the file contents."""
        self._token = self._backend.save(requests, expected=self._token)
