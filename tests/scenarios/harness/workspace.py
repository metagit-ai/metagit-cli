#!/usr/bin/env python
"""Ephemeral workspace bootstrap for multi-agent scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from git import Repo

from metagit.core.aos.service import AosService
from metagit.core.coordination.branch_service import BranchService
from metagit.core.coordination.claim_service import ClaimService
from metagit.core.coordination.lease_service import LeaseService
from metagit.core.coordination.worktree_service import WorktreeService
from metagit.core.scheduler.models import SchedulePolicy, ScheduleWeights
from metagit.core.scheduler.service import SchedulerService
from metagit.core.scheduler.store import ScheduleStore
from metagit.core.taskgraph.models import TaskAclBinding, TaskNode
from metagit.core.taskgraph.service import TaskGraphService

from .clock import ControllableClock
from .plane import StateBackend, build_document_store

_DEFAULT_MANIFEST = """\
name: scenario-workspace
kind: application
workspace:
  projects:
    - name: demo
      path: ./demo
      repos:
        - name: service-a
          path: ./demo/service-a
"""


def _init_repo(path: Path) -> Repo:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(path))
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("init")
    return repo


class ScenarioWorkspace:
    """tmp_path-scoped workspace with manifest, git repo, and ready task nodes."""

    def __init__(
        self,
        root: Path,
        *,
        clock: ControllableClock | None = None,
        document_store: Any | None = None,
        graph_id: str = "g1",
        default_repository: str = "demo/service-a",
    ) -> None:
        self.root = root
        self.manifest_path = root / ".metagit.yml"
        self.clock = clock or ControllableClock()
        self._document_store = document_store
        self.graph_id = graph_id
        self.default_repository = default_repository
        self._branches: BranchService | None = None
        self._leases: LeaseService | None = None
        self._claims: ClaimService | None = None
        self._worktrees: WorktreeService | None = None
        self._tasks: TaskGraphService | None = None
        self._scheduler: SchedulerService | None = None
        self._aos: AosService | None = None

    @classmethod
    def bootstrap(
        cls,
        tmp_path: Path,
        *,
        repos: list[str] | None = None,
        ready_nodes: int = 2,
        state_backend: StateBackend = "local",
        clock: ControllableClock | None = None,
        graph_id: str = "g1",
    ) -> ScenarioWorkspace:
        root = tmp_path / "session"
        root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / ".metagit.yml"
        manifest_path.write_text(_DEFAULT_MANIFEST, encoding="utf-8")

        repo_names = repos or ["service-a"]
        for name in repo_names:
            _init_repo(root / "demo" / name)

        store = build_document_store(state_backend)
        ws = cls(
            root,
            clock=clock,
            document_store=store,
            graph_id=graph_id,
            default_repository=f"demo/{repo_names[0]}",
        )
        if ready_nodes > 0:
            ws.seed_ready_nodes(count=ready_nodes)
        return ws

    def seed_ready_nodes(
        self,
        *,
        count: int = 2,
        graph_id: str | None = None,
        project: str = "demo",
        repository: str | None = None,
    ) -> str:
        gid = graph_id or self.graph_id
        repo = repository or self.default_repository
        service = self.task_graph()
        graph = service.create(title="Scenario graph", goal="multi-agent", graph_id=gid)
        if isinstance(graph, Exception):
            raise graph
        now = self.clock.now_iso()
        nodes = [
            TaskNode(
                node_id=f"n{index + 1}",
                graph_id=gid,
                title=f"Node n{index + 1}",
                status="ready",
                project=project,
                repository=repo,
                priority=10 - index,
                acl=TaskAclBinding(acl_commands=["metagit lease acquire --allocate"]),
                created_at=now,
                updated_at=now,
            )
            for index in range(count)
        ]
        graph.nodes = nodes
        saved = service._store.save(graph)  # noqa: SLF001 — test fixture seed
        if isinstance(saved, Exception):
            raise saved
        policy = SchedulePolicy(weights=ScheduleWeights(affinity=0.0, cost=0.0, fairness=0.0))
        sched_err = ScheduleStore(str(self.root)).save_policy(policy)
        if isinstance(sched_err, Exception):
            raise sched_err
        self.graph_id = gid
        return gid

    def branch_service(self) -> BranchService:
        if self._branches is None:
            self._branches = BranchService(
                str(self.root),
                sync_root=str(self.root),
                definition_path=str(self.manifest_path),
                now_fn=self.clock.now_iso,
            )
        return self._branches

    def lease_service(self, *, clock: ControllableClock | None = None) -> LeaseService:
        active_clock = clock or self.clock
        if self._leases is None or clock is not None:
            self._leases = LeaseService(
                str(self.root),
                sync_root=str(self.root),
                definition_path=str(self.manifest_path),
                branch_service=self.branch_service(),
                now_fn=active_clock.now_iso,
                clock_fn=active_clock.now,
            )
        return self._leases

    def claim_service(self) -> ClaimService:
        if self._claims is None:
            self._claims = ClaimService(str(self.root))
        return self._claims

    def worktree_service(self) -> WorktreeService:
        if self._worktrees is None:
            self._worktrees = WorktreeService(
                str(self.root),
                sync_root=str(self.root),
                definition_path=str(self.manifest_path),
                lease_service=self.lease_service(),
                now_fn=self.clock.now_iso,
            )
        return self._worktrees

    def task_graph(self) -> TaskGraphService:
        if self._tasks is None:
            self._tasks = TaskGraphService(str(self.root))
        return self._tasks

    def scheduler(self) -> SchedulerService:
        if self._scheduler is None:
            self._scheduler = SchedulerService(
                str(self.root),
                task_service=self.task_graph(),
                worktrees_fn=lambda: [],
                merge_status_fn=lambda: [],
                now_fn=self.clock.now_iso,
            )
        return self._scheduler

    def aos(self) -> AosService:
        if self._aos is None:
            self._aos = AosService(
                str(self.root),
                scheduler=self.scheduler(),
                now_fn=self.clock.now_iso,
            )
        return self._aos

    def document_store(self) -> Any | None:
        return self._document_store

    def snapshot(self) -> dict[str, Any]:
        leases = self.lease_service().list()
        claims = self.claim_service().list()
        worktrees = self.worktree_service().list()
        decisions = ScheduleStore(str(self.root)).list_decisions()
        nodes = self.task_graph().list_nodes()
        metagit = self.root / ".metagit"
        artifact_paths = sorted(
            str(path.relative_to(self.root))
            for path in metagit.rglob("*")
            if path.is_file()
        ) if metagit.is_dir() else []
        return {
            "root": str(self.root),
            "leases": [] if isinstance(leases, Exception) else [row.model_dump() for row in leases.leases],
            "claims": [] if isinstance(claims, Exception) else [row.model_dump() for row in claims.claims],
            "worktrees": (
                []
                if isinstance(worktrees, Exception)
                else [row.model_dump() for row in worktrees.worktrees]
            ),
            "decisions": (
                []
                if isinstance(decisions, Exception)
                else [row.model_dump() for row in decisions]
            ),
            "tasks": [] if isinstance(nodes, Exception) else [row.model_dump() for row in nodes],
            "artifact_paths": artifact_paths,
        }
