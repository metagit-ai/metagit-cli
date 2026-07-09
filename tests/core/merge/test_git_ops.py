#!/usr/bin/env python
"""Tests for GitPython merge helpers."""

from __future__ import annotations

from pathlib import Path

from git import Repo

from metagit.core.merge.git_ops import attempt_merge, ensure_branch


def _commit_file(repo: Repo, relative_path: str, content: str, message: str) -> str:
    path = Path(repo.working_tree_dir or "") / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo.index.add([relative_path])
    return repo.index.commit(message).hexsha


def _repo(tmp_path: Path) -> Repo:
    repo = Repo.init(tmp_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Metagit Test")
        writer.set_value("user", "email", "metagit@example.test")
    _commit_file(repo, "README.md", "base\n", "initial commit")
    repo.create_head("main")
    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)
    return repo


def test_ensure_branch_creates_missing_branch_from_start_point(tmp_path) -> None:
    repo = _repo(tmp_path)

    result = ensure_branch(str(tmp_path), "integration/test", "main")

    assert result is None
    assert "integration/test" in [head.name for head in repo.heads]
    assert repo.heads["integration/test"].commit.hexsha == repo.heads.main.commit.hexsha


def test_attempt_merge_returns_success_commit_sha(tmp_path) -> None:
    repo = _repo(tmp_path)
    repo.create_head("agent/change", repo.heads.main)
    repo.head.reference = repo.heads["agent/change"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "feature.txt", "feature\n", "add feature")
    repo.create_head("integration/test", repo.heads.main)

    result = attempt_merge(str(tmp_path), "agent/change", "integration/test")

    assert not isinstance(result, Exception)
    assert result.ok is True
    assert result.commit_sha == repo.head.commit.hexsha
    assert result.conflict is None
    assert repo.active_branch.name == "integration/test"
    assert (tmp_path / "feature.txt").read_text(encoding="utf-8") == "feature\n"


def test_attempt_merge_aborts_conflict_and_returns_conflict_files(tmp_path) -> None:
    repo = _repo(tmp_path)
    repo.create_head("agent/change", repo.heads.main)
    repo.head.reference = repo.heads["agent/change"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "shared.txt", "agent\n", "agent edit")
    repo.create_head("integration/test", repo.heads.main)
    repo.head.reference = repo.heads["integration/test"]
    repo.head.reset(index=True, working_tree=True)
    target_sha = _commit_file(repo, "shared.txt", "integration\n", "integration edit")

    result = attempt_merge(str(tmp_path), "agent/change", "integration/test")

    assert not isinstance(result, Exception)
    assert result.ok is False
    assert result.conflict is not None
    assert result.conflict.files == ["shared.txt"]
    assert result.commit_sha is None
    assert repo.active_branch.name == "integration/test"
    assert repo.head.commit.hexsha == target_sha
    assert not (tmp_path / ".git" / "MERGE_HEAD").exists()
    assert (tmp_path / "shared.txt").read_text(encoding="utf-8") == "integration\n"
