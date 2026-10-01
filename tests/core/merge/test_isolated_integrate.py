#!/usr/bin/env python
"""Merge integrate must not move any checkout it did not create."""

from __future__ import annotations

import hashlib
from pathlib import Path

from git import Repo

from metagit.core.merge.git_ops import attempt_merge


def _commit_file(repo: Repo, relative_path: str, content: str, message: str) -> str:
    root = Path(repo.working_tree_dir or "")
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    repo.index.add([relative_path])
    return repo.index.commit(message).hexsha


def _init(path: Path) -> Repo:
    repo = Repo.init(path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Metagit Test")
        writer.set_value("user", "email", "metagit@example.test")
    _commit_file(repo, "README.md", "base\n", "initial commit")
    repo.create_head("main")
    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)
    return repo


def _fingerprint(path: Path) -> tuple[str, str, str, tuple[tuple[str, str], ...]]:
    repo = Repo(path)
    git_dir = Path(repo.git.rev_parse("--git-dir"))
    if not git_dir.is_absolute():
        git_dir = (path / git_dir).resolve()
    index = git_dir / "index"
    files: list[tuple[str, str]] = []
    for item in sorted(path.rglob("*")):
        if not item.is_file() or ".git" in item.parts:
            continue
        files.append((str(item.relative_to(path)), hashlib.sha256(item.read_bytes()).hexdigest()))
    return (
        repo.head.commit.hexsha,
        repo.active_branch.name,
        hashlib.sha256(index.read_bytes()).hexdigest(),
        tuple(files),
    )


def test_integrate_leaves_other_worktree_byte_identical_and_moves_target(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    repo.create_head("branch-a", repo.heads.main)
    worktree = tmp_path / "wt-a"
    repo.git.worktree("add", str(worktree), "branch-a")
    repo.create_head("branch-b", repo.heads.main)
    repo.head.reference = repo.heads["branch-b"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "feature.txt", "from-b\n", "add feature")
    repo.create_head("daily", repo.heads.main)
    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)
    before = _fingerprint(worktree)
    daily_before = repo.heads.daily.commit.hexsha

    result = attempt_merge(str(tmp_path / "repo"), "branch-b", "daily")

    assert not isinstance(result, Exception)
    assert result.ok is True
    assert _fingerprint(worktree) == before
    assert repo.heads.daily.commit.hexsha != daily_before
    assert repo.git.show("daily:feature.txt").rstrip("\n") == "from-b"
    assert Repo(worktree).active_branch.name == "branch-a"


def test_integrate_refuses_when_target_is_checked_out(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    repo.create_head("branch-b", repo.heads.main)
    repo.head.reference = repo.heads["branch-b"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "feature.txt", "from-b\n", "add feature")
    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)

    result = attempt_merge(str(tmp_path / "repo"), "branch-b", "main")

    assert isinstance(result, ValueError)
    assert "No flag overrides this" in str(result)
    assert repo.active_branch.name == "main"
    assert not (tmp_path / "repo" / "feature.txt").exists()
