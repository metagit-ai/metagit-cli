#!/usr/bin/env python
"""Tests for RFC-0011 merge validators and gated promote."""

from __future__ import annotations

import sys
from pathlib import Path

from git import Repo

from metagit.core.merge.service import MergeOrchestrator
from metagit.core.merge.validators import run_validators


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
  return repo


def _clean_merge_request(tmp_path: Path, *, validators: list[str] | None = None):
  repo_path = tmp_path / "repo"
  repo = _repo(repo_path)
  repo.create_head("agent/change", repo.heads.main)
  repo.head.reference = repo.heads["agent/change"]
  repo.head.reset(index=True, working_tree=True)
  _commit_file(repo, "feature.txt", "feature\n", "add feature")
  repo.create_head("integration/test", repo.heads.main)
  repo.head.reference = repo.heads.main
  repo.head.reset(index=True, working_tree=True)
  orchestrator = MergeOrchestrator(str(tmp_path / "session"), validators=validators)
  request = orchestrator.enqueue(
    "project/repo",
    "agent/change",
    "integration/test",
    repo_path=str(repo_path),
  )
  assert not isinstance(request, Exception)
  return repo_path, orchestrator, request


def test_empty_validators_return_success(tmp_path: Path) -> None:
  repo_path = tmp_path / "repo"
  _repo(repo_path)

  result = run_validators(str(repo_path), [])

  assert result.ok is True
  assert result.commands == []


def test_failing_validator_marks_request_validation_failed(tmp_path: Path) -> None:
  command = f"{sys.executable} -c 'import sys; sys.exit(2)'"
  _, orchestrator, request = _clean_merge_request(tmp_path, validators=[command])

  integrated = orchestrator.integrate(request.merge_id)

  assert not isinstance(integrated, Exception)
  assert integrated.status == "validation_failed"
  assert integrated.validation is not None
  assert integrated.validation.ok is False
  assert integrated.validation.commands[0].cmd == command
  assert integrated.validation.commands[0].exit_code == 2


def test_promote_is_blocked_after_failed_validation(tmp_path: Path) -> None:
  command = f"{sys.executable} -c 'import sys; sys.exit(2)'"
  _, orchestrator, request = _clean_merge_request(tmp_path, validators=[command])
  integrated = orchestrator.integrate(request.merge_id)
  assert not isinstance(integrated, Exception)

  promoted = orchestrator.promote(request.merge_id, "main")

  assert isinstance(promoted, Exception)
  assert "validation failed" in str(promoted)


def test_promote_merges_integration_branch_after_success(tmp_path: Path) -> None:
  repo_path, orchestrator, request = _clean_merge_request(tmp_path)
  integrated = orchestrator.integrate(request.merge_id)
  assert not isinstance(integrated, Exception)
  assert integrated.status == "succeeded"
  assert integrated.validation is not None
  assert integrated.validation.ok is True

  promoted = orchestrator.promote(request.merge_id, "main")
  repo = Repo(repo_path)

  assert not isinstance(promoted, Exception)
  assert repo.active_branch.name == "main"
  assert (repo_path / "feature.txt").read_text(encoding="utf-8") == "feature\n"
