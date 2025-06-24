#!/usr/bin/env python
"""
Provider registry for Git hosting platforms.
"""

import logging
import os
from typing import Optional

from metagit.core.providers.base import GitProvider
from metagit.core.providers.github import GitHubProvider
from metagit.core.providers.gitlab import GitLabProvider
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for git provider plugins."""

    def __init__(self):
        self._providers: list[GitProvider] = []
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
        normalized_url = normalize_git_url(url)

        for provider in self._providers:
            if provider.can_handle_url(normalized_url) and provider.is_available():
                return provider

        return None

    def get_all_providers(self) -> list[GitProvider]:
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
                gitlab_provider = GitLabProvider(
                    api_token=app_config.providers.gitlab.api_token,
                    base_url=app_config.providers.gitlab.base_url,
                )
                self.register(gitlab_provider)
            except ImportError:
                pass  # GitLab provider not available

    def configure_from_environment(self) -> None:
        """Configure providers from environment variables (legacy method)."""
        # GitHub provider
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            try:
                github_provider = GitHubProvider(api_token=github_token)
                self.register(github_provider)
            except ImportError:
                pass

        # GitLab provider
        gitlab_token = os.getenv("GITLAB_TOKEN")
        if gitlab_token:
            try:
                gitlab_provider = GitLabProvider(api_token=gitlab_token)
                self.register(gitlab_provider)
            except ImportError:
                pass


# Global registry instance
registry = ProviderRegistry()

# Export the registry for backward compatibility
__all__ = ["GitProvider", "ProviderRegistry", "registry"]
