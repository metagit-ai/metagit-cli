#!/usr/bin/env python
"""Tests for the RFC-0011 merge orchestrator service."""

from __future__ import annotations

from pathlib import Path

from git import Repo

from metagit.core.merge.events import MergeEventStore
from metagit.core.merge.service import MergeOrchestrator


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


def test_enqueue_creates_queued_merge_request(tmp_path) -> None:
    repo_path = tmp_path / "repo"
    _repo(repo_path)
    orchestrator = MergeOrchestrator(str(tmp_path / "session"))

    request = orchestrator.enqueue(
        "project/repo",
        "agent/change",
        "integration/test",
        node_id="node-1",
        agent_id="agent-1",
        repo_path=str(repo_path),
    )

    assert not isinstance(request, Exception)
    assert request.repository == "project/repo"
    assert request.status == "queued"
    assert request.node_id == "node-1"
    assert request.agent_id == "agent-1"
    assert request.repo_path == str(repo_path)

    status = orchestrator.status(repository="project/repo")
    events = MergeEventStore(str(tmp_path / "session")).list_events()

    assert not isinstance(status, Exception)
    assert [row.merge_id for row in status] == [request.merge_id]
    assert not isinstance(events, Exception)
    assert [event.type for event in events] == ["MergeEnqueued"]


def test_integrate_clean_branch_succeeds_and_emits_event(tmp_path) -> None:
    repo_path = tmp_path / "repo"
    repo = _repo(repo_path)
    repo.create_head("agent/change", repo.heads.main)
    repo.head.reference = repo.heads["agent/change"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "feature.txt", "feature\n", "add feature")
    repo.create_head("integration/test", repo.heads.main)
    orchestrator = MergeOrchestrator(str(tmp_path / "session"))
    request = orchestrator.enqueue(
        "project/repo",
        "agent/change",
        "integration/test",
        repo_path=str(repo_path),
    )
    assert not isinstance(request, Exception)

    integrated = orchestrator.integrate(request.merge_id)
    events = MergeEventStore(str(tmp_path / "session")).list_events()

    assert not isinstance(integrated, Exception)
    assert integrated.status == "succeeded"
    assert integrated.commit_sha == Repo(repo_path).head.commit.hexsha
    assert integrated.conflict is None
    assert not isinstance(events, Exception)
    assert [event.type for event in events] == ["MergeEnqueued", "MergeSucceeded"]


def test_integrate_conflict_records_hints_and_aborts_merge(tmp_path) -> None:
    repo_path = tmp_path / "repo"
    repo = _repo(repo_path)
    repo.create_head("agent/change", repo.heads.main)
    repo.head.reference = repo.heads["agent/change"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "shared.txt", "agent\n", "agent edit")
    repo.create_head("integration/test", repo.heads.main)
    repo.head.reference = repo.heads["integration/test"]
    repo.head.reset(index=True, working_tree=True)
    target_sha = _commit_file(repo, "shared.txt", "integration\n", "integration edit")
    orchestrator = MergeOrchestrator(str(tmp_path / "session"))
    request = orchestrator.enqueue(
        "project/repo",
        "agent/change",
        "integration/test",
        node_id="node-1",
        agent_id="agent-1",
        repo_path=str(repo_path),
    )
    assert not isinstance(request, Exception)

    integrated = orchestrator.integrate(request.merge_id)
    events = MergeEventStore(str(tmp_path / "session")).list_events()
    fresh_repo = Repo(repo_path)

    assert not isinstance(integrated, Exception)
    assert integrated.status == "conflict"
    assert integrated.conflict is not None
    assert integrated.conflict.files == ["shared.txt"]
    assert integrated.conflict.dispatch_hint == "Dispatch a merge-resolution agent for project/repo."
    assert integrated.acl_commands == [
        "metagit branch allocate --purpose merge-resolution --base integration/test",
        "metagit lease acquire --branch integration/test --agent agent-1",
        "metagit worktree create --branch integration/test",
        "metagit claim declare --path shared.txt --agent agent-1",
    ]
    assert fresh_repo.active_branch.name == "integration/test"
    assert fresh_repo.head.commit.hexsha == target_sha
    assert not (repo_path / ".git" / "MERGE_HEAD").exists()
    assert not isinstance(events, Exception)
    assert [event.type for event in events] == ["MergeEnqueued", "ConflictDetected"]


def test_retry_requeues_conflict_then_integrates_again(tmp_path) -> None:
    repo_path = tmp_path / "repo"
    repo = _repo(repo_path)
    repo.create_head("agent/change", repo.heads.main)
    repo.head.reference = repo.heads["agent/change"]
    repo.head.reset(index=True, working_tree=True)
    _commit_file(repo, "feature.txt", "feature\n", "add feature")
    repo.create_head("integration/test", repo.heads.main)
    orchestrator = MergeOrchestrator(str(tmp_path / "session"))
    request = orchestrator.enqueue(
        "project/repo",
        "agent/change",
        "integration/test",
        repo_path=str(repo_path),
    )
    assert not isinstance(request, Exception)
    first = orchestrator.integrate(request.merge_id)
    assert not isinstance(first, Exception)
    first.status = "conflict"
    saved = orchestrator.store.save(first)
    assert saved is None

    retried = orchestrator.retry(request.merge_id)

    assert not isinstance(retried, Exception)
    assert retried.status == "succeeded"
