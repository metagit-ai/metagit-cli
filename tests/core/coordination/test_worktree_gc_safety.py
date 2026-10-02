#!/usr/bin/env python
"""gc and destroy must not delete checkouts that still hold work."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from git import Repo

from metagit.core.coordination.branch_service import BranchService
from metagit.core.coordination.lease_service import LeaseService
from metagit.core.coordination.worktree_service import WorktreeService


def _init_repo(path: Path) -> Repo:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(path))
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Metagit Test")
        writer.set_value("user", "email", "metagit@example.test")
    readme = path / "README.md"
    readme.write_text("hello\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("init")
    return repo


def _expired_worktree(tmp_path: Path) -> tuple[WorktreeService, str]:
    session = tmp_path / "session"
    session.mkdir()
    _init_repo(session / "demo" / "service-a")
    clock = {"now": datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)}

    def now_iso() -> str:
        return clock["now"].isoformat()

    def clock_fn() -> datetime:
        return clock["now"]

    branches = BranchService(str(session), sync_root=str(session), now_fn=now_iso)
    leases = LeaseService(
        str(session),
        sync_root=str(session),
        branch_service=branches,
        now_fn=now_iso,
        clock_fn=clock_fn,
    )
    worktrees = WorktreeService(
        str(session),
        sync_root=str(session),
        lease_service=leases,
        now_fn=now_iso,
    )
    allocation = branches.allocate(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
    )
    assert not isinstance(allocation, Exception)
    lease = leases.acquire(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
        branch=allocation.name,
        ttl="60",
    )
    assert not isinstance(lease, Exception)
    created = worktrees.create(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
        branch=allocation.name,
    )
    assert not isinstance(created, Exception)
    clock["now"] = clock["now"] + timedelta(seconds=120)
    return worktrees, created.path


def test_gc_skips_expired_worktree_with_uncommitted_change(tmp_path: Path) -> None:
    worktrees, checkout = _expired_worktree(tmp_path)
    dirty = Path(checkout) / "README.md"
    dirty.write_text("changed\n", encoding="utf-8")

    preview = worktrees.gc(dry_run=True)
    assert not isinstance(preview, Exception)
    assert preview.dry_run is True
    assert preview.destroyed == []
    assert preview.skipped
    assert "uncommitted changes" in preview.skipped[0].message
    assert "--force" in preview.skipped[0].message
    assert dirty.read_text(encoding="utf-8") == "changed\n"

    skipped = worktrees.gc()
    assert not isinstance(skipped, Exception)
    assert skipped.destroyed == []
    assert "uncommitted changes" in skipped.skipped[0].message
    assert Path(checkout).is_dir()

    forced = worktrees.gc(force=True)
    assert not isinstance(forced, Exception)
    assert len(forced.destroyed) == 1
    assert not Path(checkout).exists()


def test_destroy_refuses_uncommitted_work_unless_forced(tmp_path: Path) -> None:
    worktrees, checkout = _expired_worktree(tmp_path)
    (Path(checkout) / "notes.txt").write_text("keep me\n", encoding="utf-8")
    listed = worktrees.list(status="active")
    assert not isinstance(listed, Exception)
    worktree_id = listed.worktrees[0].worktree_id

    refused = worktrees.destroy(worktree_id=worktree_id)
    assert isinstance(refused, ValueError)
    assert "untracked files" in str(refused)
    assert "--force" in str(refused)
    assert Path(checkout).is_dir()

    removed = worktrees.destroy(worktree_id=worktree_id, force=True)
    assert not isinstance(removed, Exception)
    assert not Path(checkout).exists()
