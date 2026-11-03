#!/usr/bin/env python
"""Tests for GitPython merge helpers."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from git import GitCommandError, Repo

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

    caller_head = repo.head.commit.hexsha
    caller_branch = repo.active_branch.name
    caller_file = (tmp_path / "feature.txt").read_bytes()

    result = attempt_merge(str(tmp_path), "agent/change", "integration/test")

    assert not isinstance(result, Exception)
    assert result.ok is True
    assert result.conflict is None
    assert repo.active_branch.name == caller_branch
    assert repo.head.commit.hexsha == caller_head
    assert (tmp_path / "feature.txt").read_bytes() == caller_file
    assert result.commit_sha == repo.heads["integration/test"].commit.hexsha
    assert repo.git.show("integration/test:feature.txt").rstrip("\r\n") == "feature"


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
    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)
    caller_head = repo.head.commit.hexsha

    result = attempt_merge(str(tmp_path), "agent/change", "integration/test")

    assert not isinstance(result, Exception)
    assert result.ok is False
    assert result.conflict is not None
    assert result.conflict.files == ["shared.txt"]
    assert result.commit_sha is None
    assert repo.active_branch.name == "main"
    assert repo.head.commit.hexsha == caller_head
    assert repo.heads["integration/test"].commit.hexsha == target_sha
    assert not (tmp_path / ".git" / "MERGE_HEAD").exists()
    assert not (tmp_path / "shared.txt").exists()


def test_regenerate_takes_a_deleted_gitignored_path(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit_file(repo, "generated/index.txt", "v1\n", "track index")
    repo.create_head("integration/test", repo.heads.main)
    repo.head.reference = repo.heads["integration/test"]
    repo.head.reset(index=True, working_tree=True)
    repo.git.rm("generated/index.txt")
    (tmp_path / ".gitignore").write_text("generated/\n", encoding="utf-8")
    repo.index.add([".gitignore"])
    repo.index.commit("stop tracking generated index")

    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)
    repo.create_head("agent/change", repo.heads.main)
    repo.head.reference = repo.heads["agent/change"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "README.md", "from agent\n", "agent readme")
    _commit_file(repo, "generated/index.txt", "v2\n", "agent index")
    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)

    script = (
        "from pathlib import Path; "
        "Path('generated').mkdir(exist_ok=True); "
        "Path('generated/index.txt').write_text('rebuilt\\n')"
    )
    command = f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"
    result = attempt_merge(
        str(tmp_path),
        "agent/change",
        "integration/test",
        regenerate={"generated/*": command},
    )

    assert not isinstance(result, Exception), result
    assert result.ok is True
    assert repo.git.show("integration/test:README.md").rstrip("\r\n") == "from agent"
    try:
        repo.git.show("integration/test:generated/index.txt")
        raise AssertionError("deleted generated index was added back")
    except GitCommandError:
        pass
