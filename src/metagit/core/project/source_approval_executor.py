#!/usr/bin/env python
"""
Apply approved source reconcile removals to the workspace manifest.
"""

from __future__ import annotations

from typing import Any, Union

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.context.models import ApprovalRequest
from metagit.core.project.models import ProjectPath
from metagit.core.utils.common import normalize_git_url


class SourceSyncApprovalExecutor:
    """Apply ``source_sync_reconcile`` approval payloads to ``.metagit.yml``."""

    def apply_if_approved(
        self,
        *,
        approval: ApprovalRequest,
        config: MetagitConfig,
        config_path: str,
    ) -> Union[MetagitConfig, Exception]:
        if approval.action != "source_sync_reconcile":
            return config
        if approval.status != "approved":
            return Exception("approval is not approved")
        return self.apply_payload(
            payload=approval.payload,
            config=config,
            config_path=config_path,
        )

    def apply_payload(
        self,
        *,
        payload: dict[str, Any],
        config: MetagitConfig,
        config_path: str,
    ) -> Union[MetagitConfig, Exception]:
        project_name = str(payload.get("project", "")).strip()
        if not project_name or not config.workspace:
            return Exception("invalid source_sync_reconcile payload: project")

        project = next(
            (item for item in config.workspace.projects if item.name == project_name),
            None,
        )
        if project is None:
            return Exception(f"project '{project_name}' not found")

        remove_urls = _removal_url_keys(payload.get("to_remove"))
        if not remove_urls:
            return Exception("invalid source_sync_reconcile payload: to_remove")

        updated_repos = [
            repo
            for repo in project.repos
            if not _repo_matches_removal(repo, remove_urls)
        ]
        updated_project = project.model_copy(update={"repos": updated_repos})
        for index, item in enumerate(config.workspace.projects):
            if item.name == project_name:
                config.workspace.projects[index] = updated_project
                break

        save_result = MetagitConfigManager(config_path=config_path).save_config(
            config, config_path
        )
        if isinstance(save_result, Exception):
            return save_result
        return config


def _removal_url_keys(raw: object) -> set[str]:
    if not isinstance(raw, list):
        return set()
    keys: set[str] = set()
    for item in raw:
        if isinstance(item, dict) and item.get("url"):
            keys.add(normalize_git_url(str(item["url"])))
    return keys


def _repo_matches_removal(repo: ProjectPath, remove_urls: set[str]) -> bool:
    if not repo.url:
        return False
    return normalize_git_url(str(repo.url)) in remove_urls
