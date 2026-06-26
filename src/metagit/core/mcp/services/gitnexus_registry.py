#!/usr/bin/env python
"""
Read GitNexus global registry and per-repo index status.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional


class GitNexusRegistryAdapter:
    """Resolve GitNexus index metadata for local repository paths."""

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self._registry_path = registry_path or Path.home() / ".gitnexus" / "registry.json"

    def load_entries(self) -> list[dict[str, Any]]:
        """Load registry entries or return an empty list."""
        if not self._registry_path.is_file():
            return []
        try:
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def lookup_by_path(self, repo_path: str) -> Optional[dict[str, Any]]:
        """Find registry entry for a resolved repository path."""
        target = str(Path(repo_path).expanduser().resolve())
        for entry in self.load_entries():
            entry_path = entry.get("path")
            if not entry_path:
                continue
            if str(Path(str(entry_path)).resolve()) == target:
                return entry
        return None

    def index_status(self, repo_path: str) -> str:
        """Return indexed, stale, missing, or error for a repository path."""
        entry = self.lookup_by_path(repo_path=repo_path)
        if entry is None:
            return "missing"
        if not Path(repo_path).is_dir():
            return "missing"
        cli_status = self._status_via_cli(repo_path=repo_path)
        if cli_status:
            return cli_status
        return "indexed"

    def _status_via_cli(self, repo_path: str) -> Optional[str]:
        """Parse `gitnexus status` output when the CLI is available."""
        try:
            completed = subprocess.run(
                ["npx", "--yes", "gitnexus@1.6.4", "status"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        output = (completed.stdout or "") + (completed.stderr or "")
        if "stale" in output.lower():
            return "stale"
        if "indexed" in output.lower():
            return "indexed"
        if completed.returncode != 0:
            return "error"
        return "indexed"

    def summarize_for_paths(self, repo_paths: list[str]) -> dict[str, str]:
        """Map repo paths to gitnexus status strings."""
        return {path: self.index_status(repo_path=path) for path in repo_paths}

    def registry_name_for_path(self, repo_path: str) -> Optional[str]:
        """GitNexus registry alias for a checkout path (--repo flag value)."""
        entry = self.lookup_by_path(repo_path=repo_path)
        if entry is None:
            return None
        name = entry.get("name")
        return str(name) if isinstance(name, str) and name else None
