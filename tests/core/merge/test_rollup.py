#!/usr/bin/env python
"""Rollup rebuilds mapped generated files and stops on any other conflict."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from git import Repo

from metagit.core.merge.service import MergeOrchestrator

_INDEX = "knowledge/notes/_index.md"
_RENDERED = "rendered\n"


def _init_repo(path: Path) -> Repo:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(path))
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Metagit Test")
        writer.set_value("user", "email", "metagit@example.test")
    return repo


def _commit(repo: Repo, relative: str, text: str, message: str) -> None:
    path = Path(repo.working_tree_dir) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    repo.index.add([relative])
    repo.index.commit(message)


def _branch_from_main(repo: Repo, name: str, relative: str, text: str) -> None:
    main = repo.active_branch.name
    head = repo.create_head(name)
    head.checkout()
    _commit(repo, relative, text, name)
    repo.heads[main].checkout()


def _render_command() -> str:
    script = f"from pathlib import Path; Path({_INDEX!r}).write_text({_RENDERED!r})"
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"


def test_rollup_rebuilds_a_mapped_generated_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, _INDEX, "base\n", "init")
    _branch_from_main(repo, "session-a", _INDEX, "from-a\n")
    _branch_from_main(repo, "session-b", _INDEX, "from-b\n")
    caller_head = repo.head.commit.hexsha
    caller_branch = repo.active_branch.name

    service = MergeOrchestrator(str(tmp_path), regenerate={f"knowledge/*/_index.md": _render_command()})
    result = service.rollup("demo/service", "daily", caller_branch, ["session-a", "session-b", "session-a"], repo_path=str(tmp_path))
    assert not isinstance(result, Exception), result
    assert result.merged == ["session-a", "session-b"]
    assert result.skipped == ["session-a"]
    assert result.conflicted == []
    assert result.failed == []
    blob = repo.git.show(f"daily:{_INDEX}")
    assert blob.rstrip("\n") == _RENDERED.rstrip("\n")
    assert repo.head.commit.hexsha == caller_head
    assert repo.active_branch.name == caller_branch


def test_rollup_stops_when_an_unmapped_file_conflicts(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, _INDEX, "base\n", "init index")
    _commit(repo, "README.md", "base\n", "init readme")
    main = repo.active_branch.name

    for name in ("session-a", "session-b"):
        repo.create_head(name).checkout()
        _commit(repo, _INDEX, f"{name}-index\n", f"{name} index")
        _commit(repo, "README.md", f"{name}-readme\n", f"{name} readme")
        repo.heads[main].checkout()

    caller_head = repo.head.commit.hexsha
    service = MergeOrchestrator(str(tmp_path), regenerate={"knowledge/*/_index.md": _render_command()})
    result = service.rollup("demo/service", "daily", main, ["session-a", "session-b"], repo_path=str(tmp_path))
    assert not isinstance(result, Exception), result
    assert result.merged == ["session-a"]
    assert len(result.conflicted) == 1
    conflict = result.conflicted[0]
    assert conflict.branch == "session-b"
    assert conflict.into == "daily"
    assert "README.md" in conflict.files
    assert repo.head.commit.hexsha == caller_head
    assert repo.active_branch.name == main
    readme = repo.git.show("daily:README.md")
    assert readme.rstrip("\n") == "session-a-readme"
