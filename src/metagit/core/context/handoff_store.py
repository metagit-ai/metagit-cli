#!/usr/bin/env python
"""Persist workspace handoffs under the resolved sessions directory."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from metagit.core.context.models import HandoffItem
from metagit.core.mcp.services.session_store import SessionStore


class HandoffStore:
    """Read and write handoff queue JSON."""

    def __init__(self, workspace_root: str) -> None:
        session = SessionStore(workspace_root=workspace_root)
        self._path = Path(session.sessions_dir) / "handoffs.json"

    @property
    def path(self) -> Path:
        return self._path

    def load_handoffs(self) -> list[HandoffItem]:
        payload = self._read_json(self._path)
        if not payload:
            return []
        raw = payload.get("handoffs")
        if not isinstance(raw, list):
            return []
        rows: list[HandoffItem] = []
        for item in raw:
            if isinstance(item, dict):
                rows.append(HandoffItem.model_validate(item))
        return rows

    def save_handoffs(self, rows: list[HandoffItem]) -> None:
        self._write_json(
            self._path,
            {"handoffs": [row.model_dump(mode="json") for row in rows]},
        )

    def _read_json(self, path: Path) -> Optional[dict]:
        if not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
