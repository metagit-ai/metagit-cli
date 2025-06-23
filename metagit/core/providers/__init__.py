#!/usr/bin/env python3
"""
Git provider plugins for repository analysis.

This package provides a plugin architecture for integrating with various
git hosting platforms like GitHub, GitLab, Bitbucket, etc.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from metagit.core.config.models import Metrics


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

    def is_available(self) -> bool:
        """Check if the provider is available (has API token, etc.)."""
        return self.api_token is not None


class ProviderRegistry:
    """Registry for git provider plugins."""

    def __init__(self):
        self._providers: List[GitProvider] = []
        self._app_config = None

    def register(self, provider: GitProvider) -> None:
        """Register a git provider plugin."""
        self._providers.append(provider)

    def unregister(self, provider_name: str) -> None:
        """Unregister a provider by name."""
        self._providers = [p for p in self._providers if p.get_name() != provider_name]

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()

    def get_provider_for_url(self, url: str) -> Optional[GitProvider]:
        """Get the appropriate provider for a given URL."""
        for provider in self._providers:
            if provider.can_handle_url(url) and provider.is_available():
                return provider
        return None

    def get_all_providers(self) -> List[GitProvider]:
        """Get all registered providers."""
        return self._providers.copy()

    def get_provider_by_name(self, name: str) -> Optional[GitProvider]:
        """Get a provider by name."""
        for provider in self._providers:
            if provider.get_name() == name:
                return provider
        return None

    def configure_from_app_config(self, app_config) -> None:
        """
        Configure providers from AppConfig settings.

        Args:
            app_config: AppConfig instance with provider settings
        """
        self._app_config = app_config

        # Clear existing providers
        self.clear()

        # Configure GitHub provider
        if (
            app_config.providers.github.enabled
            and app_config.providers.github.api_token
        ):
            try:
                from metagit.core.providers.github import GitHubProvider

                github_provider = GitHubProvider(
                    api_token=app_config.providers.github.api_token,
                    base_url=app_config.providers.github.base_url,
                )
                self.register(github_provider)
            except ImportError:
                pass  # GitHub provider not available

        # Configure GitLab provider
        if (
            app_config.providers.gitlab.enabled
            and app_config.providers.gitlab.api_token
        ):
            try:
                from metagit.core.providers.gitlab import GitLabProvider

                gitlab_provider = GitLabProvider(
                    api_token=app_config.providers.gitlab.api_token,
                    base_url=app_config.providers.gitlab.base_url,
                )
                self.register(gitlab_provider)
            except ImportError:
                pass  # GitLab provider not available

    def configure_from_environment(self) -> None:
        """Configure providers from environment variables (legacy method)."""
        import os

        # GitHub provider
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            try:
                from metagit.core.providers.github import GitHubProvider

                github_provider = GitHubProvider(api_token=github_token)
                self.register(github_provider)
            except ImportError:
                pass

        # GitLab provider
        gitlab_token = os.getenv("GITLAB_TOKEN")
        if gitlab_token:
            try:
                from metagit.core.providers.gitlab import GitLabProvider

                gitlab_provider = GitLabProvider(api_token=gitlab_token)
                self.register(gitlab_provider)
            except ImportError:
                pass


# Global registry instance
registry = ProviderRegistry()
