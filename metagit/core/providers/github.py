#!/usr/bin/env python3
"""
GitHub provider for repository metadata and metrics.
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


class GitHubProvider(GitProvider):
    """GitHub provider plugin."""

    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize GitHub provider.

        Args:
            api_token: GitHub personal access token
            base_url: Base URL for GitHub API (for GitHub Enterprise)
        """
        super().__init__(api_token, base_url)
        self.api_base = base_url or "https://api.github.com"
        self.session = requests.Session()

        if api_token:
            self.session.headers.update(
                {
                    "Authorization": f"token {api_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )

    def get_name(self) -> str:
        """Get the provider name."""
        return "GitHub"

    def can_handle_url(self, url: str) -> bool:
        """Check if this provider can handle the given repository URL."""
        parsed = urlparse(url)
        return (
            parsed.netloc in ["github.com", "www.github.com"]
            or parsed.netloc.endswith(".github.com")
            or (self.base_url and parsed.netloc == urlparse(self.base_url).netloc)
        )

    def extract_repo_info(self, url: str) -> Dict[str, str]:
        """Extract owner and repo from GitHub URL."""
        normalized_url = normalize_git_url(url)

        # GitHub URL patterns
        patterns = [
            r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?/?$",
        ]

        for pattern in patterns:
            match = re.match(pattern, normalized_url)
            if match:
                return {"owner": match.group(1), "repo": match.group(2)}

        return {}

    def get_repository_metrics(
        self, owner: str, repo: str
    ) -> Union[Metrics, Exception]:
        """Get repository metrics from GitHub API."""
        try:
            if not self.api_token:
                return Exception("GitHub API token required for metrics")

            # Get repository data
            repo_url = f"{self.api_base}/repos/{owner}/{repo}"
            repo_response = self.session.get(repo_url)
            repo_response.raise_for_status()
            repo_data = repo_response.json()

            # Get issues data
            issues_url = f"{self.api_base}/repos/{owner}/{repo}/issues"
            issues_params = {"state": "open", "per_page": 1}
            issues_response = self.session.get(issues_url, params=issues_params)
            issues_response.raise_for_status()

            # Get pull requests data
            prs_url = f"{self.api_base}/repos/{owner}/{repo}/pulls"
            prs_params = {"state": "open", "per_page": 1}
            prs_response = self.session.get(prs_url, params=prs_params)
            prs_response.raise_for_status()

            # Get contributors data
            contributors_url = f"{self.api_base}/repos/{owner}/{repo}/contributors"
            contributors_response = self.session.get(contributors_url)
            contributors_response.raise_for_status()
            contributors_data = contributors_response.json()

            # Get recent commits for commit frequency
            commits_url = f"{self.api_base}/repos/{owner}/{repo}/commits"
            commits_params = {"per_page": 100}
            commits_response = self.session.get(commits_url, params=commits_params)
            commits_response.raise_for_status()
            commits_data = commits_response.json()

            # Calculate commit frequency
            commit_frequency = self._calculate_commit_frequency(commits_data)

            # Create pull requests object
            pull_requests = PullRequests(
                open=len(prs_response.json()),
                merged_last_30d=0,  # Would need additional API call for this
            )

            # Create metrics object
            metrics = Metrics(
                stars=repo_data.get("stargazers_count", 0),
                forks=repo_data.get("forks_count", 0),
                open_issues=repo_data.get("open_issues_count", 0),
                pull_requests=pull_requests,
                contributors=len(contributors_data),
                commit_frequency=commit_frequency,
            )

            return metrics

        except requests.RequestException as e:
            return Exception(f"GitHub API request failed: {e}")
        except Exception as e:
            return Exception(f"Failed to get GitHub metrics: {e}")

    def get_repository_metadata(
        self, owner: str, repo: str
    ) -> Union[Dict[str, Any], Exception]:
        """Get additional repository metadata from GitHub API."""
        try:
            if not self.api_token:
                return Exception("GitHub API token required for metadata")

            repo_url = f"{self.api_base}/repos/{owner}/{repo}"
            response = self.session.get(repo_url)
            response.raise_for_status()
            repo_data = response.json()

            # Get topics
            topics_url = f"{self.api_base}/repos/{owner}/{repo}/topics"
            topics_response = self.session.get(topics_url)
            topics_data = (
                topics_response.json()
                if topics_response.status_code == 200
                else {"names": []}
            )

            metadata = {
                "name": repo_data.get("name"),
                "description": repo_data.get("description"),
                "language": repo_data.get("language"),
                "topics": topics_data.get("names", []),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "default_branch": repo_data.get("default_branch"),
                "license": (
                    repo_data.get("license", {}).get("name")
                    if repo_data.get("license")
                    else None
                ),
                "archived": repo_data.get("archived", False),
                "fork": repo_data.get("fork", False),
                "private": repo_data.get("private", False),
                "homepage": repo_data.get("homepage"),
                "size": repo_data.get("size"),
                "watchers_count": repo_data.get("watchers_count"),
                "network_count": repo_data.get("network_count"),
                "subscribers_count": repo_data.get("subscribers_count"),
            }

            return metadata

        except requests.RequestException as e:
            return Exception(f"GitHub API request failed: {e}")
        except Exception as e:
            return Exception(f"Failed to get GitHub metadata: {e}")

    def _calculate_commit_frequency(
        self, commits_data: List[Dict[str, Any]]
    ) -> CommitFrequency:
        """Calculate commit frequency from recent commits."""
        if not commits_data or len(commits_data) < 2:
            return CommitFrequency.MONTHLY

        # Get commit dates
        commit_dates = []
        for commit in commits_data:
            if "commit" in commit and "author" in commit["commit"]:
                date_str = commit["commit"]["author"]["date"]
                commit_dates.append(date_str)

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
