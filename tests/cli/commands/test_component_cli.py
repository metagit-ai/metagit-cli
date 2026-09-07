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
    assert payload["path"] == "apps/web/src/login.tsx"
    assert payload["name"] == "web"
    assert payload["spec"]["path"] == "apps/web"


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


def test_component_graph_json_includes_api_neighbor() -> None:
    result = _run("component", "graph", "platform/core/web", "-c", str(NATIVE), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["origin"]["id"] == "platform/core/web"
    neighbor_ids = {row["id"] for row in payload["nodes"]}
    assert "platform/core/api" in neighbor_ids
    assert any(edge["to"] == "platform/core/api" and edge["type"] == "depends_on" for edge in payload["edges"])


def test_component_graph_unknown_identity_exits_1() -> None:
    result = _run("component", "graph", "platform/core/missing", "-c", str(NATIVE))
    assert result.returncode == 1
    assert "component not found" in result.stderr


def test_component_graph_negative_depth_exits_nonzero() -> None:
    result = _run(
        "component",
        "graph",
        "platform/core/web",
        "-c",
        str(NATIVE),
        "--depth",
        "-1",
        "--json",
    )
    assert result.returncode != 0
    assert "depth must be >= 0" in result.stderr


def test_component_graph_invalid_direction_exits_nonzero() -> None:
    result = _run(
        "component",
        "graph",
        "platform/core/web",
        "-c",
        str(NATIVE),
        "--direction",
        "nope",
        "--json",
    )
    assert result.returncode != 0
    assert "Invalid value" in result.stderr or "nope" in result.stderr


def _write_init_umbrella(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "apps" / "web").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: umbrella",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: core",
                "          path: ./repo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path / ".metagit.yml"


def test_cli_init_apply_same_path_is_not_silent_success(tmp_path: Path) -> None:
    manifest = _write_init_umbrella(tmp_path)
    args = (
        "component",
        "init",
        "apps/web",
        "--project",
        "platform",
        "--repo",
        "core",
        "--kind",
        "application",
        "--apply",
        "--json",
        "-c",
        str(manifest),
    )
    first = _run(*args)
    assert first.returncode == 0, first.stdout + first.stderr
    assert json.loads(first.stdout)["applied"] is True
    second = _run(*args)
    assert second.returncode != 0
    combined = second.stdout + second.stderr
    assert "already catalogued" in combined
    if second.stdout.strip():
        payload = json.loads(second.stdout)
        assert payload.get("applied") is not True


def test_cli_init_apply_application_kind_manifest_errors(tmp_path: Path) -> None:
    (tmp_path / "apps" / "web").mkdir(parents=True)
    (tmp_path / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text("name: myapp\nkind: application\n", encoding="utf-8")
    result = _run(
        "component",
        "init",
        "apps/web",
        "--apply",
        "--json",
        "-c",
        str(manifest),
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "application-kind" in combined or "no workspace repos" in combined
    if result.stdout.strip():
        payload = json.loads(result.stdout)
        assert payload.get("applied") is not True


def test_component_list_empty_catalog_json() -> None:
    result = _run("component", "list", "-c", str(NONE), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["components"] == []
