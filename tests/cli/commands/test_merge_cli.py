#!/usr/bin/env python
"""CLI tests for metagit merge commands (RFC-0011)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner
from git import Repo

from metagit.cli.main import cli


def _env(root: Path) -> dict[str, str]:
  return {**os.environ, "METAGIT_WORKSPACE_PATH": str(root.resolve())}


def _write_manifest(root: Path) -> Path:
  path = root / ".metagit.yml"
  path.write_text(
    "name: workspace\nkind: application\ndescription: merge fixture\n",
    encoding="utf-8",
  )
  return path


def _commit_file(repo: Repo, relative_path: str, content: str, message: str) -> str:
  path = Path(repo.working_tree_dir or "") / relative_path
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding="utf-8")
  repo.index.add([relative_path])
  return repo.index.commit(message).hexsha


def _repo(path: Path) -> Repo:
  repo = Repo.init(path)
  with repo.config_writer() as writer:
    writer.set_value("user", "name", "Metagit Test")
    writer.set_value("user", "email", "metagit@example.test")
  _commit_file(repo, "README.md", "base\n", "initial commit")
  repo.create_head("main")
  repo.head.reference = repo.heads.main
  repo.head.reset(index=True, working_tree=True)
  repo.create_head("agent/change", repo.heads.main)
  repo.head.reference = repo.heads["agent/change"]
  repo.head.reset(index=True, working_tree=True)
  _commit_file(repo, "feature.txt", "feature\n", "add feature")
  repo.create_head("integration/test", repo.heads.main)
  repo.head.reference = repo.heads.main
  repo.head.reset(index=True, working_tree=True)
  return repo


def test_merge_group_is_registered() -> None:
  runner = CliRunner()

  result = runner.invoke(cli, ["merge", "--help"], catch_exceptions=False)

  assert result.exit_code == 0, result.output
  assert "enqueue" in result.output
  assert "integrate" in result.output


def test_merge_enqueue_integrate_status_and_promote_json() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem() as tmp:
    root = Path(tmp)
    definition = _write_manifest(root)
    repo_path = root / "repo"
    _repo(repo_path)

    enqueue = runner.invoke(
      cli,
      [
        "merge",
        "enqueue",
        "--definition",
        str(definition),
        "--repository",
        "demo/repo",
        "--branch",
        "agent/change",
        "--into",
        "integration/test",
        "--repo-path",
        str(repo_path),
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert enqueue.exit_code == 0, enqueue.output
    payload = json.loads(enqueue.output)
    assert payload["repository"] == "demo/repo"
    assert payload["status"] == "queued"

    integrate = runner.invoke(
      cli,
      [
        "merge",
        "integrate",
        "--definition",
        str(definition),
        "--merge-id",
        payload["merge_id"],
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert integrate.exit_code == 0, integrate.output
    integrated = json.loads(integrate.output)
    assert integrated["status"] == "succeeded"

    status = runner.invoke(
      cli,
      [
        "merge",
        "status",
        "--definition",
        str(definition),
        "--repository",
        "demo/repo",
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert status.exit_code == 0, status.output
    rows = json.loads(status.output)
    assert [row["merge_id"] for row in rows] == [payload["merge_id"]]

    promote = runner.invoke(
      cli,
      [
        "merge",
        "promote",
        "--definition",
        str(definition),
        "--merge-id",
        payload["merge_id"],
        "--into",
        "main",
        "--json",
      ],
      env=_env(root),
      catch_exceptions=False,
    )
    assert promote.exit_code == 0, promote.output
    promoted = json.loads(promote.output)
    assert promoted["status"] == "succeeded"
    assert Repo(repo_path).active_branch.name == "main"
    assert (repo_path / "feature.txt").read_text(encoding="utf-8") == "feature\n"
