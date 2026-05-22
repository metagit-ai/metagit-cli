#!/usr/bin/env python
"""
Persist workspace objectives under .metagit/sessions/objectives.json.
"""

import json
import os
from pathlib import Path
from typing import Optional

from metagit.core.context.models import Objective
from metagit.core.mcp.services.session_store import SessionStore


class ObjectiveStore:
    """Read and write objectives JSON using the SessionStore layout."""

    def __init__(self, workspace_root: str) -> None:
        self._session = SessionStore(workspace_root=workspace_root)
        self._path = Path(self._session.sessions_dir) / "objectives.json"

    @property
    def path(self) -> Path:
        """Filesystem path for objectives persistence."""
        return self._path

    def load_objectives(self) -> list[Objective]:
        """Return stored objectives or an empty list when missing/invalid."""
        payload = self._read_json(path=self._path)
        if not payload:
            return []
        raw_list = payload.get("objectives")
        if not isinstance(raw_list, list):
            return []
        result: list[Objective] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            result.append(Objective.model_validate(item))
        return result

    def save_objectives(self, objectives: list[Objective]) -> None:
        """Write objectives envelope to disk."""
        self._session.ensure_dirs()
        payload = {
            "objectives": [
                objective.model_dump(mode="json") for objective in objectives
            ],
        }
        self._write_json(path=self._path, payload=payload)

    def _read_json(self, path: Path) -> Optional[dict]:
        """Read JSON object from path."""
        if not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: Path, payload: dict) -> None:
        """Write JSON object to path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
