# metagit/providers/github.py
import os
from typing import Optional, List
from github import Github
from metagit.core.config.models import Metrics, PullRequests, Maintainer
from .base import GitProvider

class GitHubProvider(GitProvider):
    """GitHub provider implementation."""
    
    def __init__(self):
        self.api_key = os.getenv("GITHUB_TOKEN")
        if not self.api_key:
            # Handle missing API key, maybe with reduced functionality
            self.github = Github()
        else:
            self.github = Github(self.api_key)

    def get_metrics(self, repo_url: str) -> Optional[Metrics]:
        # Implementation to get metrics from GitHub API
        pass

    def get_pull_requests(self, repo_url: str) -> Optional[List[PullRequests]]:
        # Implementation to get pull requests from GitHub API
        pass

    def get_contributors(self, repo_url: str) -> Optional[List[Maintainer]]:
        # Implementation to get contributors from GitHub API
        pass

    @staticmethod
    def matches_url(repo_url: str) -> bool:
        return "github.com" in repo_url.lower()
