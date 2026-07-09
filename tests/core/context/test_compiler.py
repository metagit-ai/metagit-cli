#!/usr/bin/env python
"""Unit tests for ContextCompiler (RFC-0009)."""

from __future__ import annotations

import json
from pathlib import Path

from git import Repo

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.compiler import ContextCompiler
from metagit.core.context.event_service import WorkspaceEventService
from metagit.core.context.models import Objective
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.taskgraph.service import TaskGraphService
from metagit.core.workspace.context_models import utc_now_iso


def _fixture(tmp_path: Path):
    repo_dir = tmp_path / "demo" / "svc"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: compile-test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manager = MetagitConfigManager(config_path=tmp_path / ".metagit.yml")
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    root = str(tmp_path.resolve())
    cfg_path = str((tmp_path / ".metagit.yml").resolve())
    return loaded, root, cfg_path


def test_compile_project_repo_writes_artifact_under_budget(tmp_path: Path) -> None:
    cfg, root, cfg_path = _fixture(tmp_path)
    result = ContextCompiler().compile(
        cfg,
        cfg_path,
        root,
        session_root=root,
        definition_root=root,
        project="demo",
        repo="svc",
        tier=1,
        budget=50_000,
        profile="bugfix-local",
    )
    assert not isinstance(result, Exception)
    assert result.ok is True
    assert result.inputs.project == "demo"
    assert result.inputs.repo == "svc"
    assert result.pack.tier == 1
    assert Path(result.artifact_path).is_file()
    assert result.estimated_tokens <= 50_000
    assert "cards" in result.sections or "map" in result.sections
    assert result.suggested_repomix_command is not None
    assert "bugfix-local" in result.suggested_repomix_command

    feed = WorkspaceEventService(root).list_events()
    kinds = {(e.source, e.kind) for e in feed.events}
    assert ("context", "ContextCompiled") in kinds


def test_compile_with_objective_fallback(tmp_path: Path) -> None:
    cfg, root, cfg_path = _fixture(tmp_path)
    now = utc_now_iso()
    ObjectiveService(workspace_root=root).upsert(
        Objective(
            id="obj-1",
            title="Ship",
            repos=["demo/svc"],
            status="in_progress",
            created_at=now,
            updated_at=now,
        )
    )
    result = ContextCompiler().compile(
        cfg,
        cfg_path,
        root,
        session_root=root,
        definition_root=root,
        project="demo",
        repo="svc",
        tier=0,
        objective_id="obj-1",
    )
    assert not isinstance(result, Exception)
    assert result.inputs.objective_id == "obj-1"
    assert result.pack.tier == 0
    assert Path(result.artifact_path).is_file()
    assert ".metagit/context/compiled/" in result.artifact_path.replace("\\", "/")


def test_compile_stamps_task_node(tmp_path: Path) -> None:
    cfg, root, cfg_path = _fixture(tmp_path)
    tg = TaskGraphService(root)
    graph = tg.create(title="G", goal="compile", graph_id="g-compile")
    assert not isinstance(graph, Exception)
    expanded = tg.expand(
        graph.graph_id,
        [
            {
                "node_id": "n1",
                "title": "Work",
                "project": "demo",
                "repository": "svc",
            }
        ],
    )
    assert not isinstance(expanded, Exception)
    result = ContextCompiler().compile(
        cfg,
        cfg_path,
        root,
        session_root=root,
        definition_root=root,
        project="demo",
        repo="svc",
        tier=1,
        budget=8000,
        task_id="n1",
        graph_id="g-compile",
    )
    assert not isinstance(result, Exception)
    assert "tasks/g-compile/context/n1.json" in result.artifact_path.replace("\\", "/")
    status = tg.status("n1", graph_id="g-compile")
    assert not isinstance(status, Exception)
    assert status.compiled_context_path == result.artifact_path
    assert status.context_budget == 8000
    saved = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))
    assert saved["compile_id"] == result.compile_id
