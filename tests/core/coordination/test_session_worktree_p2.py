#!/usr/bin/env python
"""P2: per-task worktrees, self-repo refs, adopt, and post-create hooks."""

from __future__ import annotations

from pathlib import Path

from git import Repo

from metagit.core.appconfig.models import WorktreePostCreateHook
from metagit.core.coordination.branch_service import BranchService
from metagit.core.coordination.claim_service import ClaimService
from metagit.core.coordination.lease_service import LeaseService
from metagit.core.coordination.worktree_service import WorktreeService
from metagit.core.merge.service import MergeOrchestrator


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


def _services(
    session: Path,
    *,
    worktree_per_task: bool = False,
    post_create: list[WorktreePostCreateHook] | None = None,
    definition_path: str | None = None,
) -> tuple[BranchService, LeaseService, WorktreeService]:
    branches = BranchService(str(session), sync_root=str(session), definition_path=definition_path)
    leases = LeaseService(
        str(session),
        sync_root=str(session),
        definition_path=definition_path,
        branch_service=branches,
    )
    worktrees = WorktreeService(
        str(session),
        sync_root=str(session),
        definition_path=definition_path,
        lease_service=leases,
        worktree_per_task=worktree_per_task,
        post_create=post_create,
    )
    return branches, leases, worktrees


def _lease_and_branch(
    branches: BranchService,
    leases: LeaseService,
    *,
    repository: str,
    agent_id: str,
    task_id: str,
) -> str:
    allocation = branches.allocate(repository=repository, agent_id=agent_id, task_id=task_id)
    assert not isinstance(allocation, Exception), allocation
    lease = leases.acquire(
        repository=repository,
        agent_id=agent_id,
        task_id=task_id,
        branch=allocation.name,
    )
    assert not isinstance(lease, Exception), lease
    return allocation.name


def test_second_worktree_requires_worktree_per_task(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _init_repo(session / "demo" / "service-a")
    branches, leases, worktrees = _services(session)
    first = _lease_and_branch(branches, leases, repository="demo/service-a", agent_id="agent-1", task_id="one")
    second = _lease_and_branch(branches, leases, repository="demo/service-a", agent_id="agent-1", task_id="two")
    created = worktrees.create(repository="demo/service-a", agent_id="agent-1", task_id="one", branch=first)
    assert not isinstance(created, Exception), created
    refused = worktrees.create(repository="demo/service-a", agent_id="agent-1", task_id="two", branch=second)
    assert isinstance(refused, ValueError)
    assert "coordination.worktree_per_task" in str(refused)

    _, _, per_task = _services(session, worktree_per_task=True)
    again = per_task.create(repository="demo/service-a", agent_id="agent-1", task_id="two", branch=second)
    assert not isinstance(again, Exception), again
    assert again.path != created.path
    assert again.task_id == "two"
    assert Path(again.path).is_dir()
    assert "two" in Path(again.path).parts


def test_self_repository_ref_for_branch_lease_worktree_claim_and_merge(tmp_path: Path) -> None:
    session = tmp_path / "umbrella"
    repo = _init_repo(session)
    definition = session / ".metagit.yml"
    definition.write_text("kind: metagit\n", encoding="utf-8")
    repo.index.add([".metagit.yml"])
    repo.index.commit("manifest")
    caller_head = repo.head.commit.hexsha
    caller_branch = repo.active_branch.name

    branches, leases, worktrees = _services(session, definition_path=str(definition))
    branch_name = _lease_and_branch(branches, leases, repository=".", agent_id="agent-1", task_id="self-task")
    assert branch_name in repo.heads

    created = worktrees.create(repository="self", agent_id="agent-1", task_id="self-task", branch=branch_name)
    assert not isinstance(created, Exception), created
    assert created.repository == "."
    assert Path(created.path).is_dir()
    assert Path(created.path).resolve() != session.resolve()

    claim = ClaimService(str(session)).declare(
        repository="self",
        agent_id="agent-1",
        patterns=["README.md"],
        task_id="self-task",
    )
    assert not isinstance(claim, Exception), claim
    assert claim.repository == "."

    feature = repo.create_head("feature")
    feature.checkout()
    (session / "feature.txt").write_text("feature\n", encoding="utf-8")
    repo.index.add(["feature.txt"])
    repo.index.commit("feature")
    repo.heads[caller_branch].checkout()
    daily = repo.create_head("daily")

    merges = MergeOrchestrator(str(session))
    queued = merges.enqueue(".", "feature", "daily")
    assert not isinstance(queued, Exception), queued
    assert queued.repository == "."
    integrated = merges.integrate(queued.merge_id)
    assert not isinstance(integrated, Exception), integrated
    assert integrated.status == "succeeded"
    assert repo.head.commit.hexsha == caller_head
    assert repo.active_branch.name == caller_branch
    assert repo.heads["daily"].commit.hexsha != caller_head


def test_adopt_registers_existing_worktree_without_recreating_it(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    repo = _init_repo(session / "demo" / "service-a")
    checkout = tmp_path / "hand-made"
    repo.git.worktree("add", "-b", "agent/adopted", str(checkout))
    before = repo.git.worktree("list", "--porcelain")

    worktrees = WorktreeService(str(session), sync_root=str(session))
    adopted = worktrees.adopt(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="adopt-1",
        path=str(checkout),
    )
    assert not isinstance(adopted, Exception), adopted
    assert Path(adopted.path).resolve() == checkout.resolve()
    assert adopted.branch == "agent/adopted"
    assert adopted.lease_id == ""
    assert repo.git.worktree("list", "--porcelain") == before

    again = worktrees.adopt(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="adopt-1",
        path=str(checkout),
    )
    assert not isinstance(again, Exception), again
    assert again.worktree_id == adopted.worktree_id

    detached = tmp_path / "detached"
    repo.git.worktree("add", "--detach", str(detached), "HEAD")
    refused = worktrees.adopt(
        repository="demo/service-a",
        agent_id="agent-2",
        task_id="adopt-2",
        path=str(detached),
    )
    assert isinstance(refused, ValueError)
    assert "--branch" in str(refused)


def test_post_create_refuses_tracked_symlink_and_links_gitignored_env(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    repo = _init_repo(session / "demo" / "service-a")
    source = session / "demo" / "service-a"
    (source / ".gitignore").write_text(".env\n", encoding="utf-8")
    (source / ".env").write_text("SECRET=1\n", encoding="utf-8")
    repo.index.add([".gitignore"])
    repo.index.commit("ignore env")

    branches, leases, refused_service = _services(
        session,
        post_create=[WorktreePostCreateHook(symlink="README.md")],
    )
    branch_name = _lease_and_branch(
        branches,
        leases,
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="hooks",
    )
    refused = refused_service.create(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="hooks",
        branch=branch_name,
    )
    assert isinstance(refused, ValueError)
    assert "coordination.worktree.post_create" in str(refused)
    listed = repo.git.worktree("list", "--porcelain")
    assert "README.md" not in listed

    _, _, linked = _services(session, post_create=[WorktreePostCreateHook(symlink=".env")])
    created = linked.create(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="hooks",
        branch=branch_name,
    )
    assert not isinstance(created, Exception), created
    env_link = Path(created.path) / ".env"
    assert env_link.is_symlink()
    assert env_link.read_text(encoding="utf-8") == "SECRET=1\n"
