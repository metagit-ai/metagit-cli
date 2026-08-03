#!/usr/bin/env python
"""CLI tests for metagit context switch."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _write_workspace(tmp_path: Path) -> tuple[Path, Path]:
  sync = tmp_path / "sync"
  (sync / "attune" / "attune").mkdir(parents=True)
  manifest = tmp_path / ".metagit.yml"
  manifest.write_text(
    "\n".join(
      [
        "name: ws",
        "kind: umbrella",
        "workspace:",
        "  projects:",
        "    - name: attune",
        "      tags:",
        "        hermes_profile: attune",
        "      repos:",
        "        - name: attune",
        "          url: https://example.com/attune.git",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  app_cfg = tmp_path / "metagit.config.yaml"
  app_cfg.write_text(
    "\n".join(
      [
        "config:",
        "  description: test",
        "  workspace:",
        f"    path: {sync.as_posix()}",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return app_cfg, manifest


def test_context_switch_json_ok(tmp_path: Path) -> None:
  app_cfg, manifest = _write_workspace(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "context",
      "switch",
      "attune",
      "--json",
      "--no-pack",
      "--no-prompt",
      "--no-objective",
      "-c",
      str(manifest),
    ],
    catch_exceptions=False,
  )
  assert result.exit_code == 0
  payload = json.loads(result.output)
  assert payload["ok"] is True
  assert payload["env"]["METAGIT_PROJECT"] == "attune"
  assert payload["env"]["METAGIT_AGENT_MODE"] == "true"
  assert payload["env"]["METAGIT_HERMES_PROFILE"] == "attune"


def test_context_switch_default_stdout_is_exports_only(tmp_path: Path) -> None:
  app_cfg, manifest = _write_workspace(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "context",
      "switch",
      "attune",
      "--no-pack",
      "--no-prompt",
      "--no-objective",
      "-c",
      str(manifest),
    ],
    catch_exceptions=False,
  )
  assert result.exit_code == 0
  lines = [line for line in result.output.splitlines() if line.strip()]
  assert lines
  assert all(line.startswith("export ") for line in lines)
  assert any("METAGIT_AGENT_MODE=" in line for line in lines)


def test_context_switch_unknown_project_exits_nonzero(tmp_path: Path) -> None:
  app_cfg, manifest = _write_workspace(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "context",
      "switch",
      "missing",
      "--no-pack",
      "--no-prompt",
      "--no-objective",
      "-c",
      str(manifest),
    ],
  )
  assert result.exit_code != 0
