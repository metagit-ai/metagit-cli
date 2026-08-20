#!/usr/bin/env python3
"""
Azure DevOps provider for repository metadata and metrics.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import quote, urlparse

import requests

from metagit.core.config.models import CommitFrequency, Metrics, PullRequests
from metagit.core.project.ci_target_resolver import parse_remote_locator
from metagit.core.providers.base import GitProvider
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class AzureDevOpsGitProvider(GitProvider):
    """Azure DevOps Repos provider plugin."""

    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_token, base_url)
        self.api_base = (base_url or "https://dev.azure.com").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if api_token:
            token = base64.b64encode(f":{api_token}".encode("utf-8")).decode("ascii")
            self.session.headers.update({"Authorization": f"Basic {token}"})

    def get_name(self) -> str:
        return "Azure DevOps"

    def can_handle_url(self, url: str) -> bool:
        normalized = normalize_git_url(url)
        parsed = urlparse(normalized if "://" in normalized else f"https://{normalized}")
        host = (parsed.hostname or "").lower()
        if "dev.azure.com" in host or "visualstudio.com" in host:
            return True
        if "://" not in url and "@" in url and ":" in url:
            _, remainder = url.split("@", 1)
            host_part = remainder.split(":", 1)[0].lower()
            return "dev.azure.com" in host_part or "visualstudio.com" in host_part
        if self.base_url:
            configured = urlparse(self.base_url).hostname
            if configured and host == configured.lower():
                return True
        return False

    def extract_repo_info(self, url: str) -> Dict[str, str]:
        locator = parse_remote_locator(url)
        org = locator.get("organization") or ""
        project = locator.get("project") or ""
        repo = locator.get("repository") or ""
        if not org or not repo:
            return {}
        owner = f"{org}/{project}" if project else org
        return {
            "owner": owner,
            "repo": repo,
            "organization": org,
            "project": project,
            "api_url": self.api_base,
        }

    def get_repository_metrics(self, owner: str, repo: str) -> Union[Metrics, Exception]:
        try:
            metadata = self.get_repository_metadata(owner, repo)
            if isinstance(metadata, Exception):
                return metadata
            return Metrics(
                stars=0,
                forks=0,
                open_issues=0,
                contributors=0,
                pull_requests=PullRequests(open=0, merged_last_30d=0),
                commit_frequency=CommitFrequency.UNKNOWN,
            )
        except Exception as exc:
            return exc

    def get_repository_metadata(self, owner: str, repo: str) -> Union[Dict[str, Any], Exception]:
        try:
            if not self.api_token:
                return Exception("Azure DevOps API token required for metadata")
            organization, project = self._split_owner(owner)
            if not organization or not project:
                return Exception("Azure DevOps metadata requires organization/project owner path")
            project_ref = quote(project, safe="")
            repo_ref = quote(repo, safe="")
            endpoint = f"{self.api_base}/{organization}/{project_ref}/_apis/git/repositories/{repo_ref}"
            response = self.session.get(endpoint, params={"api-version": "7.1"}, timeout=30)
            response.raise_for_status()
            data = response.json()
            return {
                "name": data.get("name"),
                "description": data.get("project", {}).get("description"),
                "default_branch": str(data.get("defaultBranch") or "").replace("refs/heads/", "") or None,
                "private": True,
                "topics": [],
                "url": data.get("remoteUrl") or data.get("webUrl"),
                "id": data.get("id"),
            }
        except Exception as exc:
            return exc

    def _split_owner(self, owner: str) -> tuple[str, str]:
        parts = [part for part in owner.split("/") if part]
        if len(parts) >= 2:
            return parts[0], "/".join(parts[1:])
        return owner, ""
