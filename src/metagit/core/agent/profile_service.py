#!/usr/bin/env python
"""Resolve, validate, and apply inheritable agent_profile blocks."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from metagit.core.agent.paths import AGENT_SUPPORTED_TARGETS
from metagit.core.agent.profile_catalog import (
    bundled_rules_root,
    validate_profile_references,
)
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.project.models import ProjectPath
from metagit.core.skills.installer import (
    InstallScope,
    install_mcp_for_targets,
    install_skills_for_targets,
)
from metagit.core.workspace.agent_profile_models import (
    AgentApplySummary,
    AgentApplyTargetResult,
    AgentProfile,
    AgentProfileLayer,
    AgentProfileValidationIssue,
    EffectiveAgentProfile,
)
from metagit.core.workspace.layout_resolver import find_project, find_repo
from metagit.core.workspace.models import WorkspaceProject
from metagit.core.workspace.protection import merge_project_repo_tags

_VENDOR_RULE_DIRS: dict[str, str] = {
    "cursor": ".cursor/rules",
    "claude_code": ".claude/rules",
    "github_copilot": ".github/instructions",
    "windsurf": ".windsurf/rules",
}


class AgentProfileService:
    """Merge agent_profile blocks and materialize them into vendor runtimes."""

    def __init__(
        self,
        *,
        config: MetagitConfig,
        definition_root: Path,
        workspace_root: Optional[Path] = None,
    ) -> None:
        self._config = config
        self._definition_root = definition_root.resolve()
        self._workspace_root = (workspace_root or definition_root).resolve()
        self._index = WorkspaceIndexService()

    def effective_profile(
        self,
        *,
        project_name: str,
        repo_name: str,
    ) -> Optional[EffectiveAgentProfile]:
        """Return the merged profile for one manifest repo entry."""
        project = find_project(self._config, project_name)
        if project is None:
            return None
        repo = find_repo(project, repo_name)
        if repo is None:
            return None
        return self._merge_for_repo(project=project, repo=repo)

    def list_validation_issues(self) -> list[AgentProfileValidationIssue]:
        """Validate every declared agent_profile reference against bundled catalogs."""
        issues: list[AgentProfileValidationIssue] = []
        if not self._config.workspace:
            return issues
        workspace_profile = self._config.workspace.agent_profile
        if workspace_profile is not None:
            issues.extend(self._validate_one(workspace_profile, scope="workspace"))
        for project in self._config.workspace.projects:
            if project.agent_profile is not None:
                issues.extend(
                    self._validate_one(
                        project.agent_profile,
                        scope="project",
                        project=project.name,
                    ),
                )
            for repo in project.repos:
                if repo.agent_profile is None:
                    continue
                issues.extend(
                    self._validate_one(
                        repo.agent_profile,
                        scope="repo",
                        project=project.name,
                        repo=repo.name,
                    ),
                )
        return issues

    def select_targets(
        self,
        *,
        project: Optional[str] = None,
        repo: Optional[str] = None,
        tag_filters: Optional[dict[str, str]] = None,
    ) -> list[tuple[str, str, ProjectPath, str]]:
        """Return (project_name, repo_name, repo_model, repo_path) rows matching filters."""
        if not self._config.workspace:
            return []
        rows: list[tuple[str, str, ProjectPath, str]] = []
        index_rows = {
            (item["project_name"], item["repo_name"]): item["repo_path"]
            for item in self._index.build_index(
                self._config,
                str(self._workspace_root),
                definition_root=str(self._definition_root),
            )
        }
        for project_model in self._config.workspace.projects:
            if project and project_model.name != project:
                continue
            for repo_model in project_model.repos:
                if repo and repo_model.name != repo:
                    continue
                if tag_filters and not _tags_match(
                    merge_project_repo_tags(project_model, repo_model),
                    tag_filters,
                ):
                    continue
                repo_path = index_rows.get(
                    (project_model.name, repo_model.name),
                    str(self._definition_root),
                )
                rows.append((project_model.name, repo_model.name, repo_model, repo_path))
        return rows

    def apply(
        self,
        *,
        vendor: str,
        scope: InstallScope = "project",
        project: Optional[str] = None,
        repo: Optional[str] = None,
        tag_filters: Optional[dict[str, str]] = None,
        dry_run: bool = False,
    ) -> AgentApplySummary:
        """Materialize merged profiles into vendor artifacts for matching repos."""
        if vendor not in AGENT_SUPPORTED_TARGETS:
            supported = ", ".join(AGENT_SUPPORTED_TARGETS)
            raise ValueError(f"Unknown vendor {vendor!r}. Supported: {supported}")

        summary = AgentApplySummary(vendor=vendor, dry_run=dry_run)
        for project_name, _repo_name, repo_model, repo_path in self.select_targets(
            project=project,
            repo=repo,
            tag_filters=tag_filters,
        ):
            project_model = find_project(self._config, project_name)
            if project_model is None:
                continue
            effective = self._merge_for_repo(project=project_model, repo=repo_model)
            if effective is None:
                continue
            if effective.vendors and vendor not in effective.vendors:
                continue
            target_result = self._apply_one(
                effective=effective,
                vendor=vendor,
                scope=scope,
                repo_path=Path(repo_path),
                dry_run=dry_run,
            )
            summary.targets.append(target_result)
        return summary

    def _apply_one(
        self,
        *,
        effective: EffectiveAgentProfile,
        vendor: str,
        scope: InstallScope,
        repo_path: Path,
        dry_run: bool,
    ) -> AgentApplyTargetResult:
        details: list[str] = []
        install_results = []
        applied = False
        cwd = Path.cwd()
        try:
            os.chdir(repo_path)
            if effective.skills:
                skill_results = install_skills_for_targets(
                    [vendor],
                    scope,
                    effective.skills,
                    dry_run=dry_run,
                )
                install_results.extend(skill_results)
                applied = applied or any(item.applied for item in skill_results)
                details.extend(item.details for item in skill_results if item.details)
            if "metagit" in effective.mcp:
                if dry_run:
                    details.append(f"Would configure MCP server 'metagit' for {vendor}")
                    applied = True
                else:
                    mcp_results = install_mcp_for_targets([vendor], scope, server_name="metagit")
                    install_results.extend(mcp_results)
                    applied = applied or any(item.applied for item in mcp_results)
                    details.extend(item.details for item in mcp_results if item.details)
            for server_name in [name for name in effective.mcp if name != "metagit"]:
                details.append(f"Skipped MCP server {server_name!r} (no bundled installer yet)")
            if effective.rules:
                rule_details, rule_applied = self._install_rules(
                    vendor=vendor,
                    rule_ids=effective.rules,
                    dry_run=dry_run,
                )
                details.extend(rule_details)
                applied = applied or rule_applied
        finally:
            os.chdir(cwd)

        return AgentApplyTargetResult(
            project_name=effective.project_name,
            repo_name=effective.repo_name,
            repo_path=str(repo_path),
            vendor=vendor,
            applied=applied,
            dry_run=dry_run,
            details=details,
            install_results=install_results,
        )

    def _install_rules(
        self,
        *,
        vendor: str,
        rule_ids: list[str],
        dry_run: bool,
    ) -> tuple[list[str], bool]:
        """Copy bundled rules into the vendor-specific rules directory."""
        rel_dir = _VENDOR_RULE_DIRS.get(vendor)
        if rel_dir is None:
            return [f"No rules directory mapping for vendor {vendor!r}"], False
        destination_root = Path.cwd() / rel_dir
        source_root = bundled_rules_root()
        details: list[str] = []
        applied = False
        for rule_id in rule_ids:
            source = _rule_source_file(source_root, rule_id)
            if source is None:
                details.append(f"Rule {rule_id!r} not found in bundled catalog")
                continue
            dest = destination_root / source.name
            verb = "Would install" if dry_run else "Installed"
            details.append(f"{verb} rule {rule_id!r} -> {dest}")
            applied = True
            if dry_run:
                continue
            destination_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        return details, applied

    def _merge_for_repo(
        self,
        *,
        project: WorkspaceProject,
        repo: ProjectPath,
    ) -> Optional[EffectiveAgentProfile]:
        layers: list[AgentProfileLayer] = []
        merged: Optional[AgentProfile] = None
        if self._config.workspace and self._config.workspace.agent_profile is not None:
            workspace_profile = self._config.workspace.agent_profile
            layers.append(AgentProfileLayer(scope="workspace", profile=workspace_profile))
            merged = _merge_profiles(merged, workspace_profile)
        if project.agent_profile is not None:
            layers.append(AgentProfileLayer(scope="project", profile=project.agent_profile))
            merged = _merge_profiles(merged, project.agent_profile)
        if repo.agent_profile is not None:
            layers.append(AgentProfileLayer(scope="repo", profile=repo.agent_profile))
            merged = _merge_profiles(merged, repo.agent_profile)
        if merged is None:
            tier = repo.tags.get("agent_tier") or project.tags.get("agent_tier")
            if not tier:
                return None
            merged = AgentProfile(tier=tier, inherit=False)
        tier = merged.tier or repo.tags.get("agent_tier") or project.tags.get("agent_tier")
        return EffectiveAgentProfile(
            project_name=project.name,
            repo_name=repo.name,
            tier=tier,
            skills=list(merged.skills),
            mcp=list(merged.mcp),
            rules=list(merged.rules),
            vendors=list(merged.vendors),
            layers=layers,
        )

    def _validate_one(
        self,
        profile: AgentProfile,
        *,
        scope: str,
        project: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> list[AgentProfileValidationIssue]:
        issues: list[AgentProfileValidationIssue] = []
        for vendor in profile.vendors:
            if vendor not in AGENT_SUPPORTED_TARGETS:
                issues.append(
                    AgentProfileValidationIssue(
                        scope=scope,
                        project=project,
                        repo=repo,
                        field="vendors",
                        value=vendor,
                        message=f"unknown vendor {vendor!r}",
                    ),
                )
        for message in validate_profile_references(
            skills=profile.skills,
            mcp=profile.mcp,
            rules=profile.rules,
        ):
            field = "skills"
            if message.startswith("unknown mcp"):
                field = "mcp"
            elif message.startswith("unknown rule"):
                field = "rules"
            issues.append(
                AgentProfileValidationIssue(
                    scope=scope,
                    project=project,
                    repo=repo,
                    field=field,
                    value="",
                    message=message,
                ),
            )
        return issues


def _merge_profiles(
    parent: Optional[AgentProfile],
    child: AgentProfile,
) -> AgentProfile:
    """Merge child into parent using inherit semantics."""
    if parent is None or not child.inherit:
        return child.model_copy(deep=True)
    return AgentProfile(
        tier=child.tier or parent.tier,
        skills=_merge_lists(parent.skills, child.skills),
        mcp=_merge_lists(parent.mcp, child.mcp),
        rules=_merge_lists(parent.rules, child.rules),
        vendors=_merge_lists(parent.vendors, child.vendors),
        inherit=True,
    )


def _merge_lists(parent: list[str], child: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in [*parent, *child]:
        if item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def _tags_match(tags: dict[str, str], filters: dict[str, str]) -> bool:
    return all(tags.get(key) == value for key, value in filters.items())


def _rule_source_file(source_root: Path, rule_id: str) -> Optional[Path]:
    for suffix in (".mdc", ".md"):
        candidate = source_root / f"{rule_id}{suffix}"
        if candidate.is_file():
            return candidate
    if not source_root.exists():
        return None
    for item in source_root.iterdir():
        if item.is_file() and item.stem == rule_id:
            return item
    return None
