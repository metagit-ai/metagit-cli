#!/usr/bin/env python
"""CLI tests for config graph suggest/export leaf -c and verbose."""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _minimal_manifest(path: Path) -> None:
    path.write_text(
        "name: demo\nkind: umbrella\nworkspace:\n  projects:\n"
        "    - name: p\n      repos: []\n",
        encoding="utf-8",
    )


def _env_workspace_root(root: Path) -> dict[str, str]:
    return {**os.environ, "METAGIT_WORKSPACE_PATH": str(root.resolve())}


def test_graph_suggest_accepts_leaf_config_path(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    _minimal_manifest(manifest)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["config", "graph", "suggest", "-c", str(manifest), "--json"],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "candidates" in result.output


def test_graph_suggest_verbose_prints_summary(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    _minimal_manifest(manifest)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["config", "graph", "suggest", "-c", str(manifest), "--verbose", "--json"],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    combined = result.output + (result.stderr or "")
    assert "candidates" in combined.lower() or "Graph suggest" in combined


def test_graph_suggest_default_human_summary_not_raw_json(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    _minimal_manifest(manifest)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["config", "graph", "suggest", "-c", str(manifest)],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Graph suggest summary" in result.output
    assert '"candidates"' not in result.output
    assert not result.output.strip().startswith("{")


def test_graph_export_accepts_leaf_config_path(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    _minimal_manifest(manifest)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["config", "graph", "export", "-c", str(manifest), "--format", "json"],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "statements" in result.output
