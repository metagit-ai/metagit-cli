#!/usr/bin/env python
"""
Repository Terrain DTO assembly for the MetaGit 3D web visualization.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from git import Repo
from git.exc import GitCommandError
from pydantic import BaseModel, Field

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.repo_git_stats import inspect_repo_state
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.web.graph_service import WorkspaceGraphService
from metagit.core.web.pipeline_status_service import (
    PipelineQueryOptions,
    PipelineStatusService,
)

TILE_SPACING = 2.8
PROJECT_SPACING = 24.0
FLAT_ELEVATION = 0.0
LOCAL_WORK_SCALE = 0.16
BEHIND_SCALE = 0.14
MAX_ELEVATION = 4.0
MIN_ELEVATION = -3.0

SyncColor = Literal[
    "synced_main",
    "main_local_work",
    "behind_remote",
    "behind_heavy",
    "feature_branch",
    "develop_branch",
    "hotfix_branch",
    "detached",
    "other_branch",
    "conflict",
    "gray",
    "unknown",
]
ActivityLevel = Literal["active", "recent", "inactive", "abandoned"]
BranchKind = Literal["default", "feature", "develop", "hotfix", "detached", "other"]
DependencyHealth = Literal["healthy", "outdated", "broken"]
PipelineStatusKind = Literal[
    "passed",
    "failed",
    "running",
    "pending",
    "canceled",
    "skipped",
    "unknown",
]
TerrainDetailLevel = Literal["manifest", "enriched"]


class TerrainCoordinates(BaseModel):
    """Grid placement for a repository tile."""

    x: float
    y: float
    z: float = 0.0
    region: Optional[str] = None


class TerrainGitState(BaseModel):
    """Normalized git inspection fields for terrain rendering."""

    branch: Optional[str] = None
    default_branch: Optional[str] = None
    branch_kind: BranchKind = "other"
    ahead: int = 0
    behind: int = 0
    dirty: bool = False
    uncommitted_count: int = 0
    untracked_count: int = 0
    modified_count: int = 0
    merge_conflicts: bool = False
    detached_head: bool = False
    head_commit_age_days: Optional[float] = None


class TerrainPipelineState(BaseModel):
    """CI/CD beacon metadata for a repository tile."""

    status: PipelineStatusKind = "unknown"
    provider: Optional[str] = None
    workflow: Optional[str] = None
    updated_at: Optional[str] = None
    duration_sec: Optional[float] = None
    web_url: Optional[str] = None
    result: Optional[str] = None


class TerrainActivity(BaseModel):
    """Recent commit activity windows."""

    commits_24h: int = 0
    commits_7d: int = 0
    commits_30d: int = 0
    level: ActivityLevel = "abandoned"
    pulse_intensity: float = Field(default=0.0, ge=0.0, le=1.0)


class TerrainAgentState(BaseModel):
    """Agent-readiness hints for future holographic overlays."""

    has_agents_md: bool = False
    has_llms_txt: bool = False
    has_agent_instructions: bool = False
    documentation_score: float = Field(default=0.0, ge=0.0, le=1.0)


class TerrainVisualState(BaseModel):
    """Precomputed visual hints consumed by the Three.js renderer."""

    elevation: float = 0.0
    sync_color: SyncColor = "gray"
    state_label: str = "Unknown"
    local_pressure: int = 0
    surface_fracture: float = Field(default=0.0, ge=0.0, le=1.0)
    fissure_glow: float = Field(default=0.0, ge=0.0, le=1.0)
    crack_severity: float = Field(default=0.0, ge=0.0, le=1.0)
    darken_factor: float = Field(default=0.0, ge=0.0, le=1.0)
    fade_factor: float = Field(default=0.0, ge=0.0, le=1.0)


class RepositoryTerrainNode(BaseModel):
    """Single repository tile in the terrain map."""

    id: str
    project_name: str
    repo_name: str
    label: str
    repo_path: str
    configured_path: Optional[str] = None
    exists: bool = False
    is_git_repo: bool = False
    local_status: str = "unknown"
    url: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    ownership: Optional[str] = None
    coordinates: TerrainCoordinates
    git: TerrainGitState
    pipeline: Optional[TerrainPipelineState] = None
    activity: TerrainActivity
    agent: TerrainAgentState
    visual: TerrainVisualState
    dependencies_out: int = 0
    dependencies_in: int = 0


class TerrainDependency(BaseModel):
    """Cross-repository dependency arc."""

    id: str
    from_id: str
    to_id: str
    type: str
    label: Optional[str] = None
    source: Literal["manual", "inferred", "structure"] = "inferred"
    health: DependencyHealth = "healthy"
    consumer_count: int = 1


class TerrainRegion(BaseModel):
    """Directory cluster bounding region."""

    id: str
    label: str
    project_name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float


class TerrainProjectOption(BaseModel):
    """Project entry for terrain UI filtering."""

    name: str
    repo_count: int = 0


class RepositoryTerrainResponse(BaseModel):
    """Normalized payload for the Repository Terrain SPA."""

    ok: bool = True
    fetched_at: str
    detail_level: TerrainDetailLevel = "enriched"
    project_filter: Optional[str] = None
    node_count: int = 0
    projects: list[TerrainProjectOption] = Field(default_factory=list)
    nodes: list[RepositoryTerrainNode] = Field(default_factory=list)
    dependencies: list[TerrainDependency] = Field(default_factory=list)
    regions: list[TerrainRegion] = Field(default_factory=list)


class RepositoryTerrainService:
    """Assemble terrain nodes from workspace index, git, CI, and graph data."""

    def __init__(
        self,
        *,
        index_service: Optional[WorkspaceIndexService] = None,
        graph_service: Optional[WorkspaceGraphService] = None,
        pipeline_service: Optional[PipelineStatusService] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._graph = graph_service or WorkspaceGraphService()
        self._pipelines = pipeline_service or PipelineStatusService()

    def build_view(
        self,
        *,
        config: MetagitConfig,
        app_config: AppConfig,
        workspace_root: str,
        definition_root: str,
        project_filter: Optional[str] = None,
        detail_level: TerrainDetailLevel = "enriched",
        include_pipelines: bool = False,
        include_inferred_deps: bool = True,
        limit: int = 2000,
    ) -> RepositoryTerrainResponse:
        """Return terrain-ready nodes, dependency arcs, and directory regions."""
        all_rows = self._index.build_index(
            config=config,
            workspace_root=workspace_root,
            definition_root=definition_root,
        )
        projects = _project_options(all_rows)
        rows = list(all_rows)
        if project_filter:
            rows = [row for row in rows if row["project_name"] == project_filter]
        rows = rows[:limit]

        manifest_only = detail_level == "manifest"
        pipeline_by_key: dict[str, dict[str, Any]] = {}
        if include_pipelines and not manifest_only:
            pipeline_by_key = self._load_pipeline_map(
                config=config,
                app_config=app_config,
                workspace_root=workspace_root,
                definition_root=definition_root,
                project_filter=project_filter,
                limit=limit,
            )

        layout = _compute_layout(rows)
        nodes: list[RepositoryTerrainNode] = []
        for row in rows:
            if manifest_only:
                node = self._build_manifest_node(row, layout)
            else:
                node = self._build_node(row, layout, pipeline_by_key)
            nodes.append(node)

        include_inferred = include_inferred_deps and not manifest_only
        graph_view = self._graph.build_view(
            config,
            workspace_root,
            include_inferred=include_inferred,
            include_structure=False,
        )
        repo_ids = {node.id for node in nodes}
        in_counts: dict[str, int] = defaultdict(int)
        out_counts: dict[str, int] = defaultdict(int)
        dependencies: list[TerrainDependency] = []
        for edge in graph_view.edges:
            if edge.from_id not in repo_ids or edge.to_id not in repo_ids:
                continue
            if edge.source == "structure":
                continue
            out_counts[edge.from_id] += 1
            in_counts[edge.to_id] += 1
            dependencies.append(
                TerrainDependency(
                    id=edge.id,
                    from_id=edge.from_id,
                    to_id=edge.to_id,
                    type=edge.type,
                    label=edge.label,
                    source=edge.source,
                    health=_dependency_health(edge.type, edge.label),
                    consumer_count=1,
                )
            )

        for dep in dependencies:
            dep.consumer_count = max(in_counts.get(dep.to_id, 1), 1)

        for node in nodes:
            node.dependencies_in = in_counts.get(node.id, 0)
            node.dependencies_out = out_counts.get(node.id, 0)

        regions = _build_regions(nodes)
        return RepositoryTerrainResponse(
            ok=True,
            fetched_at=_iso_now(),
            detail_level=detail_level,
            project_filter=project_filter,
            node_count=len(nodes),
            projects=projects,
            nodes=nodes,
            dependencies=dependencies,
            regions=regions,
        )

    def _build_manifest_node(
        self,
        row: dict[str, Any],
        layout: dict[str, TerrainCoordinates],
    ) -> RepositoryTerrainNode:
        """Fast skeleton node from workspace index only (no git or CI I/O)."""
        project_name = str(row["project_name"])
        repo_name = str(row["repo_name"])
        node_id = f"repo:{project_name}/{repo_name}"
        configured_path = row.get("configured_path")
        configured_str = str(configured_path) if isinstance(configured_path, str) else None
        raw_tags = row.get("tags")
        tags = [f"{key}={value}" for key, value in sorted(raw_tags.items())] if isinstance(raw_tags, dict) else []
        ownership = _ownership_from_tags(raw_tags if isinstance(raw_tags, dict) else {})
        exists = bool(row.get("exists"))
        url_raw = row.get("url")
        url = str(url_raw) if isinstance(url_raw, str) else None
        local_status = str(row.get("status", "unknown"))
        sync_color: SyncColor = "unknown"
        if local_status == "configured_missing":
            sync_color = "gray"

        return RepositoryTerrainNode(
            id=node_id,
            project_name=project_name,
            repo_name=repo_name,
            label=repo_name,
            repo_path=str(row["repo_path"]),
            configured_path=configured_str,
            exists=exists,
            is_git_repo=bool(row.get("is_git_repo")),
            local_status=local_status,
            url=url,
            tags=tags,
            ownership=ownership,
            coordinates=layout.get(node_id, TerrainCoordinates(x=0.0, y=0.0)),
            git=TerrainGitState(),
            pipeline=None,
            activity=TerrainActivity(),
            agent=TerrainAgentState(),
            visual=TerrainVisualState(sync_color=sync_color, state_label="Manifest entry"),
        )

    def _load_pipeline_map(
        self,
        *,
        config: MetagitConfig,
        app_config: AppConfig,
        workspace_root: str,
        definition_root: str,
        project_filter: Optional[str],
        limit: int,
    ) -> dict[str, dict[str, Any]]:
        result = self._pipelines.pipeline_status(
            config=config,
            app_config=app_config,
            workspace_root=workspace_root,
            definition_root=definition_root,
            options=PipelineQueryOptions(
                project=project_filter,
                include_unsynced=True,
                limit=limit,
            ),
        )
        out: dict[str, dict[str, Any]] = {}
        for row in result.get("rows", []):
            if not isinstance(row, dict):
                continue
            key = f"{row.get('project_name', '')}/{row.get('repo_name', '')}"
            out[key] = row
        return out

    def _build_node(
        self,
        row: dict[str, Any],
        layout: dict[str, TerrainCoordinates],
        pipeline_by_key: dict[str, dict[str, Any]],
    ) -> RepositoryTerrainNode:
        project_name = str(row["project_name"])
        repo_name = str(row["repo_name"])
        node_id = f"repo:{project_name}/{repo_name}"
        repo_path = str(row["repo_path"])
        exists = bool(row.get("exists"))
        is_git_repo = bool(row.get("is_git_repo"))
        configured_path = row.get("configured_path")
        configured_str = str(configured_path) if isinstance(configured_path, str) else None

        raw_tags = row.get("tags")
        tags = [f"{key}={value}" for key, value in sorted(raw_tags.items())] if isinstance(raw_tags, dict) else []
        ownership = _ownership_from_tags(raw_tags if isinstance(raw_tags, dict) else {})

        inspected: dict[str, Any] = dict(inspect_repo_state(repo_path=repo_path)) if exists and is_git_repo else {}
        git_state = _build_git_state(inspected, repo_path if exists and is_git_repo else None)
        activity = _activity_metrics(repo_path) if exists and is_git_repo else TerrainActivity()
        agent = _agent_state(repo_path) if exists else TerrainAgentState()
        visual = _visual_state(git_state, activity)

        pipeline_row = pipeline_by_key.get(f"{project_name}/{repo_name}")
        pipeline = _pipeline_from_row(pipeline_row) if pipeline_row else None

        url_raw = row.get("url")
        url = str(url_raw) if isinstance(url_raw, str) else None

        return RepositoryTerrainNode(
            id=node_id,
            project_name=project_name,
            repo_name=repo_name,
            label=repo_name,
            repo_path=repo_path,
            configured_path=configured_str,
            exists=exists,
            is_git_repo=is_git_repo,
            local_status=str(row.get("status", "unknown")),
            url=url,
            tags=tags,
            ownership=ownership,
            coordinates=layout.get(
                node_id,
                TerrainCoordinates(x=0.0, y=0.0),
            ),
            git=git_state,
            pipeline=pipeline,
            activity=activity,
            agent=agent,
            visual=visual,
        )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_options(rows: list[dict[str, Any]]) -> list[TerrainProjectOption]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row["project_name"])] += 1
    return [TerrainProjectOption(name=name, repo_count=counts[name]) for name in sorted(counts.keys())]


def _ownership_from_tags(tags: dict[str, str]) -> Optional[str]:
    for key in ("owner", "ownership", "team", "squad"):
        value = tags.get(key)
        if value:
            return value
    return None


def _dependency_health(edge_type: str, label: Optional[str]) -> DependencyHealth:
    lowered = f"{edge_type} {label or ''}".lower()
    if any(token in lowered for token in ("broken", "missing", "failed")):
        return "broken"
    if any(token in lowered for token in ("outdated", "stale", "deprecated")):
        return "outdated"
    return "healthy"


def _build_git_state(
    inspected: dict[str, Any],
    repo_path: Optional[str],
) -> TerrainGitState:
    if inspected.get("ok") is not True:
        return TerrainGitState()

    branch_raw = inspected.get("branch")
    branch = branch_raw if isinstance(branch_raw, str) else None
    detached = branch == "DETACHED"
    default_branch = _default_branch(repo_path) if repo_path else None
    branch_kind = _branch_kind(branch, default_branch, detached)

    ahead_raw = inspected.get("ahead")
    behind_raw = inspected.get("behind")
    ahead = ahead_raw if isinstance(ahead_raw, int) else 0
    behind = behind_raw if isinstance(behind_raw, int) else 0

    dirty = inspected.get("dirty") is True
    uncommitted_raw = inspected.get("uncommitted_count")
    uncommitted = uncommitted_raw if isinstance(uncommitted_raw, int) else 0

    untracked = _untracked_count(repo_path) if repo_path and dirty else 0
    modified = max(uncommitted - untracked, 0)
    merge_conflicts = _has_merge_conflicts(repo_path) if repo_path else False

    age_raw = inspected.get("head_commit_age_days")
    age = float(age_raw) if isinstance(age_raw, (int, float)) else None

    return TerrainGitState(
        branch=branch,
        default_branch=default_branch,
        branch_kind=branch_kind,
        ahead=max(ahead, 0),
        behind=max(behind, 0),
        dirty=dirty,
        uncommitted_count=uncommitted,
        untracked_count=untracked,
        modified_count=modified,
        merge_conflicts=merge_conflicts,
        detached_head=detached,
        head_commit_age_days=age,
    )


def _branch_kind(
    branch: Optional[str],
    default_branch: Optional[str],
    detached: bool,
) -> BranchKind:
    if detached:
        return "detached"
    if not branch:
        return "other"
    normalized = branch.lower()
    if default_branch and branch == default_branch:
        return "default"
    if normalized in {"main", "master"}:
        return "default"
    if normalized in {"develop", "development", "dev"}:
        return "develop"
    if normalized.startswith("hotfix") or normalized.startswith("fix/"):
        return "hotfix"
    if normalized.startswith("feature/") or normalized.startswith("feat/"):
        return "feature"
    return "other"


def _default_branch(repo_path: str) -> Optional[str]:
    try:
        repo = Repo(repo_path)
        out = repo.git.symbolic_ref("refs/remotes/origin/HEAD").strip()
        if out.startswith("refs/remotes/origin/"):
            return out[len("refs/remotes/origin/") :]
    except GitCommandError:
        pass
    for candidate in ("main", "master", "develop"):
        try:
            Repo(repo_path).git.rev_parse("--verify", f"origin/{candidate}")
            return candidate
        except GitCommandError:
            continue
    return None


def _untracked_count(repo_path: str) -> int:
    try:
        return len(Repo(repo_path).untracked_files)
    except Exception:
        return 0


def _has_merge_conflicts(repo_path: str) -> bool:
    try:
        return bool(Repo(repo_path).index.unmerged_blobs())
    except Exception:
        return False


def _activity_metrics(repo_path: str) -> TerrainActivity:
    try:
        repo = Repo(repo_path)
        c24 = int(repo.git.rev_list("--count", "--since=24 hours ago", "HEAD") or 0)
        c7 = int(repo.git.rev_list("--count", "--since=7 days ago", "HEAD") or 0)
        c30 = int(repo.git.rev_list("--count", "--since=30 days ago", "HEAD") or 0)
    except Exception:
        return TerrainActivity()

    if c24 > 0:
        level: ActivityLevel = "active"
        pulse = min(1.0, 0.35 + c24 * 0.08)
    elif c7 > 0:
        level = "recent"
        pulse = min(0.6, 0.15 + c7 * 0.03)
    elif c30 > 0:
        level = "inactive"
        pulse = 0.0
    else:
        level = "abandoned"
        pulse = 0.0

    return TerrainActivity(
        commits_24h=c24,
        commits_7d=c7,
        commits_30d=c30,
        level=level,
        pulse_intensity=pulse,
    )


def _agent_state(repo_path: str) -> TerrainAgentState:
    root = Path(repo_path)
    has_agents = (root / "AGENTS.md").is_file()
    has_llms = (root / "llms.txt").is_file()
    has_readme = (root / "README.md").is_file()
    score = 0.0
    if has_agents:
        score += 0.5
    if has_llms:
        score += 0.25
    if has_readme:
        score += 0.15
    if (root / "docs").is_dir():
        score += 0.1
    return TerrainAgentState(
        has_agents_md=has_agents,
        has_llms_txt=has_llms,
        has_agent_instructions=has_agents,
        documentation_score=min(score, 1.0),
    )


def _local_pressure(git: TerrainGitState) -> int:
    """Unpushed commits plus uncommitted file changes."""
    return git.ahead + git.uncommitted_count


def _is_synced_main(git: TerrainGitState) -> bool:
    return (
        git.branch_kind == "default"
        and not git.dirty
        and git.ahead == 0
        and git.behind == 0
        and not git.merge_conflicts
        and not git.detached_head
    )


def _branch_sync_color(branch_kind: BranchKind) -> SyncColor:
    mapping: dict[BranchKind, SyncColor] = {
        "default": "main_local_work",
        "feature": "feature_branch",
        "develop": "develop_branch",
        "hotfix": "hotfix_branch",
        "detached": "detached",
        "other": "other_branch",
    }
    return mapping.get(branch_kind, "other_branch")


def _state_label(sync_color: SyncColor, git: TerrainGitState, pressure: int) -> str:
    labels: dict[SyncColor, str] = {
        "synced_main": "Synced on default branch",
        "main_local_work": "Default branch with local or unpushed work",
        "behind_remote": "Behind remote — pull to resync",
        "behind_heavy": "Heavily behind remote",
        "feature_branch": "Feature branch",
        "develop_branch": "Develop branch",
        "hotfix_branch": "Hotfix branch",
        "detached": "Detached HEAD",
        "other_branch": "Non-default branch",
        "conflict": "Merge conflicts",
        "gray": "Missing or unavailable",
        "unknown": "Awaiting git enrichment",
    }
    base = labels.get(sync_color, "Repository state")
    if git.branch and sync_color not in {"synced_main", "gray", "unknown"}:
        base = f"{base} · {git.branch}"
    if pressure > 0 and sync_color not in {"conflict", "gray", "unknown"}:
        return f"{base} · {pressure} local change unit(s)"
    return base


def _visual_state(git: TerrainGitState, activity: TerrainActivity) -> TerrainVisualState:
    pressure = _local_pressure(git)
    sync_color: SyncColor = "gray"
    elevation = FLAT_ELEVATION

    if git.merge_conflicts:
        sync_color = "conflict"
        elevation = min(pressure * LOCAL_WORK_SCALE + 0.45, MAX_ELEVATION)
    elif _is_synced_main(git):
        sync_color = "synced_main"
        elevation = FLAT_ELEVATION
    elif git.behind > 0 and pressure == 0 and git.branch_kind == "default":
        sync_color = "behind_heavy" if git.behind > 5 else "behind_remote"
        elevation = max(-git.behind * BEHIND_SCALE, MIN_ELEVATION)
    elif git.branch_kind == "default":
        sync_color = "main_local_work"
        elevation = min(pressure * LOCAL_WORK_SCALE, MAX_ELEVATION)
        if git.behind > 0:
            elevation -= min(git.behind * BEHIND_SCALE * 0.45, MAX_ELEVATION * 0.5)
            elevation = max(elevation, MIN_ELEVATION)
    else:
        sync_color = _branch_sync_color(git.branch_kind)
        elevation = min(pressure * LOCAL_WORK_SCALE, MAX_ELEVATION)
        if git.behind > 0:
            elevation -= min(git.behind * BEHIND_SCALE * 0.35, MAX_ELEVATION * 0.4)
            elevation = max(elevation, MIN_ELEVATION)

    if not git.branch and pressure == 0 and git.behind == 0 and not git.merge_conflicts:
        sync_color = "gray"
        elevation = FLAT_ELEVATION

    elevation = max(MIN_ELEVATION, min(MAX_ELEVATION, elevation))

    fracture = min(1.0, git.modified_count * 0.12) if git.dirty else 0.0
    fissure = min(1.0, git.untracked_count * 0.15) if git.untracked_count else 0.0
    crack = 1.0 if git.merge_conflicts else min(0.8, fracture * 0.5)

    darken = 0.0
    fade = 0.0
    if sync_color in {"behind_remote", "behind_heavy"}:
        darken = 0.2 if sync_color == "behind_remote" else 0.35
    elif activity.level == "inactive":
        darken = 0.25
    elif activity.level == "abandoned":
        darken = 0.45
        fade = 0.35

    return TerrainVisualState(
        elevation=elevation,
        sync_color=sync_color,
        state_label=_state_label(sync_color, git, pressure),
        local_pressure=pressure,
        surface_fracture=fracture,
        fissure_glow=fissure,
        crack_severity=crack,
        darken_factor=darken,
        fade_factor=fade,
    )


def _pipeline_from_row(row: dict[str, Any]) -> TerrainPipelineState:
    status_raw = str(row.get("pipeline_status", "unknown"))
    status: PipelineStatusKind = (
        status_raw
        if status_raw
        in {
            "passed",
            "failed",
            "running",
            "pending",
            "canceled",
            "skipped",
            "unknown",
        }
        else "unknown"
    )
    duration_raw = row.get("duration_sec")
    duration = float(duration_raw) if isinstance(duration_raw, (int, float)) else None
    return TerrainPipelineState(
        status=status,
        provider=str(row.get("provider")) if row.get("provider") else None,
        workflow=str(row.get("pipeline_name")) if row.get("pipeline_name") else None,
        updated_at=str(row.get("updated_at")) if row.get("updated_at") else None,
        duration_sec=duration,
        web_url=str(row.get("web_url")) if row.get("web_url") else None,
        result=status,
    )


def _compute_layout(rows: list[dict[str, Any]]) -> dict[str, TerrainCoordinates]:
    """Place repositories on a grid derived from filesystem hierarchy."""
    by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_project[str(row["project_name"])].append(row)

    layout: dict[str, TerrainCoordinates] = {}
    for project_index, project_name in enumerate(sorted(by_project.keys())):
        project_rows = by_project[project_name]
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in project_rows:
            rel = row.get("configured_path") or row.get("repo_name") or ""
            rel_path = Path(str(rel))
            parent = str(rel_path.parent) if rel_path.parent != Path(".") else ""
            groups[parent].append(row)

        base_x = project_index * PROJECT_SPACING
        group_keys = sorted(groups.keys(), key=lambda key: (key.count("/"), key))
        group_y_offset = 0.0
        for group_key in group_keys:
            group_rows = sorted(
                groups[group_key],
                key=lambda item: str(item.get("repo_name", "")),
            )
            depth = len(Path(group_key).parts) if group_key else 0
            for sibling_index, row in enumerate(group_rows):
                repo_name = str(row["repo_name"])
                node_id = f"repo:{project_name}/{repo_name}"
                x = base_x + depth * TILE_SPACING + sibling_index * 0.35
                y = group_y_offset + sibling_index * TILE_SPACING
                region = group_key or project_name
                layout[node_id] = TerrainCoordinates(x=x, y=y, region=region)
            group_y_offset += max(len(group_rows), 1) * TILE_SPACING * 0.85

    return layout


def _build_regions(nodes: list[RepositoryTerrainNode]) -> list[TerrainRegion]:
    buckets: dict[tuple[str, str], list[RepositoryTerrainNode]] = defaultdict(list)
    for node in nodes:
        region_key = node.coordinates.region or node.project_name
        buckets[(node.project_name, region_key)].append(node)

    regions: list[TerrainRegion] = []
    padding = TILE_SPACING * 0.6
    for (project_name, region_label), members in sorted(buckets.items()):
        xs = [member.coordinates.x for member in members]
        ys = [member.coordinates.y for member in members]
        region_id = f"region:{project_name}:{region_label}"
        regions.append(
            TerrainRegion(
                id=region_id,
                label=region_label,
                project_name=project_name,
                min_x=min(xs) - padding,
                max_x=max(xs) + padding,
                min_y=min(ys) - padding,
                max_y=max(ys) + padding,
            )
        )
    return regions


__all__ = [
    "RepositoryTerrainNode",
    "RepositoryTerrainResponse",
    "RepositoryTerrainService",
    "TerrainDependency",
]
