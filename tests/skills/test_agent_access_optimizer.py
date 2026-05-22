#!/usr/bin/env python3
"""Tests for metagit-agent-access optimizer script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
  Path(__file__).resolve().parents[2]
  / "src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py"
)


def test_audit_json_on_temp_repo(tmp_path: Path) -> None:
  (tmp_path / "README.md").write_text("# Demo\n\nA sample project.\n", encoding="utf-8")
  (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
  result = subprocess.run(
    [sys.executable, str(SCRIPT), str(tmp_path), "--json"],
    check=True,
    capture_output=True,
    text=True,
  )
  payload = json.loads(result.stdout)
  assert payload["has_llms_txt"] is False
  assert "llms.txt" in payload["gaps"]


def test_apply_creates_llms_and_comment(tmp_path: Path) -> None:
  (tmp_path / "README.md").write_text("# Demo\n\nSample.\n", encoding="utf-8")
  subprocess.run(
    [sys.executable, str(SCRIPT), str(tmp_path), "--apply", "--json"],
    check=True,
    capture_output=True,
    text=True,
  )
  assert (tmp_path / "llms.txt").is_file()
  assert (tmp_path / "AGENTS.md").is_file()
  readme = (tmp_path / "README.md").read_text(encoding="utf-8")
  assert "agent-access:start" in readme
