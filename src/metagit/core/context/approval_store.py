#!/usr/bin/env python
"""
Persist approval queue JSON under ``<workspace_root>/.metagit/approvals/pending.json``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from metagit.core.context.models import ApprovalRequest


class ApprovalStore:
    """Load and save approval rows as a single JSON document."""

    def __init__(self, workspace_root: str) -> None:
        self._workspace_root = str(Path(workspace_root).expanduser().resolve())
        approvals_dir = os.path.join(self._workspace_root, ".metagit", "approvals")
        self._path = os.path.join(approvals_dir, "pending.json")

    @property
    def path(self) -> Path:
        """Absolute path to the queue file."""
        return Path(self._path)

    def ensure_dirs(self) -> None:
        """Create approvals directory with restrictive permissions when possible."""
        parent = Path(self._path).parent
        parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(parent, 0o700)
        except OSError:
            pass

    def load_requests(self) -> list[ApprovalRequest]:
        """Return stored requests, or an empty list when missing or invalid."""
        path = Path(self._path)
        if not path.is_file():
            return []
        try:
            raw_text = path.read_text(encoding="utf-8")
            blob = json.loads(raw_text)
        except (OSError, json.JSONDecodeError):
            return []
        rows = blob.get("requests") if isinstance(blob, dict) else None
        if not isinstance(rows, list):
            return []
        items: list[ApprovalRequest] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                items.append(ApprovalRequest.model_validate(row))
            except ValidationError:
                continue
        return items

    def save_requests(self, requests: list[ApprovalRequest]) -> None:
        """Persist all requests, replacing the file contents."""
        self.ensure_dirs()
        payload = {"requests": [req.model_dump(mode="json") for req in requests]}
        Path(self._path).write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass
