#!/usr/bin/env python
"""
Persist workspace objectives under .metagit/sessions/objectives.json.
"""

from pathlib import Path

from metagit.core.context.models import Objective
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.state.base import ObjectiveBackend, StateToken
from metagit.core.state.resolver import resolve_backend


class ObjectiveStore:
    """Read and write objectives JSON using the SessionStore layout."""

    def __init__(
        self,
        workspace_root: str,
        backend: ObjectiveBackend | None = None,
    ) -> None:
        self._backend = backend or resolve_backend(workspace_root).objectives()
        self._token: StateToken = None
        adapter_path = getattr(self._backend, "path", None)
        if isinstance(adapter_path, Path):
            self._path = adapter_path
        else:
            session = SessionStore(workspace_root=workspace_root)
            self._path = Path(session.sessions_dir) / "objectives.json"

    @property
    def path(self) -> Path:
        """Filesystem path for objectives persistence."""
        return self._path

    def load_objectives(self) -> list[Objective]:
        """Return stored objectives or an empty list when missing/invalid."""
        objectives, token = self._backend.load()
        self._token = token
        return objectives

    def save_objectives(self, objectives: list[Objective]) -> None:
        """Write objectives envelope to disk."""
        self._token = self._backend.save(objectives, expected=self._token)
