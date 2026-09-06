#!/usr/bin/env python
"""CLI tests for component validation via config validate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_config_validate_rejects_duplicate_component_name(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: acme\nkind: umbrella\nworkspace:\n  projects:\n"
        "    - name: platform\n      repos:\n"
        "        - name: core\n          path: ./platform\n"
        "          components:\n"
        "            - name: web\n              path: apps/web\n"
        "            - name: web\n              path: apps/other\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "metagit.cli.main", "config", "validate", "-c", str(manifest)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "duplicate" in combined.lower()
    assert "Failed to load" not in combined


def test_config_validate_accepts_manifest_without_components(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: demo\nkind: umbrella\nworkspace:\n  projects:\n    - name: p\n      repos: []\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "metagit.cli.main", "config", "validate", "-c", str(manifest)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
