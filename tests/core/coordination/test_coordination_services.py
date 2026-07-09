#!/usr/bin/env python
"""Unit tests for ACL coordination services (RFC-0007)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from git import Repo

from metagit.core.context.event_service import WorkspaceEventService
from metagit.core.coordination.branch_service import BranchService
from metagit.core.coordination.claim_service import ClaimService, patterns_overlap
from metagit.core.coordination.lease_service import LeaseService
from metagit.core.coordination.ttl import parse_ttl_seconds
from metagit.core.coordination.worktree_service import WorktreeService


def _init_repo(path: Path) -> Repo:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(path))
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("init")
    return repo


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    session = tmp_path / "session"
    session.mkdir()
    repo_path = session / "demo" / "service-a"
    _init_repo(repo_path)
    return session


def test_parse_ttl_seconds_shared() -> None:
    assert parse_ttl_seconds("30") == 30
    assert parse_ttl_seconds("30m") == 1800
    assert parse_ttl_seconds("2h") == 7200


def test_branch_allocate_and_conflict(workspace: Path) -> None:
    service = BranchService(str(workspace), sync_root=str(workspace))
    first = service.allocate(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
        description="auth",
    )
    assert not isinstance(first, Exception)
    assert first.name.startswith("agent/412")
    conflict = service.allocate(
        repository="demo/service-a",
        agent_id="agent-2",
        task_id="412",
        description="auth",
    )
    assert isinstance(conflict, Exception)


def test_lease_blocks_second_agent(workspace: Path) -> None:
    branches = BranchService(str(workspace), sync_root=str(workspace))
    leases = LeaseService(
        str(workspace),
        sync_root=str(workspace),
        branch_service=branches,
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
        ttl="30m",
    )
    assert not isinstance(lease, Exception)
    blocked = leases.acquire(
        repository="demo/service-a",
        agent_id="agent-2",
        task_id="413",
        branch=allocation.name,
        ttl="30m",
    )
    assert isinstance(blocked, Exception)


def test_lease_auto_expires(workspace: Path) -> None:
    clock = {"now": datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)}

    def now_iso() -> str:
        return clock["now"].isoformat()

    def clock_fn() -> datetime:
        return clock["now"]

    branches = BranchService(
        str(workspace),
        sync_root=str(workspace),
        now_fn=now_iso,
    )
    leases = LeaseService(
        str(workspace),
        sync_root=str(workspace),
        branch_service=branches,
        now_fn=now_iso,
        clock_fn=clock_fn,
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
    clock["now"] = clock["now"] + timedelta(seconds=120)
    listed = leases.list()
    assert not isinstance(listed, Exception)
    assert listed.leases[0].status == "expired"


def test_worktree_create_requires_lease_and_isolates(workspace: Path) -> None:
    branches = BranchService(str(workspace), sync_root=str(workspace))
    leases = LeaseService(
        str(workspace),
        sync_root=str(workspace),
        branch_service=branches,
    )
    worktrees = WorktreeService(
        str(workspace),
        sync_root=str(workspace),
        lease_service=leases,
    )
    a1 = branches.allocate(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
    )
    a2 = branches.allocate(
        repository="demo/service-a",
        agent_id="agent-2",
        task_id="413",
    )
    assert not isinstance(a1, Exception)
    assert not isinstance(a2, Exception)
    missing = worktrees.create(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
        branch=a1.name,
    )
    assert isinstance(missing, Exception)
    lease1 = leases.acquire(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
        branch=a1.name,
    )
    lease2 = leases.acquire(
        repository="demo/service-a",
        agent_id="agent-2",
        task_id="413",
        branch=a2.name,
    )
    assert not isinstance(lease1, Exception)
    assert not isinstance(lease2, Exception)
    wt1 = worktrees.create(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
        branch=a1.name,
    )
    wt2 = worktrees.create(
        repository="demo/service-a",
        agent_id="agent-2",
        task_id="413",
        branch=a2.name,
    )
    assert not isinstance(wt1, Exception)
    assert not isinstance(wt2, Exception)
    assert wt1.path != wt2.path
    assert Path(wt1.path).is_dir()
    assert Path(wt2.path).is_dir()
    assert (Path(wt1.path) / ".metagit-agent.json").is_file()
    manifest = worktrees.manifest("agent-1")
    assert not isinstance(manifest, Exception)
    assert manifest.branch == a1.name


def test_claim_overlap_detection(workspace: Path) -> None:
    assert patterns_overlap("backend/auth/*", "backend/auth/token.py")
    assert patterns_overlap("backend/auth/*", "backend/auth/**")
    assert not patterns_overlap("backend/auth/*", "frontend/*")
    service = ClaimService(str(workspace))
    first = service.declare(
        repository="demo/service-a",
        agent_id="agent-1",
        patterns=["backend/auth/*"],
    )
    assert not isinstance(first, Exception)
    check = service.check(
        repository="demo/service-a",
        patterns=["backend/auth/token.py"],
        agent_id="agent-2",
    )
    assert not isinstance(check, Exception)
    assert check.conflicts
    assert check.conflicts[0].owner == "agent-1"
    conflict = service.declare(
        repository="demo/service-a",
        agent_id="agent-2",
        patterns=["backend/auth/*"],
        allow_conflicts=False,
    )
    from metagit.core.coordination.models import ClaimCheckResult

    assert isinstance(conflict, ClaimCheckResult)


def test_acl_events_appear_in_workspace_feed(workspace: Path) -> None:
    branches = BranchService(str(workspace), sync_root=str(workspace))
    result = branches.allocate(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="412",
        create_git_branch=True,
    )
    assert not isinstance(result, Exception)
    events = WorkspaceEventService(str(workspace)).list_events()
    acl = [row for row in events.events if row.source == "acl"]
    assert any(row.kind == "BranchAllocated" for row in acl)
