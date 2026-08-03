#!/usr/bin/env python
"""Regression tests for cold-importable state identity helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_identity_helpers_are_cold_importable(cold_import_environment) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    environment = cold_import_environment
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            ("from metagit.core.state.identity import resolve_org_id, resolve_workspace_id; print('ok')"),
        ],
        cwd=repository_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
