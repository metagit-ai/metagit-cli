#!/usr/bin/env python
"""
Workspace discovery orchestration — health + summary + readiness (RFC-0020).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.gate import WorkspaceGate
from metagit.core.mcp.services.workspace_health import WorkspaceHealthService
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.workspace.agent_surface_probe import (
    has_any_agent_surface,
    probe_repo_agent_surfaces,
)
from metagit.core.workspace.context_models import utc_now_iso
from metagit.core.workspace.discovery_models import (
    AgentSurfaceStats,
    CoordinationHints,
    CoverageHints,
    DiscoveryGateStatus,
    DiscoveryHealthRollup,
    DiscoveryMapStats,
    ReadinessBlocker,
    ReadinessDimension,
    ReadinessScore,
    WorkspaceSummaryResult,
)
from metagit.core.workspace.health_models import WorkspaceHealthResult

_READINESS_WEIGHTS = {
    "gate_active": 0.25,
    "repos_present": 0.25,
    "maintenance_clear": 0.25,
    "agent_surfaces": 0.25,
}


def readiness_grade(score: int) -> str:
    """Map 0–100 readiness score to grade band."""
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 50:
        return "fair"
    return "poor"


class WorkspaceDiscoveryService:
    """Thin composition over health, index, gate, and agent-surface probes."""

    def __init__(
        self,
        *,
        health_service: Optional[WorkspaceHealthService] = None,
        index_service: Optional[WorkspaceIndexService] = None,
        gate: Optional[WorkspaceGate] = None,
        now_fn=None,
    ) -> None:
        self._health = health_service or WorkspaceHealthService()
        self._index = index_service or WorkspaceIndexService()
        self._gate = gate or WorkspaceGate()
        self._now = now_fn or utc_now_iso

    def health(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        check_git_status: bool = True,
        check_dependencies: bool = True,
        check_stale_branches: bool = True,
        check_gitnexus: bool = True,
        project_name: Optional[str] = None,
        dedupe: WorkspaceDedupeConfig | None = None,
        definition_root: Optional[str] = None,
    ) -> WorkspaceHealthResult:
        """Delegate to WorkspaceHealthService (CLI/MCP parity)."""
        return self._health.check(
            config=config,
            workspace_root=workspace_root,
            check_git_status=check_git_status,
            check_dependencies=check_dependencies,
            check_stale_branches=check_stale_branches,
            check_gitnexus=check_gitnexus,
            project_name=project_name,
            dedupe=dedupe,
            definition_root=definition_root,
        )

    def summary(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        project_name: Optional[str] = None,
        include_cards: bool = False,
        include_coordination: bool = True,
        dedupe: WorkspaceDedupeConfig | None = None,
        session_root: Optional[str] = None,
        definition_root: Optional[str] = None,
    ) -> WorkspaceSummaryResult:
        """Build lean discovery + readiness payload (report-only)."""
        root = str(Path(workspace_root).expanduser().resolve())
        def_root = str(Path(definition_root or session_root or root).expanduser().resolve())
        session = str(Path(session_root or def_root).expanduser().resolve())
        gate_status = self._gate.evaluate(root_path=def_root)
        health = self.health(
            config=config,
            workspace_root=root,
            check_git_status=True,
            check_dependencies=True,
            check_stale_branches=False,
            check_gitnexus=False,
            project_name=project_name,
            dedupe=dedupe,
            definition_root=def_root,
        )
        index_rows = self._index.build_index(
            config=config,
            workspace_root=root,
            definition_root=def_root,
        )
        if project_name:
            index_rows = [row for row in index_rows if row.get("project_name") == project_name]

        map_stats = self._map_stats(config=config, rows=index_rows, project_name=project_name)
        agent_surfaces = self._agent_surfaces(config=config, workspace_root=def_root, rows=index_rows)
        health_rollup = self._health_rollup(health)
        coordination = (
            self._coordination_hints(session_root=session)
            if include_coordination
            else CoordinationHints(available=False)
        )
        coverage = self._coverage_hints(config=config, rows=index_rows, session_root=session)
        readiness = self._score_readiness(
            gate_status=gate_status,
            map_stats=map_stats,
            health=health,
            agent_surfaces=agent_surfaces,
        )
        cards: list[dict[str, Any]] | None = None
        if include_cards:
            cards = self._lean_cards(rows=index_rows)

        return WorkspaceSummaryResult(
            generated_at=self._now(),
            workspace_root=root,
            gate=DiscoveryGateStatus(
                state=gate_status.state.value,
                reason=gate_status.reason,
            ),
            map=map_stats,
            health=health_rollup,
            agent_surfaces=agent_surfaces,
            coordination=coordination,
            coverage=coverage,
            readiness=readiness,
            cards=cards,
        )

    def _map_stats(
        self,
        *,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        project_name: Optional[str],
    ) -> DiscoveryMapStats:
        projects = config.workspace.projects if config.workspace else []
        if project_name:
            projects = [p for p in projects if p.name == project_name]
        present = sum(1 for row in rows if row.get("exists"))
        total = len(rows)
        return DiscoveryMapStats(
            projects=len(projects),
            repos_total=total,
            repos_present=present,
            repos_missing=max(total - present, 0),
        )

    def _agent_surfaces(
        self,
        *,
        config: MetagitConfig,
        workspace_root: str,
        rows: list[dict[str, Any]],
    ) -> AgentSurfaceStats:
        root = Path(workspace_root)
        has_instructions = bool(
            (config.agent_instructions or "").strip()
            or (config.workspace and (config.workspace.agent_instructions or "").strip())
        )
        umbrella = probe_repo_agent_surfaces(root)
        with_agents = 0
        with_llms = 0
        with_marker = 0
        with_any = 0
        audited = 0
        for row in rows:
            if not row.get("exists"):
                continue
            audited += 1
            probe = probe_repo_agent_surfaces(str(row.get("repo_path", "")))
            if probe["has_agents_md"]:
                with_agents += 1
            if probe["has_llms_txt"]:
                with_llms += 1
            if probe["has_readme_marker"]:
                with_marker += 1
            if has_any_agent_surface(probe):
                with_any += 1
        return AgentSurfaceStats(
            manifest_has_agent_instructions=has_instructions,
            umbrella_has_agents_md=umbrella["has_agents_md"],
            umbrella_has_llms_txt=umbrella["has_llms_txt"],
            repos_audited=audited,
            repos_with_agents_md=with_agents,
            repos_with_llms_txt=with_llms,
            repos_with_readme_marker=with_marker,
            repos_with_any_surface=with_any,
        )

    def _health_rollup(self, health: WorkspaceHealthResult) -> DiscoveryHealthRollup:
        critical = sum(1 for item in health.recommendations if item.severity == "critical")
        warning = sum(1 for item in health.recommendations if item.severity == "warning")
        actions: list[str] = []
        for item in health.recommendations:
            if item.action in actions:
                continue
            actions.append(item.action)
            if len(actions) >= 5:
                break
        clear = critical == 0 and warning == 0
        return DiscoveryHealthRollup(
            ok=clear,
            critical_count=critical,
            warning_count=warning,
            top_actions=actions,
        )

    def _coordination_hints(self, *, session_root: str) -> CoordinationHints:
        try:
            from metagit.core.aos.service import AosService
        except Exception:  # noqa: BLE001 — soft degrade
            return CoordinationHints(available=False)

        service = AosService(session_root)
        status = service.status()
        if isinstance(status, Exception):
            return CoordinationHints(available=False)
        doctor = service.doctor(fix=False, confirm=False)
        doctor_findings = 0 if isinstance(doctor, Exception) else len(doctor.findings)
        acl = status.subsystems.get("acl")
        taskgraph = status.subsystems.get("taskgraph")
        leases = 0
        ready = 0
        if acl is not None and acl.available:
            leases = int(acl.summary.get("leases_active", 0) or 0)
        if taskgraph is not None and taskgraph.available:
            ready = int(taskgraph.summary.get("ready", 0) or 0)
        return CoordinationHints(
            available=True,
            acl_leases_active=leases,
            ready_tasks=ready,
            doctor_findings=doctor_findings,
        )

    def _coverage_hints(
        self,
        *,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        session_root: str,
    ) -> CoverageHints:
        with_ci = 0
        for row in rows:
            project_name = str(row.get("project_name", ""))
            repo_name = str(row.get("repo_name", ""))
            repo = self._find_repo(config, project_name, repo_name)
            if repo is not None and getattr(repo, "ci", None) is not None:
                with_ci += 1
        concepts: int | None = None
        semantic_available = False
        try:
            from metagit.core.semantic.store import SemanticGraphStore

            store = SemanticGraphStore(session_root)
            loaded = store.load_concepts()
            if not isinstance(loaded, Exception):
                semantic_available = True
                concepts = len(loaded)
        except Exception:  # noqa: BLE001
            pass
        return CoverageHints(
            repos_with_ci=with_ci,
            repos_total=len(rows),
            semantic_concepts=concepts,
            semantic_available=semantic_available,
        )

    def _find_repo(self, config: MetagitConfig, project_name: str, repo_name: str):
        if not config.workspace:
            return None
        for project in config.workspace.projects:
            if project.name != project_name:
                continue
            for repo in project.repos or []:
                if repo.name == repo_name:
                    return repo
        return None

    def _lean_cards(self, *, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for row in rows:
            probe = (
                probe_repo_agent_surfaces(str(row.get("repo_path", "")))
                if row.get("exists")
                else {
                    "has_agents_md": False,
                    "has_llms_txt": False,
                    "has_readme_marker": False,
                }
            )
            cards.append(
                {
                    "project_name": row.get("project_name"),
                    "repo_name": row.get("repo_name"),
                    "repo_path": row.get("repo_path"),
                    "exists": bool(row.get("exists")),
                    "status": row.get("status"),
                    "agent_surfaces": probe,
                }
            )
        return cards

    def _score_readiness(
        self,
        *,
        gate_status,
        map_stats: DiscoveryMapStats,
        health: WorkspaceHealthResult,
        agent_surfaces: AgentSurfaceStats,
    ) -> ReadinessScore:
        gate_active = gate_status.state.value == "active"
        gate_score = 100 if gate_active else 0

        repos_total = max(map_stats.repos_total, 1)
        repos_score = int(round(100 * map_stats.repos_present / repos_total))
        if map_stats.repos_total == 0:
            repos_score = 100

        maint_score = 100
        for item in health.recommendations:
            if item.severity == "critical":
                maint_score -= 30
            elif item.severity == "warning":
                maint_score -= 10
        maint_score = max(0, maint_score)

        umbrella = 0
        if agent_surfaces.manifest_has_agent_instructions:
            umbrella += 40
        if agent_surfaces.umbrella_has_agents_md:
            umbrella += 30
        if agent_surfaces.umbrella_has_llms_txt:
            umbrella += 30
        if agent_surfaces.repos_audited == 0:
            repo_fraction = 1.0 if map_stats.repos_total == 0 else 0.0
        else:
            repo_fraction = agent_surfaces.repos_with_any_surface / agent_surfaces.repos_audited
        agent_score = min(100, int(round(umbrella * 0.6 + 40 * repo_fraction)))

        dimensions = {
            "gate_active": ReadinessDimension(
                score=gate_score,
                weight=_READINESS_WEIGHTS["gate_active"],
                met=gate_active,
            ),
            "repos_present": ReadinessDimension(
                score=repos_score,
                weight=_READINESS_WEIGHTS["repos_present"],
                met=repos_score >= 75,
            ),
            "maintenance_clear": ReadinessDimension(
                score=maint_score,
                weight=_READINESS_WEIGHTS["maintenance_clear"],
                met=maint_score >= 75,
            ),
            "agent_surfaces": ReadinessDimension(
                score=agent_score,
                weight=_READINESS_WEIGHTS["agent_surfaces"],
                met=agent_score >= 75,
            ),
        }
        composite = int(round(sum(dim.score * dim.weight for dim in dimensions.values())))
        blockers = self._blockers(
            gate_active=gate_active,
            gate_reason=gate_status.reason,
            map_stats=map_stats,
            health=health,
            agent_surfaces=agent_surfaces,
        )
        return ReadinessScore(
            score=composite,
            grade=readiness_grade(composite),  # type: ignore[arg-type]
            dimensions=dimensions,
            blockers=blockers,
            suggested_commands=self._suggested_commands(blockers),
        )

    def _blockers(
        self,
        *,
        gate_active: bool,
        gate_reason: Optional[str],
        map_stats: DiscoveryMapStats,
        health: WorkspaceHealthResult,
        agent_surfaces: AgentSurfaceStats,
    ) -> list[ReadinessBlocker]:
        blockers: list[ReadinessBlocker] = []
        if not gate_active:
            blockers.append(
                ReadinessBlocker(
                    code="gate_inactive",
                    severity="critical",
                    message=gate_reason or "Workspace gate is not active.",
                )
            )
        for item in health.recommendations:
            if item.severity not in ("critical", "warning"):
                continue
            if item.action == "clone":
                blockers.append(
                    ReadinessBlocker(
                        code="missing_clone",
                        severity=item.severity,
                        message=item.message,
                        project_name=item.project_name,
                        repo_name=item.repo_name,
                    )
                )
            elif item.severity == "critical":
                blockers.append(
                    ReadinessBlocker(
                        code=item.action,
                        severity="critical",
                        message=item.message,
                        project_name=item.project_name,
                        repo_name=item.repo_name,
                    )
                )
        if map_stats.repos_missing and not any(b.code == "missing_clone" for b in blockers):
            blockers.append(
                ReadinessBlocker(
                    code="missing_clone",
                    severity="warning",
                    message=f"{map_stats.repos_missing} configured repo(s) missing on disk.",
                )
            )
        if not agent_surfaces.manifest_has_agent_instructions:
            blockers.append(
                ReadinessBlocker(
                    code="missing_agent_instructions",
                    severity="info",
                    message="Manifest lacks agent_instructions for session guidance.",
                )
            )
        if not agent_surfaces.umbrella_has_agents_md:
            blockers.append(
                ReadinessBlocker(
                    code="missing_agents_md",
                    severity="info",
                    message="Umbrella workspace has no AGENTS.md.",
                )
            )
        if not agent_surfaces.umbrella_has_llms_txt:
            blockers.append(
                ReadinessBlocker(
                    code="missing_llms_txt",
                    severity="info",
                    message="Umbrella workspace has no llms.txt.",
                )
            )
        return blockers

    def _suggested_commands(self, blockers: list[ReadinessBlocker]) -> list[str]:
        commands: list[str] = []
        codes = {b.code for b in blockers}
        projects = sorted({b.project_name for b in blockers if b.code == "missing_clone" and b.project_name})
        for project in projects:
            cmd = f"metagit project sync --project {project}"
            if cmd not in commands:
                commands.append(cmd)
        if "missing_clone" in codes and not projects:
            commands.append("metagit project sync")
        if codes & {"missing_agents_md", "missing_llms_txt", "missing_agent_instructions"}:
            commands.append("metagit init --agent-optimized  # on repos missing AGENTS.md")
        if "gate_inactive" in codes:
            commands.append("metagit config validate")
        return commands
