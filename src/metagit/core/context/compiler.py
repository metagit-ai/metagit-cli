#!/usr/bin/env python
"""Agent Context Compiler (RFC-0009) — budgeted packs from task/objective scope."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from metagit.core.config.models import MetagitConfig
from metagit.core.context.context_pack_service import ContextPackService
from metagit.core.context.models import CompiledContext, CompiledContextInputs
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.taskgraph.service import TaskGraphService
from metagit.core.taskgraph.store import TaskGraphStore
from metagit.core.workspace.context_models import utc_now_iso


def compiled_context_dir(session_root: str) -> Path:
    return Path(session_root) / ".metagit" / "context" / "compiled"


def task_context_artifact_path(session_root: str, graph_id: str, node_id: str) -> Path:
    return Path(session_root) / ".metagit" / "tasks" / graph_id / "context" / f"{node_id}.json"


def estimate_tokens_from_obj(payload: object) -> int:
    """Char/4 heuristic matching ContextPackService."""
    data = payload.model_dump(mode="python") if hasattr(payload, "model_dump") else payload
    return len(json.dumps(data, default=str)) // 4


class ContextCompiler:
    """Compile a budgeted context artifact for a project/repo (+ optional task)."""

    def __init__(
        self,
        *,
        pack_service: ContextPackService | None = None,
    ) -> None:
        self._pack = pack_service or ContextPackService()

    def compile(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        *,
        session_root: str,
        definition_root: str,
        project: str,
        repo: str,
        tier: Literal[0, 1, 2] = 1,
        budget: int | None = None,
        profile: str | None = None,
        task_id: str | None = None,
        graph_id: str | None = None,
        objective_id: str | None = None,
        update_task: bool = True,
    ) -> CompiledContext | Exception:
        """Build pack, write artifact, optionally stamp task node metadata."""
        try:
            resolved = self._resolve_scope(
                session_root=session_root,
                project=project,
                repo=repo,
                task_id=task_id,
                graph_id=graph_id,
                objective_id=objective_id,
                budget=budget,
            )
            if isinstance(resolved, Exception):
                return resolved
            project_name, repo_name, node_graph_id, node_id, obj_id, effective_budget = resolved

            pack = self._pack.pack(
                config=config,
                config_path=config_path,
                workspace_root=workspace_root,
                session_root=session_root,
                definition_root=definition_root,
                tier=tier,
                project_name=project_name,
                repo_name=repo_name,
                max_tokens=effective_budget,
            )
            compile_id = uuid.uuid4().hex[:12]
            now = utc_now_iso()
            if node_graph_id and node_id:
                artifact = task_context_artifact_path(session_root, node_graph_id, node_id)
            else:
                artifact = compiled_context_dir(session_root) / f"{compile_id}.json"

            sections: list[str] = []
            if pack.map is not None:
                sections.append("map")
            if pack.cards is not None:
                sections.append("cards")
            if pack.digest is not None:
                sections.append("digest")

            suggested: str | None = None
            if profile:
                suggested = f"metagit context repomix --profile {profile} --project {project_name} --repo {repo_name}"

            result = CompiledContext(
                compile_id=compile_id,
                inputs=CompiledContextInputs(
                    project=project_name,
                    repo=repo_name,
                    tier=tier,
                    budget=effective_budget,
                    profile=profile,
                    task_id=node_id,
                    graph_id=node_graph_id,
                    objective_id=obj_id,
                ),
                pack=pack,
                estimated_tokens=pack.token_estimate or estimate_tokens_from_obj(pack),
                artifact_path=str(artifact),
                sections=sections,
                dropped_sections=list(pack.dropped_sections),
                suggested_repomix_command=suggested,
                created_at=now,
            )

            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(
                json.dumps(result.model_dump(mode="json"), indent=2) + "\n",
                encoding="utf-8",
            )

            if update_task and node_id:
                stamp = self._stamp_task_node(
                    session_root=session_root,
                    node_id=node_id,
                    graph_id=node_graph_id,
                    artifact_path=str(artifact),
                    budget=effective_budget,
                )
                if isinstance(stamp, Exception):
                    return stamp

            self._append_event(
                session_root,
                {
                    "compile_id": compile_id,
                    "artifact_path": str(artifact),
                    "project": project_name,
                    "repo": repo_name,
                    "task_id": node_id,
                    "graph_id": node_graph_id,
                    "objective_id": obj_id,
                    "estimated_tokens": result.estimated_tokens,
                },
            )
            return result
        except Exception as exc:  # noqa: BLE001 — surface to callers
            return exc

    def _resolve_scope(
        self,
        *,
        session_root: str,
        project: str,
        repo: str,
        task_id: str | None,
        graph_id: str | None,
        objective_id: str | None,
        budget: int | None,
    ) -> tuple[str, str, str | None, str | None, str | None, int | None] | Exception:
        project_name = project.strip()
        repo_name = repo.strip()
        node_graph_id = graph_id
        node_id: str | None = None
        obj_id = objective_id
        effective_budget = budget

        if task_id:
            service = TaskGraphService(session_root)
            located = service.status(task_id, graph_id=graph_id)
            if isinstance(located, Exception):
                return located
            node_id = located.node_id
            node_graph_id = located.graph_id
            if located.project:
                project_name = located.project
            if located.repository:
                # repository may be "project/repo" or bare repo name
                if "/" in located.repository:
                    parts = located.repository.split("/", 1)
                    project_name = parts[0]
                    repo_name = parts[1]
                else:
                    repo_name = located.repository
            if effective_budget is None and located.context_budget is not None:
                effective_budget = located.context_budget
            graph = TaskGraphStore(session_root).load(located.graph_id)
            if not isinstance(graph, Exception) and graph.objective_id and not obj_id:
                obj_id = graph.objective_id

        if obj_id and not task_id:
            objective = ObjectiveService(workspace_root=session_root).get(obj_id)
            if objective is None:
                return FileNotFoundError(f"objective not found: {obj_id}")
            # Prefer explicit CLI project/repo; if repos listed and project/repo empty-ish, keep CLI values

        if not project_name or not repo_name:
            return ValueError("project and repo are required (or resolve from task node)")
        return project_name, repo_name, node_graph_id, node_id, obj_id, effective_budget

    def _stamp_task_node(
        self,
        *,
        session_root: str,
        node_id: str,
        graph_id: str | None,
        artifact_path: str,
        budget: int | None,
    ) -> None | Exception:
        store = TaskGraphStore(session_root)
        if not graph_id:
            return ValueError("graph_id required to stamp task node")
        graph = store.load(graph_id)
        if isinstance(graph, Exception):
            return graph
        now = utc_now_iso()
        found = False
        for node in graph.nodes:
            if node.node_id == node_id:
                node.compiled_context_path = artifact_path
                if budget is not None:
                    node.context_budget = budget
                node.updated_at = now
                found = True
                break
        if not found:
            return FileNotFoundError(f"task node not found: {node_id}")
        graph.updated_at = now
        return store.save(graph)

    @staticmethod
    def _append_event(session_root: str, payload: dict) -> None:
        path = Path(session_root) / ".metagit" / "events" / "context.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "event_id": uuid.uuid4().hex,
                "type": "ContextCompiled",
                "at": utc_now_iso(),
                "payload": payload,
            },
            sort_keys=False,
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


__all__ = [
    "ContextCompiler",
    "compiled_context_dir",
    "estimate_tokens_from_obj",
    "task_context_artifact_path",
]
