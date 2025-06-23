# metagit/providers/base.py
from abc import ABC, abstractmethod
from typing import Optional, List
from metagit.core.config.models import Metrics, PullRequests, Maintainer

class GitProvider(ABC):
    """
    Abstract base class for Git hosting providers.
    """
    @abstractmethod
    def get_metrics(self, repo_url: str) -> Optional[Metrics]:
        """Fetch repository metrics like stars, forks, and open issues."""
        pass

    @abstractmethod
    def get_pull_requests(self, repo_url: str) -> Optional[List[PullRequests]]:
        """Fetch information about pull requests."""
        pass

    @abstractmethod
    def get_contributors(self, repo_url: str) -> Optional[List[Maintainer]]:
        """Fetch repository contributors."""
        pass

    @staticmethod
    @abstractmethod
    def matches_url(repo_url: str) -> bool:
        """Check if this provider can handle the given repository URL."""
        pass