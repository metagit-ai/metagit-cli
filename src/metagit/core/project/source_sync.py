#!/usr/bin/env python
"""
Provider-backed recursive repository discovery and workspace planning.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import requests

from metagit.core.appconfig.models import AppConfig
from metagit.core.project.models import ProjectPath
from metagit.core.project.source_enrichment import (
    enrich_discovered_repos,
    merge_repo_tags,
    topics_to_tags,
)
from metagit.core.project.source_filters import apply_source_filters
from metagit.core.project.source_naming import resolve_manifest_names
from metagit.core.project.source_models import (
    DiscoveredRepo,
    SourceProvider,
    SourceSpec,
    SourceSyncMode,
    SourceSyncPlan,
)
from metagit.core.utils.common import normalize_git_url
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.providers import ProviderRegistry
from metagit.core.workspace.models import WorkspaceProject
from metagit.core.workspace.protection import project_is_protected


class SourceSyncService:
    """Discovers repositories from providers and builds/apply sync plans."""

    def __init__(self, app_config: AppConfig, logger: UnifiedLogger):
        self._app_config = app_config
        self._logger = logger

    def discover(self, spec: SourceSpec) -> Union[List[DiscoveredRepo], Exception]:
        try:
            if spec.provider == SourceProvider.GITHUB:
                raw = self._discover_github(spec)
            elif spec.provider == SourceProvider.GITLAB:
                raw = self._discover_gitlab(spec)
            else:
                return Exception(f"Unsupported provider: {spec.provider}")

            if isinstance(raw, Exception):
                return raw

            raw_count = len(raw)
            filtered = apply_source_filters(spec, raw)
            registry = ProviderRegistry()
            registry.configure_from_app_config(self._app_config)
            enriched = enrich_discovered_repos(spec, filtered, registry, self._logger)
            self._logger.info(
                f"Source discovery: raw={raw_count} filtered={len(enriched)}"
            )
            return enriched
        except Exception as exc:
            return exc

    def plan(
        self,
        spec: SourceSpec,
        project: WorkspaceProject,
        discovered: List[DiscoveredRepo],
        mode: SourceSyncMode,
    ) -> SourceSyncPlan:
        manifest_names = resolve_manifest_names(
            discovered,
            strategy=spec.name_strategy,
        )
        discovered_project_paths = [
            self._to_project_path(
                spec, repo, manifest_names.get(repo.clone_url, repo.name)
            )
            for repo in discovered
        ]
        discovered_by_url = {
            self._normalized_url(path.url): path
            for path in discovered_project_paths
            if path.url
        }
        existing_by_url = {
            self._normalized_url(repo.url): repo for repo in project.repos if repo.url
        }

        plan = SourceSyncPlan(
            discovered_count=len(discovered),
            filtered_count=len(discovered),
        )

        for url_key, new_repo in discovered_by_url.items():
            existing = existing_by_url.get(url_key)
            if existing is None:
                existing = self._find_existing_by_repo_id(project, new_repo)
            if existing is None:
                plan.to_add.append(new_repo)
                continue
            if spec.ensure and not spec.refresh_metadata:
                plan.unchanged += 1
                continue
            if self._needs_update(existing, new_repo, spec):
                plan.to_update.append(self._merge_repo_update(existing, new_repo, spec))
            else:
                plan.unchanged += 1

        if mode == SourceSyncMode.RECONCILE:
            for repo in project.repos:
                if project_is_protected(project):
                    continue
                if not repo.url:
                    continue
                if bool(repo.protected):
                    continue
                if spec.source_id and repo.source_id != spec.source_id:
                    continue
                if not spec.source_id:
                    if repo.source_provider != spec.provider.value:
                        continue
                    if repo.source_namespace != spec.namespace_key:
                        continue
                url_key = self._normalized_url(repo.url)
                if url_key not in discovered_by_url:
                    plan.to_remove.append(repo)

        return plan

    def apply_plan(
        self, project: WorkspaceProject, plan: SourceSyncPlan, mode: SourceSyncMode
    ) -> WorkspaceProject:
        if mode == SourceSyncMode.DISCOVER:
            return project

        repos: List[ProjectPath] = list(project.repos)
        repo_index: Dict[str, int] = {}
        for index, repo in enumerate(repos):
            if repo.url:
                repo_index[self._normalized_url(repo.url)] = index

        for candidate in plan.to_add:
            repos.append(candidate)

        for candidate in plan.to_update:
            if not candidate.url:
                continue
            url_key = self._normalized_url(candidate.url)
            if url_key in repo_index:
                repos[repo_index[url_key]] = candidate

        remove_keys = set()
        for candidate in plan.to_remove:
            if candidate.url:
                remove_keys.add(self._normalized_url(candidate.url))

        if remove_keys:
            repos = [
                repo
                for repo in repos
                if not repo.url or self._normalized_url(repo.url) not in remove_keys
            ]

        return WorkspaceProject(
            name=project.name,
            description=project.description,
            agent_instructions=project.agent_instructions,
            dedupe=project.dedupe,
            protected=project.protected,
            tags=dict(project.tags),
            documentation=project.documentation,
            metadata=dict(project.metadata),
            repos=repos,
        )

    def _discover_github(
        self, spec: SourceSpec
    ) -> Union[List[DiscoveredRepo], Exception]:
        provider_cfg = self._app_config.providers.github
        if not provider_cfg.enabled:
            return Exception("GitHub provider is disabled in app config")
        if not provider_cfg.api_token:
            return Exception("GitHub API token is not configured")

        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"token {provider_cfg.api_token}",
                "Accept": "application/vnd.github+json",
            }
        )

        scope_kind = "orgs" if spec.org else "users"
        scope_value = spec.org if spec.org else spec.user
        endpoint = f"{provider_cfg.base_url}/{scope_kind}/{scope_value}/repos"

        discovered: List[DiscoveredRepo] = []
        page = 1
        while True:
            response = session.get(
                endpoint,
                params={"per_page": 100, "page": page, "type": "all"},
                timeout=30,
            )
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for repo in items:
                candidate = DiscoveredRepo(
                    provider=SourceProvider.GITHUB,
                    namespace=spec.namespace_key,
                    full_name=repo.get("full_name", ""),
                    name=repo.get("name", ""),
                    clone_url=repo.get("clone_url", ""),
                    default_branch=repo.get("default_branch"),
                    description=repo.get("description"),
                    repo_id=str(repo.get("id")) if repo.get("id") is not None else None,
                    archived=bool(repo.get("archived", False)),
                    fork=bool(repo.get("fork", False)),
                    private=repo.get("private"),
                    language=repo.get("language"),
                )
                discovered.append(candidate)
            page += 1
        return discovered

    def _discover_gitlab(
        self, spec: SourceSpec
    ) -> Union[List[DiscoveredRepo], Exception]:
        provider_cfg = self._app_config.providers.gitlab
        if not provider_cfg.enabled:
            return Exception("GitLab provider is disabled in app config")
        if not provider_cfg.api_token:
            return Exception("GitLab API token is not configured")

        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {provider_cfg.api_token}"})

        group_ref = requests.utils.quote(spec.group or "", safe="")
        endpoint = f"{provider_cfg.base_url}/groups/{group_ref}/projects"

        discovered: List[DiscoveredRepo] = []
        page = 1
        while True:
            response = session.get(
                endpoint,
                params={
                    "per_page": 100,
                    "page": page,
                    "include_subgroups": "true" if spec.recursive else "false",
                    "with_shared": "false",
                },
                timeout=30,
            )
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for repo in items:
                visibility = repo.get("visibility")
                candidate = DiscoveredRepo(
                    provider=SourceProvider.GITLAB,
                    namespace=spec.namespace_key,
                    full_name=repo.get("path_with_namespace", ""),
                    name=repo.get("path", ""),
                    clone_url=repo.get("http_url_to_repo", ""),
                    default_branch=repo.get("default_branch"),
                    description=repo.get("description"),
                    repo_id=str(repo.get("id")) if repo.get("id") is not None else None,
                    archived=bool(repo.get("archived", False)),
                    fork=repo.get("forked_from_project") is not None,
                    private=(visibility in {"private", "internal"}),
                    language=repo.get("language"),
                    topics=list(repo.get("topics") or []),
                )
                discovered.append(candidate)
            page += 1
        return discovered

    def _to_project_path(
        self,
        spec: SourceSpec,
        repo: DiscoveredRepo,
        manifest_name: str,
    ) -> ProjectPath:
        incoming_tags = topics_to_tags(repo.topics, repo.provider.value)
        return ProjectPath(
            name=manifest_name,
            description=repo.description,
            url=repo.clone_url,
            sync=True,
            language=repo.language,
            source_provider=repo.provider.value,
            source_namespace=repo.namespace,
            source_repo_id=repo.repo_id,
            source_id=spec.source_id,
            tags=incoming_tags,
        )

    def _find_existing_by_repo_id(
        self,
        project: WorkspaceProject,
        incoming: ProjectPath,
    ) -> Optional[ProjectPath]:
        if not incoming.source_repo_id:
            return None
        for repo in project.repos:
            if repo.source_repo_id == incoming.source_repo_id:
                return repo
        return None

    def _needs_update(
        self,
        current: ProjectPath,
        incoming: ProjectPath,
        spec: SourceSpec,
    ) -> bool:
        tracked_fields: List[Tuple[Optional[str], Optional[str]]] = [
            (current.name, incoming.name),
            (current.description, incoming.description),
            (current.source_provider, incoming.source_provider),
            (current.source_namespace, incoming.source_namespace),
            (current.source_repo_id, incoming.source_repo_id),
            (current.language, incoming.language),
        ]
        if any(lhs != rhs for lhs, rhs in tracked_fields):
            return True
        if spec.refresh_metadata:
            return current.tags != incoming.tags
        for key, value in incoming.tags.items():
            if key not in current.tags:
                return True
        return False

    def _merge_repo_update(
        self,
        current: ProjectPath,
        incoming: ProjectPath,
        spec: SourceSpec,
    ) -> ProjectPath:
        merged_tags = merge_repo_tags(
            dict(current.tags),
            dict(incoming.tags),
            refresh_metadata=spec.refresh_metadata,
        )
        return incoming.model_copy(update={"tags": merged_tags})

    def _normalized_url(self, url: Optional[object]) -> str:
        if not url:
            return ""
        return normalize_git_url(str(url))
