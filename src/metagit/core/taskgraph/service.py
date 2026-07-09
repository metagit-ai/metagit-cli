#!/usr/bin/env python
"""TaskGraphService — create, expand, ready-set, status transitions (RFC-0008)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

from metagit.core.taskgraph.events import TaskGraphEventStore
from metagit.core.taskgraph.models import (
    TaskAclBinding,
    TaskGraph,
    TaskIntent,
    TaskNode,
    TaskNodeStatus,
)
from metagit.core.taskgraph.store import TaskGraphStore
from metagit.core.workspace.context_models import utc_now_iso

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str, *, fallback: str = "node") -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug[:48].rstrip("-") or fallback


def detect_cycle(nodes: list[TaskNode]) -> str | None:
    """Return a node id participating in a cycle, or None if the DAG is acyclic."""
    edges: dict[str, list[str]] = {node.node_id: list(node.depends_on) for node in nodes}
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node_id: str) -> str | None:
        if node_id in visiting:
            return node_id
        if node_id in visited:
            return None
        visiting.add(node_id)
        for dep in edges.get(node_id, []):
            if dep not in edges:
                continue
            hit = dfs(dep)
            if hit is not None:
                return hit
        visiting.remove(node_id)
        visited.add(node_id)
        return None

    for nid in edges:
        hit = dfs(nid)
        if hit is not None:
            return hit
    return None


def compute_ready_ids(nodes: list[TaskNode]) -> set[str]:
    """Ids whose dependencies are all completed and status is pending/ready."""
    by_id = {node.node_id: node for node in nodes}
    ready: set[str] = set()
    for node in nodes:
        if node.status in {"completed", "cancelled", "blocked", "running"}:
            continue
        deps_ok = all(by_id.get(dep) is not None and by_id[dep].status == "completed" for dep in node.depends_on)
        if deps_ok:
            ready.add(node.node_id)
    return ready


class TaskGraphService:
    """Create and mutate task graphs under the session root."""

    def __init__(
        self,
        session_root: str,
        *,
        store: TaskGraphStore | None = None,
        event_store: TaskGraphEventStore | None = None,
        now_fn: Callable[[], str] | None = None,
    ) -> None:
        self._session_root = session_root
        self._store = store or TaskGraphStore(session_root)
        self._events = event_store or TaskGraphEventStore(session_root)
        self._now = now_fn or utc_now_iso

    def create(
        self,
        *,
        title: str,
        goal: str,
        acceptance: list[str] | None = None,
        objective_id: str | None = None,
        handoff_id: str | None = None,
        project: str | None = None,
        repos: list[str] | None = None,
        graph_id: str | None = None,
    ) -> TaskGraph | Exception:
        now = self._now()
        gid = graph_id or uuid.uuid4().hex[:12]
        intent_id = f"intent-{gid}"
        intent = TaskIntent(
            intent_id=intent_id,
            title=title.strip(),
            goal=goal.strip(),
            acceptance=list(acceptance or []),
            project=project,
            repos=list(repos or []),
            objective_id=objective_id,
            handoff_id=handoff_id,
            created_at=now,
            updated_at=now,
        )
        graph = TaskGraph(
            graph_id=gid,
            title=title.strip(),
            root_intent_id=intent_id,
            objective_id=objective_id,
            handoff_id=handoff_id,
            intent=intent,
            nodes=[],
            status="active",
            created_at=now,
            updated_at=now,
        )
        err = self._store.save(graph)
        if isinstance(err, Exception):
            return err
        self._events.append("TaskGraphCreated", {"graph_id": gid, "title": title.strip()})
        return graph

    def expand(
        self,
        graph_id: str,
        outline: list[dict[str, Any]] | str,
    ) -> TaskGraph | Exception:
        graph = self._store.load(graph_id)
        if isinstance(graph, Exception):
            return graph
        parsed = self._parse_outline(outline) if isinstance(outline, str) else list(outline)
        if isinstance(parsed, Exception):
            return parsed
        now = self._now()
        existing_ids = {node.node_id for node in graph.nodes}
        new_nodes: list[TaskNode] = []
        for item in parsed:
            title = str(item.get("title", "")).strip()
            if not title:
                return ValueError("outline item requires title")
            node_id = str(item.get("node_id") or _slugify(title)).strip()
            if not node_id:
                return ValueError("outline item produced empty node_id")
            if node_id in existing_ids or any(n.node_id == node_id for n in new_nodes):
                node_id = f"{node_id}-{uuid.uuid4().hex[:6]}"
            depends_on = [str(d) for d in item.get("depends_on") or []]
            new_nodes.append(
                TaskNode(
                    node_id=node_id,
                    graph_id=graph_id,
                    title=title,
                    depends_on=depends_on,
                    status="pending",
                    project=item.get("project"),
                    repository=item.get("repository"),
                    intent_id=graph.root_intent_id,
                    created_at=now,
                    updated_at=now,
                )
            )
        candidate = list(graph.nodes) + new_nodes
        cycle = detect_cycle(candidate)
        if cycle is not None:
            return ValueError(f"cycle detected involving node {cycle!r}")
        unknown = self._unknown_deps(candidate)
        if unknown:
            return ValueError(f"unknown dependency ids: {', '.join(sorted(unknown))}")
        graph.nodes = candidate
        graph.updated_at = now
        self._refresh_ready(graph, now=now, emit=True)
        err = self._store.save(graph)
        if isinstance(err, Exception):
            return err
        for node in new_nodes:
            self._events.append(
                "TaskNodeCreated",
                {"graph_id": graph_id, "node_id": node.node_id, "title": node.title},
            )
        return graph

    def ready(self, graph_id: str | None = None) -> list[TaskNode] | Exception:
        graphs = self._select_graphs(graph_id)
        if isinstance(graphs, Exception):
            return graphs
        out: list[TaskNode] = []
        for graph in graphs:
            self._refresh_ready(graph, now=self._now(), emit=False)
            for node in graph.nodes:
                if node.status == "ready":
                    out.append(node)
        return out

    def list_nodes(
        self,
        *,
        graph_id: str | None = None,
        status: TaskNodeStatus | None = None,
    ) -> list[TaskNode] | Exception:
        graphs = self._select_graphs(graph_id)
        if isinstance(graphs, Exception):
            return graphs
        rows: list[TaskNode] = []
        for graph in graphs:
            for node in graph.nodes:
                if status is None or node.status == status:
                    rows.append(node)
        return rows

    def list_graphs(self) -> list[TaskGraph] | Exception:
        return self._store.list_graphs()

    def status(self, node_id: str, *, graph_id: str | None = None) -> TaskNode | Exception:
        found = self._find_node(node_id, graph_id=graph_id)
        if isinstance(found, Exception):
            return found
        return found[1]

    def get_graph(self, graph_id: str) -> TaskGraph | Exception:
        return self._store.load(graph_id)

    def complete(self, node_id: str, *, graph_id: str | None = None) -> TaskNode | Exception:
        return self._set_status(node_id, "completed", graph_id=graph_id)

    def block(
        self,
        node_id: str,
        reason: str,
        *,
        graph_id: str | None = None,
    ) -> TaskNode | Exception:
        return self._set_status(node_id, "blocked", graph_id=graph_id, blocker_reason=reason)

    def start(self, node_id: str, *, graph_id: str | None = None) -> TaskNode | Exception:
        return self._set_status(node_id, "running", graph_id=graph_id)

    def cancel(self, node_id: str, *, graph_id: str | None = None) -> TaskNode | Exception:
        return self._set_status(node_id, "cancelled", graph_id=graph_id)

    def bind_acl(
        self,
        node_id: str,
        *,
        agent_id: str,
        graph_id: str | None = None,
        branch: str | None = None,
        lease_id: str | None = None,
        worktree_id: str | None = None,
        claim_ids: list[str] | None = None,
        pattern: str | None = None,
    ) -> TaskNode | Exception:
        located = self._find_node(node_id, graph_id=graph_id)
        if isinstance(located, Exception):
            return located
        graph, node = located
        now = self._now()
        if node.repository and "/" in node.repository:
            repo = node.repository
        elif node.project and node.repository:
            repo = f"{node.project}/{node.repository}"
        elif node.repository:
            repo = node.repository
        else:
            repo = "PROJECT/REPO"
        task_id = node.node_id
        desc = _slugify(node.title, fallback=task_id)
        commands = [
            (
                f"metagit branch allocate --repository {repo} --agent-id {agent_id} "
                f"--task-id {task_id} --description {desc}"
            ),
            (f"metagit lease acquire --repository {repo} --agent-id {agent_id} --task-id {task_id} --allocate"),
            (
                f"metagit worktree create --repository {repo} --agent-id {agent_id} "
                f"--task-id {task_id} --branch agent/{task_id}-{desc}"
            ),
        ]
        claim_pattern = pattern or "**/*"
        commands.append(f"metagit claim declare --repository {repo} --agent-id {agent_id} --pattern {claim_pattern!r}")
        node.agent_id = agent_id
        node.acl = TaskAclBinding(
            branch=branch,
            lease_id=lease_id,
            worktree_id=worktree_id,
            claim_ids=list(claim_ids or []),
            acl_commands=commands,
        )
        node.updated_at = now
        graph.updated_at = now
        err = self._store.save(graph)
        if isinstance(err, Exception):
            return err
        return node

    def _set_status(
        self,
        node_id: str,
        status: TaskNodeStatus,
        *,
        graph_id: str | None = None,
        blocker_reason: str | None = None,
    ) -> TaskNode | Exception:
        located = self._find_node(node_id, graph_id=graph_id)
        if isinstance(located, Exception):
            return located
        graph, node = located
        now = self._now()
        if status == "running" and node.status not in {"ready", "pending", "running"}:
            return ValueError(f"cannot start node in status {node.status!r}")
        if status == "completed" and node.status == "cancelled":
            return ValueError("cannot complete a cancelled node")
        node.status = status
        node.blocker_reason = blocker_reason if status == "blocked" else None
        node.updated_at = now
        graph.updated_at = now
        event_type = {
            "completed": "TaskCompleted",
            "blocked": "TaskBlocked",
            "cancelled": "TaskCancelled",
            "running": "TaskStarted",
        }.get(status)
        if event_type:
            payload: dict[str, Any] = {
                "graph_id": graph.graph_id,
                "node_id": node.node_id,
            }
            if blocker_reason:
                payload["reason"] = blocker_reason
            self._events.append(event_type, payload)  # type: ignore[arg-type]
        if status == "completed":
            self._refresh_ready(graph, now=now, emit=True)
        err = self._store.save(graph)
        if isinstance(err, Exception):
            return err
        return node

    def _refresh_ready(self, graph: TaskGraph, *, now: str, emit: bool) -> None:
        ready_ids = compute_ready_ids(graph.nodes)
        for node in graph.nodes:
            if node.node_id in ready_ids and node.status == "pending":
                node.status = "ready"
                node.updated_at = now
                if emit:
                    self._events.append(
                        "TaskReady",
                        {"graph_id": graph.graph_id, "node_id": node.node_id},
                    )
            elif (
                node.status == "ready"
                and node.node_id not in ready_ids
                and node.status not in {"completed", "cancelled", "blocked", "running"}
            ):
                node.status = "pending"
                node.updated_at = now

    def _select_graphs(self, graph_id: str | None) -> list[TaskGraph] | Exception:
        if graph_id:
            graph = self._store.load(graph_id)
            if isinstance(graph, Exception):
                return graph
            return [graph]
        return self._store.list_graphs()

    def _find_node(
        self,
        node_id: str,
        *,
        graph_id: str | None = None,
    ) -> tuple[TaskGraph, TaskNode] | Exception:
        graphs = self._select_graphs(graph_id)
        if isinstance(graphs, Exception):
            return graphs
        matches: list[tuple[TaskGraph, TaskNode]] = []
        for graph in graphs:
            for node in graph.nodes:
                if node.node_id == node_id:
                    matches.append((graph, node))
        if not matches:
            return FileNotFoundError(f"task node not found: {node_id}")
        if len(matches) > 1 and graph_id is None:
            return ValueError(f"ambiguous node_id {node_id!r}; pass --graph-id")
        return matches[0]

    @staticmethod
    def _unknown_deps(nodes: list[TaskNode]) -> set[str]:
        known = {node.node_id for node in nodes}
        unknown: set[str] = set()
        for node in nodes:
            for dep in node.depends_on:
                if dep not in known:
                    unknown.add(dep)
        return unknown

    @staticmethod
    def _parse_outline(text: str) -> list[dict[str, Any]] | Exception:
        stripped = text.strip()
        if not stripped:
            return ValueError("outline is empty")
        if stripped.startswith("["):
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                return ValueError(f"invalid JSON outline: {exc}")
            if not isinstance(data, list):
                return ValueError("JSON outline must be a list")
            return [item if isinstance(item, dict) else {"title": str(item)} for item in data]

        # Indented outline: indent level implies parent dependency
        lines = [line.rstrip() for line in stripped.splitlines() if line.strip()]
        stack: list[tuple[int, str]] = []
        rows: list[dict[str, Any]] = []
        used: dict[str, int] = {}
        for line in lines:
            indent = len(line) - len(line.lstrip(" \t"))
            title = line.strip().lstrip("-* ").strip()
            if not title:
                continue
            base = _slugify(title)
            count = used.get(base, 0)
            used[base] = count + 1
            node_id = base if count == 0 else f"{base}-{count + 1}"
            while stack and stack[-1][0] >= indent:
                stack.pop()
            depends_on = [stack[-1][1]] if stack else []
            rows.append({"node_id": node_id, "title": title, "depends_on": depends_on})
            stack.append((indent, node_id))
        return rows


__all__ = [
    "TaskGraphService",
    "compute_ready_ids",
    "detect_cycle",
]
