#!/usr/bin/env python3
"""
GitLab provider for repository metadata and metrics.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import requests

from metagit.core.config.models import CommitFrequency, Metrics, PullRequests
from metagit.core.providers.base import GitProvider
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class GitLabProvider(GitProvider):
    """GitLab provider plugin."""

    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize GitLab provider.

        Args:
            api_token: GitLab personal access token
            base_url: Base URL for GitLab API (for self-hosted instances)
        """
        super().__init__(api_token, base_url)
        self.api_base = base_url or "https://gitlab.com/api/v4"
        self.session = requests.Session()

        if api_token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                }
            )

    def get_name(self) -> str:
        """Get the provider name."""
        return "GitLab"

    def can_handle_url(self, url: str) -> bool:
        """Check if this provider can handle the given repository URL."""
        parsed = urlparse(url)
        return (
            parsed.netloc in ["gitlab.com", "www.gitlab.com"]
            or parsed.netloc.endswith(".gitlab.com")
            or (self.base_url and parsed.netloc == urlparse(self.base_url).netloc)
        )

    def extract_repo_info(self, url: str) -> Dict[str, str]:
        """Extract owner and repo from GitLab URL."""
        normalized_url = normalize_git_url(url)

        # GitLab URL patterns
        patterns = [
            r"gitlab\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"git@gitlab\.com:([^/]+)/([^/]+?)(?:\.git)?/?$",
        ]

        for pattern in patterns:
            match = re.match(pattern, normalized_url)
            if match:
                return {"owner": match.group(1), "repo": match.group(2)}

        return {}

    def get_repository_metrics(
        self, owner: str, repo: str
    ) -> Union[Metrics, Exception]:
        """Get repository metrics from GitLab API."""
        try:
            if not self.api_token:
                return Exception("GitLab API token required for metrics")

            project_path = f"{owner}/{repo}"
            project_id = project_path.replace("/", "%2F")

            # Get project data
            project_url = f"{self.api_base}/projects/{project_id}"
            project_response = self.session.get(project_url)
            project_response.raise_for_status()
            project_data = project_response.json()

            # Get issues data
            issues_url = f"{self.api_base}/projects/{project_id}/issues"
            issues_params = {"state": "opened", "per_page": 1}
            issues_response = self.session.get(issues_url, params=issues_params)
            issues_response.raise_for_status()

            # Get merge requests data
            mr_url = f"{self.api_base}/projects/{project_id}/merge_requests"
            mr_params = {"state": "opened", "per_page": 1}
            mr_response = self.session.get(mr_url, params=mr_params)
            mr_response.raise_for_status()

            # Get contributors data (approximation using project members)
            members_url = f"{self.api_base}/projects/{project_id}/members"
            members_response = self.session.get(members_url)
            members_data = (
                members_response.json() if members_response.status_code == 200 else []
            )

            # Get recent commits for commit frequency
            commits_url = f"{self.api_base}/projects/{project_id}/repository/commits"
            commits_params = {"per_page": 100}
            commits_response = self.session.get(commits_url, params=commits_params)
            commits_response.raise_for_status()
            commits_data = commits_response.json()

            # Calculate commit frequency
            commit_frequency = self._calculate_commit_frequency(commits_data)

            # Create pull requests object (GitLab calls them merge requests)
            pull_requests = PullRequests(
                open=len(mr_response.json()),
                merged_last_30d=0,  # Would need additional API call for this
            )

            # Create metrics object
            metrics = Metrics(
                stars=project_data.get("star_count", 0),
                forks=project_data.get("forks_count", 0),
                open_issues=len(issues_response.json()),
                pull_requests=pull_requests,
                contributors=len(members_data),
                commit_frequency=commit_frequency,
            )

            return metrics

        except requests.RequestException as e:
            return Exception(f"GitLab API request failed: {e}")
        except Exception as e:
            return Exception(f"Failed to get GitLab metrics: {e}")

    def get_repository_metadata(
        self, owner: str, repo: str
    ) -> Union[Dict[str, Any], Exception]:
        """Get additional repository metadata from GitLab API."""
        try:
            if not self.api_token:
                return Exception("GitLab API token required for metadata")

            project_path = f"{owner}/{repo}"
            project_id = project_path.replace("/", "%2F")

            project_url = f"{self.api_base}/projects/{project_id}"
            response = self.session.get(project_url)
            response.raise_for_status()
            project_data = response.json()

            metadata = {
                "name": project_data.get("name"),
                "description": project_data.get("description"),
                "topics": project_data.get("topics", []),
                "created_at": project_data.get("created_at"),
                "updated_at": project_data.get("last_activity_at"),
                "default_branch": project_data.get("default_branch"),
                "archived": project_data.get("archived", False),
                "fork": project_data.get("forked_from_project") is not None,
                "private": project_data.get("visibility") == "private",
                "homepage": project_data.get("web_url"),
                "size": project_data.get("statistics", {}).get("repository_size"),
                "watchers_count": project_data.get("star_count"),
                "forks_count": project_data.get("forks_count"),
                "open_issues_count": project_data.get("open_issues_count"),
                "visibility": project_data.get("visibility"),
                "namespace": project_data.get("namespace", {}).get("name"),
            }

            return metadata

        except requests.RequestException as e:
            return Exception(f"GitLab API request failed: {e}")
        except Exception as e:
            return Exception(f"Failed to get GitLab metadata: {e}")

    def _calculate_commit_frequency(
        self, commits_data: List[Dict[str, Any]]
    ) -> CommitFrequency:
        """Calculate commit frequency from recent commits."""
        if not commits_data or len(commits_data) < 2:
            return CommitFrequency.MONTHLY

        # Get commit dates
        commit_dates = []
        for commit in commits_data:
            if "created_at" in commit:
                commit_dates.append(commit["created_at"])

        if len(commit_dates) < 2:
            return CommitFrequency.MONTHLY

        # Calculate frequency based on recent activity
        from datetime import datetime, timedelta, timezone

        recent_commits = 0
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        for date_str in commit_dates[:10]:  # Check last 10 commits
            try:
                commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if commit_date >= week_ago:
                    recent_commits += 1
            except Exception:
                continue

        if recent_commits >= 5:
            return CommitFrequency.DAILY
        elif recent_commits >= 1:
            return CommitFrequency.WEEKLY
        else:
            return CommitFrequency.MONTHLY
