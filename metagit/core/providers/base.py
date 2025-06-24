#!/usr/bin/env python
"""
Base provider for Git hosting platforms.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from metagit.core.config.models import Metrics
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class GitProvider(ABC):
    """Base class for git provider plugins."""

    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the git provider.

        Args:
            api_token: API token for authentication
            base_url: Base URL for the API (for self-hosted instances)
        """
        self.api_token = api_token
        self.base_url = base_url
        self._session = None

    @abstractmethod
    def get_name(self) -> str:
        """Get the provider name."""
        pass

    @abstractmethod
    def can_handle_url(self, url: str) -> bool:
        """Check if this provider can handle the given repository URL."""
        pass

    @abstractmethod
    def extract_repo_info(self, url: str) -> Dict[str, str]:
        """
        Extract repository information from URL.

        Returns:
            Dict with keys: owner, repo, api_url
        """
        pass

    @abstractmethod
    def get_repository_metrics(
        self, owner: str, repo: str
    ) -> Union[Metrics, Exception]:
        """
        Get repository metrics from the provider.

        Args:
            owner: Repository owner/organization
            repo: Repository name

        Returns:
            Metrics object or Exception
        """
        pass

    @abstractmethod
    def get_repository_metadata(
        self, owner: str, repo: str
    ) -> Union[Dict[str, Any], Exception]:
        """
        Get additional repository metadata.

        Args:
            owner: Repository owner/organization
            repo: Repository name

        Returns:
            Dict with metadata or Exception
        """
        pass

    def supports_url(self, url: str) -> bool:
        """Check if this provider supports the given URL."""
        normalized_url = normalize_git_url(url)
        return self.can_handle_url(normalized_url)

    def is_available(self) -> bool:
        """Check if the provider is available (has API token, etc.)."""
        return self.api_token is not None
