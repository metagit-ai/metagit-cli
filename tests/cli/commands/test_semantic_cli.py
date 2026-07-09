#!/usr/bin/env python
"""CLI tests for metagit semantic (RFC-0010)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _env(root: Path) -> dict[str, str]:
  return {**os.environ, "METAGIT_WORKSPACE_PATH": str(root.resolve())}


def _write_manifest(root: Path) -> Path:
  path = root / ".metagit.yml"
  path.write_text(
    "name: workspace\nkind: application\ndescription: semantic fixture\n",
    encoding="utf-8",
  )
  return path


def test_semantic_declare_and_owners_json_authenticates_concept_id() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem() as tmp:
    root = Path(tmp)
    definition = _write_manifest(root)
    declare = runner.invoke(
      cli,
      [
        "semantic",
        "declare",
        "--definition",
        str(definition),
        "--concept",
        "Authentication",
        "--repository",
        "demo/api",
        "--pattern",
        "backend/auth/**",
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert declare.exit_code == 0, declare.output
    declare_payload = json.loads(declare.output)
    assert declare_payload["concept"]["concept_id"] == "authentication"

    owners = runner.invoke(
      cli,
      [
        "semantic",
        "owners",
        "--definition",
        str(definition),
        "--path",
        "backend/auth/token.py",
        "--repository",
        "demo/api",
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert owners.exit_code == 0, owners.output
    owners_payload = json.loads(owners.output)
    assert owners_payload["concepts"][0]["concept_id"] == "authentication"


def test_semantic_query_json_finds_declared_concept() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem() as tmp:
    root = Path(tmp)
    definition = _write_manifest(root)
    declare = runner.invoke(
      cli,
      [
        "semantic",
        "declare",
        "--definition",
        str(definition),
        "--concept",
        "Authentication",
        "--repository",
        "demo/api",
        "--pattern",
        "backend/auth/**",
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert declare.exit_code == 0, declare.output

    result = runner.invoke(
      cli,
      [
        "semantic",
        "query",
        "--definition",
        str(definition),
        "--concept",
        "authentication",
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["concept"]["concept_id"] == "authentication"
    assert payload["ownerships"][0]["repository"] == "demo/api"


def test_semantic_conflicts_json_returns_empty_hints() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem() as tmp:
    root = Path(tmp)
    definition = _write_manifest(root)

    result = runner.invoke(
      cli,
      [
        "semantic",
        "conflicts",
        "--definition",
        str(definition),
        "--repository",
        "demo/api",
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["repository"] == "demo/api"
    assert payload["hints"] == []
