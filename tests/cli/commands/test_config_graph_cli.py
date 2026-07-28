#!/usr/bin/env python
"""CLI tests for config graph suggest/export leaf -c and verbose."""

from __future__ import annotations

import json
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


def _workspace_manifest(tmp_path: Path) -> tuple[Path, Path]:
    """Manifest plus a two-repo workspace where beta/worker imports alpha/api."""
    root = tmp_path / "workspace"
    alpha_repo = root / "alpha" / "api"
    beta_repo = root / "beta" / "worker"
    alpha_repo.mkdir(parents=True)
    beta_repo.mkdir(parents=True)
    (alpha_repo / ".git").mkdir()
    (beta_repo / ".git").mkdir()
    relative_api = os.path.relpath(alpha_repo, beta_repo)
    (beta_repo / "package.json").write_text(
        json.dumps({"name": "worker", "dependencies": {"api-client": f"file:{relative_api}"}}),
        encoding="utf-8",
    )
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: workspace\nkind: application\nworkspace:\n  projects:\n"
        "    - name: alpha\n      repos:\n        - name: api\n          path: alpha/api\n"
        "    - name: beta\n      repos:\n        - name: worker\n          path: beta/worker\n",
        encoding="utf-8",
    )
    return manifest, root


def test_config_validate_rejects_graph_relationship_without_id(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "name: demo\nkind: umbrella\nworkspace:\n  projects:\n    - name: p\n      repos: []\n"
        "graph:\n  relationships:\n    - from:\n        project: p\n      to:\n        project: p\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", "-c", str(manifest)])

    assert result.exit_code != 0
    combined = result.output + (result.stderr or "")
    assert "missing required 'id'" in combined
    assert "Failed to load" not in combined


def test_config_validate_passes_after_graph_suggest_apply(tmp_path: Path) -> None:
    """The documented apply -> validate workflow must succeed with no prior graph section."""
    manifest, root = _workspace_manifest(tmp_path)
    runner = CliRunner()
    env = _env_workspace_root(root)

    applied = runner.invoke(
        cli,
        ["config", "graph", "suggest", "-c", str(manifest), "--apply", "--json"],
        env=env,
        catch_exceptions=False,
    )
    assert applied.exit_code == 0, applied.output
    assert '"saved": true' in applied.output

    validated = runner.invoke(cli, ["config", "validate", "-c", str(manifest)], env=env)
    combined = validated.output + (validated.stderr or "")
    assert validated.exit_code == 0, combined
    assert "example-value" not in manifest.read_text(encoding="utf-8")


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
