#!/usr/bin/env python
"""CLI tests for metagit component list|show|resolve (RFC-0027)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "components"
NATIVE = FIXTURES / "native-nested.yml"
NONE = FIXTURES / "no-components.yml"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "metagit.cli.main", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_component_list_json_includes_nested_ids() -> None:
    result = _run("component", "list", "-c", str(NATIVE), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    ids = {row["id"] for row in payload["components"]}
    assert "platform/core/web" in ids
    assert "platform/core/api" in ids


def test_component_show_json_has_name_web() -> None:
    result = _run("component", "show", "platform/core/web", "-c", str(NATIVE), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["name"] == "web"


def test_component_resolve_json_matches_web() -> None:
    result = _run(
        "component",
        "resolve",
        "apps/web/src/login.tsx",
        "-c",
        str(NATIVE),
        "--project",
        "platform",
        "--repo",
        "core",
        "--json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["matched"] is True
    assert payload["name"] == "web"


def test_component_resolve_json_miss_exits_nonzero() -> None:
    result = _run(
        "component",
        "resolve",
        "docs/nope.md",
        "-c",
        str(NATIVE),
        "--project",
        "platform",
        "--repo",
        "core",
        "--json",
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["matched"] is False


def test_component_list_empty_catalog_json() -> None:
    result = _run("component", "list", "-c", str(NONE), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["components"] == []
