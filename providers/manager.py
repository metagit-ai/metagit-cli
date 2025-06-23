# metagit/providers/manager.py
from typing import Optional, Type
from .base import GitProvider
from .github import GitHubProvider
# Import other providers here as they are created

class ProviderManager:
    """Manages the discovery and selection of Git provider plugins."""
    
    def __init__(self):
        self.providers: List[Type[GitProvider]] = [
            GitHubProvider,
            # Add other provider classes here
        ]

    def get_provider(self, repo_url: str) -> Optional[GitProvider]:
        """
        Get the appropriate provider for a given repository URL.
        """
        for provider_class in self.providers:
            if provider_class.matches_url(repo_url):
                return provider_class()
        return None