#!/usr/bin/env python
"""Branch prefix policy for ACL allocations."""

from __future__ import annotations

from pathlib import Path

from git import Repo

from metagit.core.coordination.branch_service import BranchService


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(path))
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "Metagit Test")
        writer.set_value("user", "email", "metagit@example.test")
    readme = path / "README.md"
    readme.write_text("hello\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("init")


def test_default_prefixes_allow_agent_and_reject_custom(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _init_repo(session / "demo" / "service-a")
    service = BranchService(str(session), sync_root=str(session))

    allowed = service.allocate(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="foo",
        branch_name="agent/foo",
    )
    rejected = service.allocate(
        repository="demo/service-a",
        agent_id="agent-1",
        task_id="foo",
        branch_name="zloeber/jax/foo",
    )

    assert not isinstance(allowed, Exception)
    assert allowed.name == "agent/foo"
    assert isinstance(rejected, ValueError)
    assert "coordination.allowed_branch_prefixes" in str(rejected)


def test_custom_prefixes_allow_person_agent_and_reject_agent(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    _init_repo(session / "demo" / "service-a")
    service = BranchService(
        str(session),
        sync_root=str(session),
        allowed_branch_prefixes=["zloeber/jax/"],
        branch_pattern="zloeber/jax/{task_id}[-{slug}]",
    )

    allowed = service.allocate(
        repository="demo/service-a",
        agent_id="jax",
        task_id="foo",
        branch_name="zloeber/jax/foo",
    )
    rejected = service.allocate(
        repository="demo/service-a",
        agent_id="jax",
        task_id="foo",
        branch_name="agent/foo",
    )

    names = [head.name for head in Repo(session / "demo" / "service-a").heads]
    assert not isinstance(allowed, Exception)
    assert allowed.name == "zloeber/jax/foo"
    assert isinstance(rejected, ValueError)
    assert "coordination.allowed_branch_prefixes" in str(rejected)
    assert "agent/foo" not in names
    assert "zloeber/jax/foo" in names
