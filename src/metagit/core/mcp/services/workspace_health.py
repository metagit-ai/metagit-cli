#!/usr/bin/env python
"""
Workspace integrity and maintenance health checks.
"""

from __future__ import annotations

from typing import Any, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.gate import WorkspaceGate
from metagit.core.mcp.services.gitnexus_registry import GitNexusRegistryAdapter
from metagit.core.mcp.services.repo_git_stats import inspect_repo_state
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.workspace.health_models import (
    HealthRecommendation,
    RepoHealthRow,
    WorkspaceHealthResult,
)


class WorkspaceHealthService:
    """Validate workspace integrity and emit maintenance recommendations."""

    def __init__(
        self,
        index_service: Optional[WorkspaceIndexService] = None,
        registry: Optional[GitNexusRegistryAdapter] = None,
        gate: Optional[WorkspaceGate] = None,
    ) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._registry = registry or GitNexusRegistryAdapter()
        self._gate = gate or WorkspaceGate()

    def check(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        check_git_status: bool = True,
        check_dependencies: bool = True,
        check_stale_branches: bool = True,
        check_gitnexus: bool = True,
        project_name: Optional[str] = None,
        branch_head_warning_days: float = 180.0,
        branch_head_critical_days: float = 365.0,
        integration_stale_days: float = 90.0,
    ) -> WorkspaceHealthResult:
        """Run selected health checks across workspace repositories."""
        gate_status = self._gate.evaluate(root_path=workspace_root)
        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        if project_name:
            rows = [row for row in rows if row["project_name"] == project_name]

        recommendations: list[HealthRecommendation] = []
        repo_rows: list[RepoHealthRow] = []
        gitnexus_map: dict[str, str] = {}
        if check_gitnexus:
            paths = [str(row["repo_path"]) for row in rows if row.get("exists")]
            gitnexus_map = self._registry.summarize_for_paths(repo_paths=paths)

        missing_count = 0
        dirty_count = 0
        behind_count = 0
        stale_gn_count = 0
        stale_head_warn_count = 0
        stale_head_critical_count = 0
        integration_stale_count = 0

        for row in rows:
            repo_path = str(row.get("repo_path", ""))
            inspect_git = (
                row.get("exists")
                and row.get("is_git_repo")
                and (check_git_status or check_stale_branches)
            )
            inspected = inspect_repo_state(repo_path=repo_path) if inspect_git else {}
            gn_status = gitnexus_map.get(repo_path) if check_gitnexus else None
            head_age_days = (
                float(inspected["head_commit_age_days"])
                if isinstance(inspected.get("head_commit_age_days"), (int, float))
                else None
            )
            merge_age_days = (
                float(inspected["merge_base_age_days"])
                if isinstance(inspected.get("merge_base_age_days"), (int, float))
                else None
            )
            repo_rows.append(
                RepoHealthRow(
                    project_name=str(row.get("project_name", "")),
                    repo_name=str(row.get("repo_name", "")),
                    repo_path=repo_path,
                    status=str(row.get("status", "")),
                    exists=bool(row.get("exists")),
                    is_git_repo=bool(row.get("is_git_repo")),
                    branch=str(inspected.get("branch"))
                    if inspected.get("branch") is not None
                    else None,
                    dirty=bool(inspected.get("dirty"))
                    if check_git_status and inspected.get("dirty") is not None
                    else None,
                    ahead=int(inspected["ahead"])
                    if check_git_status and isinstance(inspected.get("ahead"), int)
                    else None,
                    behind=int(inspected["behind"])
                    if check_git_status and isinstance(inspected.get("behind"), int)
                    else None,
                    gitnexus_status=gn_status,
                    head_commit_age_days=head_age_days
                    if check_stale_branches
                    else None,
                    merge_base_age_days=merge_age_days
                    if check_stale_branches
                    else None,
                )
            )

            if check_dependencies and row.get("status") == "configured_missing":
                missing_count += 1
                recommendations.append(
                    HealthRecommendation(
                        severity="warning",
                        action="clone",
                        message="Configured repository path is missing on disk.",
                        project_name=row.get("project_name"),
                        repo_name=row.get("repo_name"),
                        repo_path=repo_path,
                    )
                )

            if check_stale_branches and inspected.get("ok"):
                warn_td = min(branch_head_warning_days, branch_head_critical_days)
                crit_td = max(branch_head_warning_days, branch_head_critical_days)
                if head_age_days is not None:
                    if head_age_days >= crit_td:
                        stale_head_critical_count += 1
                        recommendations.append(
                            HealthRecommendation(
                                severity="warning",
                                action="review_branch_age",
                                message=(
                                    "HEAD commit is stale "
                                    f"({head_age_days:.0f}d); merge or archive."
                                ),
                                project_name=row.get("project_name"),
                                repo_name=row.get("repo_name"),
                                repo_path=repo_path,
                            )
                        )
                    elif head_age_days >= warn_td:
                        stale_head_warn_count += 1
                        recommendations.append(
                            HealthRecommendation(
                                severity="info",
                                action="review_branch_age",
                                message=(
                                    "HEAD commit is aging "
                                    f"({head_age_days:.0f}d since last commit on HEAD)."
                                ),
                                project_name=row.get("project_name"),
                                repo_name=row.get("repo_name"),
                                repo_path=repo_path,
                            )
                        )
                if (
                    merge_age_days is not None
                    and merge_age_days >= integration_stale_days
                ):
                    integration_stale_count += 1
                    recommendations.append(
                        HealthRecommendation(
                            severity="warning",
                            action="reconcile_integration",
                            message=(
                                "Merge-base with default remote branch is old "
                                f"({merge_age_days:.0f}d); rebase or merge default."
                            ),
                            project_name=row.get("project_name"),
                            repo_name=row.get("repo_name"),
                            repo_path=repo_path,
                        )
                    )

            if check_git_status and inspected.get("ok"):
                if inspected.get("dirty"):
                    dirty_count += 1
                    recommendations.append(
                        HealthRecommendation(
                            severity="info",
                            action="review_changes",
                            message="Repository has uncommitted changes.",
                            project_name=row.get("project_name"),
                            repo_name=row.get("repo_name"),
                            repo_path=repo_path,
                        )
                    )
                behind = inspected.get("behind")
                if isinstance(behind, int) and behind > 0:
                    behind_count += 1
                    recommendations.append(
                        HealthRecommendation(
                            severity="warning",
                            action="sync",
                            message=f"Repository is {behind} commit(s) behind upstream.",
                            project_name=row.get("project_name"),
                            repo_name=row.get("repo_name"),
                            repo_path=repo_path,
                        )
                    )
                if inspected.get("branch") == "DETACHED":
                    recommendations.append(
                        HealthRecommendation(
                            severity="warning",
                            action="fix_branch",
                            message="Repository is in detached HEAD state.",
                            project_name=row.get("project_name"),
                            repo_name=row.get("repo_name"),
                            repo_path=repo_path,
                        )
                    )

            if check_gitnexus and row.get("exists") and row.get("is_git_repo"):
                if gn_status == "stale":
                    stale_gn_count += 1
                    recommendations.append(
                        HealthRecommendation(
                            severity="warning",
                            action="analyze",
                            message="GitNexus index is stale; run gitnexus analyze.",
                            project_name=row.get("project_name"),
                            repo_name=row.get("repo_name"),
                            repo_path=repo_path,
                        )
                    )
                elif gn_status == "missing":
                    recommendations.append(
                        HealthRecommendation(
                            severity="info",
                            action="analyze",
                            message="Repository is not indexed in GitNexus.",
                            project_name=row.get("project_name"),
                            repo_name=row.get("repo_name"),
                            repo_path=repo_path,
                        )
                    )

        if gate_status.state.value != "active":
            recommendations.insert(
                0,
                HealthRecommendation(
                    severity="critical",
                    action="fix_config",
                    message=gate_status.reason
                    or "Workspace configuration is not active.",
                ),
            )

        recommendations.extend(self._duplicate_url_warnings(rows=rows))
        summary = {
            "repos_total": len(repo_rows),
            "repos_missing": missing_count,
            "repos_dirty": dirty_count,
            "repos_behind": behind_count,
            "repos_gitnexus_stale": stale_gn_count,
            "repos_branch_head_stale_warning": stale_head_warn_count,
            "repos_branch_head_stale_critical": stale_head_critical_count,
            "repos_integration_stale": integration_stale_count,
            "recommendations": len(recommendations),
        }
        critical = sum(1 for item in recommendations if item.severity == "critical")
        return WorkspaceHealthResult(
            ok=critical == 0,
            workspace_root=workspace_root,
            summary=summary,
            repos=repo_rows,
            recommendations=self._sort_recommendations(recommendations),
        )

    def _duplicate_url_warnings(
        self, rows: list[dict[str, Any]]
    ) -> list[HealthRecommendation]:
        """Warn when multiple repos share the same configured URL."""
        by_url: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            url = row.get("url")
            if not url:
                continue
            by_url.setdefault(str(url), []).append(row)
        warnings: list[HealthRecommendation] = []
        for url, grouped in by_url.items():
            if len(grouped) < 2:
                continue
            names = ", ".join(
                f"{item['project_name']}/{item['repo_name']}" for item in grouped
            )
            warnings.append(
                HealthRecommendation(
                    severity="info",
                    action="review_config",
                    message=f"Multiple repos share URL {url}: {names}",
                )
            )
        return warnings

    def _sort_recommendations(
        self, recommendations: list[HealthRecommendation]
    ) -> list[HealthRecommendation]:
        """Sort recommendations by severity."""
        order = {"critical": 0, "warning": 1, "info": 2}
        return sorted(recommendations, key=lambda item: order.get(item.severity, 3))
