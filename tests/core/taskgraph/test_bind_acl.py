#!/usr/bin/env python
"""Tests for ACL bind hints on task nodes."""

from __future__ import annotations

from pathlib import Path

from metagit.core.taskgraph.service import TaskGraphService


def test_bind_acl_stores_commands_without_git(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    service = TaskGraphService(str(session))
    graph = service.create(title="ACL", goal="hints")
    assert not isinstance(graph, Exception)
    expanded = service.expand(
        graph.graph_id,
        [
            {
                "node_id": "auth",
                "title": "Auth work",
                "project": "demo",
                "repository": "service-a",
            }
        ],
    )
    assert not isinstance(expanded, Exception)
    bound = service.bind_acl("auth", agent_id="agent-1", graph_id=graph.graph_id)
    assert not isinstance(bound, Exception)
    assert bound.agent_id == "agent-1"
    assert bound.acl is not None
    assert len(bound.acl.acl_commands) >= 3
    joined = "\n".join(bound.acl.acl_commands)
    assert "metagit branch allocate" in joined
    assert "demo/service-a" in joined
    assert "agent-1" in joined
    assert "auth" in joined
    # No worktree directory created by bind
    assert not (session / ".worktrees").exists()
