#!/usr/bin/env python
"""
Git cache manager for handling repository caching operations.

This module provides both synchronous and asynchronous operations
for caching git repositories and local directories.
"""

import asyncio
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import git  # Add this at the top with other imports

from metagit.core.gitcache.config import (
    CacheStatus,
    CacheType,
    GitCacheConfig,
    GitCacheEntry,
)
from metagit.core.providers.base import GitProvider
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class GitCacheManager:
    """Manager for git cache operations."""

    def __init__(self, config: GitCacheConfig):
        """
        Initialize the git cache manager.

        Args:
            config: Git cache configuration
        """
        self.config = config
        self._providers: Dict[str, GitProvider] = {}

    def register_provider(self, provider: GitProvider) -> None:
        """
        Register a git provider for handling specific URLs.

        Args:
            provider: Git provider instance
        """
        self._providers[provider.get_name()] = provider
        logger.info(f"Registered git provider: {provider.get_name()}")

    def _get_provider_for_url(self, url: str) -> Optional[GitProvider]:
        """
        Get the appropriate provider for a given URL.

        Args:
            url: Repository URL

        Returns:
            Git provider or None if no provider supports the URL
        """
        normalized_url = normalize_git_url(url)
        for provider in self._providers.values():
            if provider.can_handle_url(normalized_url):
                return provider
        return None

    def _generate_cache_name(self, source: str) -> str:
        """
        Generate a cache name from source URL or path.

        Args:
            source: Source URL or local path

        Returns:
            Generated cache name
        """
        # For git URLs, extract repo name
        if source.startswith(("http://", "https://", "git://", "ssh://")):
            normalized_url = normalize_git_url(source)
            # Extract repo name from URL
            if "/" in normalized_url:
                repo_name = normalized_url.split("/")[-1]
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]
                return repo_name
            return normalized_url.replace("/", "_").replace(":", "_")

        # For local paths, use the directory name
        path = Path(source)
        return path.name if path.name else path.stem

    def _is_git_url(self, source: str) -> bool:
        """
        Check if source is a git URL.

        Args:
            source: Source URL or path

        Returns:
            True if source is a git URL
        """
        return source.startswith(("http://", "https://", "git://", "ssh://"))

    def _is_local_path(self, source: str) -> bool:
        """
        Check if source is a local path.

        Args:
            source: Source URL or path

        Returns:
            True if source is a local path
        """
        path = Path(source)
        return path.exists() and path.is_dir()

    def _is_git_repository(self, path: Path) -> bool:
        """
        Check if a local path is a git repository using gitpython.

        Args:
            path: Local path to check

        Returns:
            True if path is a git repository
        """
        try:
            _ = git.Repo(path)
            return True
        except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
            return False
        except Exception:
            return False

    def _is_local_git_repository(self, source: str) -> bool:
        """
        Check if source is a local git repository.

        Args:
            source: Source URL or path

        Returns:
            True if source is a local git repository
        """
        path = Path(source)
        return path.exists() and path.is_dir() and self._is_git_repository(path)

    def _clone_repository(self, url: str, cache_path: Path) -> Union[bool, Exception]:
        """
        Clone a git repository using gitpython.

        Args:
            url: Repository URL
            cache_path: Local cache path

        Returns:
            True if successful, Exception if failed
        """
        try:
            # Remove existing directory if it exists
            if cache_path.exists():
                shutil.rmtree(cache_path)
            cache_path.mkdir(parents=True, exist_ok=True)
            git.Repo.clone_from(url, str(cache_path), depth=1)
            logger.info(f"Successfully cloned repository: {url}")
            return True
        except Exception as e:
            return Exception(f"Git clone error: {str(e)}")

    async def _clone_repository_async(
        self, url: str, cache_path: Path
    ) -> Union[bool, Exception]:
        """
        Clone a git repository asynchronously using gitpython in a thread.

        Args:
            url: Repository URL
            cache_path: Local cache path

        Returns:
            True if successful, Exception if failed
        """
        import asyncio

        try:
            result = await asyncio.to_thread(self._clone_repository, url, cache_path)
            return result
        except Exception as e:
            return Exception(f"Git clone error (async): {str(e)}")

    def _copy_local_directory(
        self, source_path: Path, cache_path: Path
    ) -> Union[bool, Exception]:
        """
        Copy a local directory to cache.

        Args:
            source_path: Source directory path
            cache_path: Local cache path

        Returns:
            True if successful, Exception if failed
        """
        try:
            # Remove existing directory if it exists
            if cache_path.exists():
                shutil.rmtree(cache_path)

            # Copy directory
            shutil.copytree(source_path, cache_path)

            logger.info(f"Successfully copied local directory: {source_path}")
            return True

        except Exception as e:
            return Exception(f"Directory copy error: {str(e)}")

    async def _copy_local_directory_async(
        self, source_path: Path, cache_path: Path
    ) -> Union[bool, Exception]:
        """
        Copy a local directory to cache asynchronously.

        Args:
            source_path: Source directory path
            cache_path: Local cache path

        Returns:
            True if successful, Exception if failed
        """
        try:
            # Run copy operation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._copy_local_directory, source_path, cache_path
            )
            return result

        except Exception as e:
            return Exception(f"Directory copy error: {str(e)}")

    def _pull_updates(self, cache_path: Path) -> Union[bool, Exception]:
        """
        Pull updates for an existing git repository using gitpython.

        Args:
            cache_path: Local cache path

        Returns:
            True if successful, Exception if failed
        """
        try:
            repo = git.Repo(cache_path)
            origin = repo.remotes.origin
            origin.pull()
            logger.info(f"Successfully pulled updates for: {cache_path}")
            return True
        except Exception as e:
            return Exception(f"Git pull error: {str(e)}")

    async def _pull_updates_async(self, cache_path: Path) -> Union[bool, Exception]:
        """
        Pull updates for an existing git repository asynchronously using gitpython in a thread.

        Args:
            cache_path: Local cache path

        Returns:
            True if successful, Exception if failed
        """
        import asyncio

        try:
            result = await asyncio.to_thread(self._pull_updates, cache_path)
            return result
        except Exception as e:
            return Exception(f"Git pull error (async): {str(e)}")

    def _calculate_directory_size(self, path: Path) -> int:
        """
        Calculate directory size in bytes.

        Args:
            path: Directory path

        Returns:
            Size in bytes
        """
        total_size = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, PermissionError):
            pass
        return total_size

    def cache_repository(
        self, source: str, name: Optional[str] = None
    ) -> Union[GitCacheEntry, Exception]:
        """
        Cache a repository or local directory synchronously.

        Args:
            source: Source URL or local path
            name: Optional cache name (auto-generated if not provided)

        Returns:
            GitCacheEntry if successful, Exception if failed
        """
        try:
            # Generate cache name if not provided
            if name is None:
                name = self._generate_cache_name(source)

            # Check if entry already exists
            existing_entry = self.config.get_entry(name)
            cache_path = self.config.get_cache_path(name)

            # Determine cache type
            if self._is_git_url(source):
                cache_type = CacheType.GIT
            elif self._is_local_git_repository(source):
                cache_type = CacheType.LOCAL
            else:
                return Exception(
                    f"Invalid source: {source} - must be a git URL or local git repository"
                )

            # Handle existing cache
            if existing_entry and cache_path.exists():
                if cache_type == CacheType.GIT:
                    # Pull updates for git repositories
                    result = self._pull_updates(cache_path)
                    if isinstance(result, Exception):
                        existing_entry.status = CacheStatus.ERROR
                        existing_entry.error_message = str(result)
                        return result
                else:
                    # For local directories, recopy
                    result = self._copy_local_directory(Path(source), cache_path)
                    if isinstance(result, Exception):
                        existing_entry.status = CacheStatus.ERROR
                        existing_entry.error_message = str(result)
                        return result

                # Update entry
                existing_entry.last_updated = datetime.now()
                existing_entry.last_accessed = datetime.now()
                existing_entry.status = CacheStatus.FRESH
                existing_entry.size_bytes = self._calculate_directory_size(cache_path)
                existing_entry.error_message = None

                return existing_entry

            # Create new cache entry
            entry = GitCacheEntry(
                name=name,
                source_url=source,
                cache_type=cache_type,
                cache_path=cache_path,
                created_at=datetime.now(),
                last_updated=datetime.now(),
                last_accessed=datetime.now(),
                status=CacheStatus.FRESH,
            )

            # Perform caching operation
            if cache_type == CacheType.GIT:
                result = self._clone_repository(source, cache_path)
            else:
                result = self._copy_local_directory(Path(source), cache_path)

            if isinstance(result, Exception):
                entry.status = CacheStatus.ERROR
                entry.error_message = str(result)
                self.config.add_entry(entry)
                return result

            # Calculate size and add entry
            entry.size_bytes = self._calculate_directory_size(cache_path)
            self.config.add_entry(entry)

            logger.info(f"Successfully cached: {source} -> {cache_path}")
            return entry

        except Exception as e:
            return Exception(f"Cache operation failed: {str(e)}")

    async def cache_repository_async(
        self, source: str, name: Optional[str] = None
    ) -> Union[GitCacheEntry, Exception]:
        """
        Cache a repository or local directory asynchronously.

        Args:
            source: Source URL or local path
            name: Optional cache name (auto-generated if not provided)

        Returns:
            GitCacheEntry if successful, Exception if failed
        """
        try:
            # Generate cache name if not provided
            if name is None:
                name = self._generate_cache_name(source)

            # Check if entry already exists
            existing_entry = self.config.get_entry(name)
            cache_path = self.config.get_cache_path(name)

            # Determine cache type
            if self._is_git_url(source):
                cache_type = CacheType.GIT
            elif self._is_local_git_repository(source):
                cache_type = CacheType.LOCAL
            else:
                return Exception(
                    f"Invalid source: {source} - must be a git URL or local git repository"
                )

            # Handle existing cache
            if existing_entry and cache_path.exists():
                if cache_type == CacheType.GIT:
                    # Pull updates for git repositories
                    result = await self._pull_updates_async(cache_path)
                    if isinstance(result, Exception):
                        existing_entry.status = CacheStatus.ERROR
                        existing_entry.error_message = str(result)
                        return result
                else:
                    # For local directories, recopy
                    result = await self._copy_local_directory_async(
                        Path(source), cache_path
                    )
                    if isinstance(result, Exception):
                        existing_entry.status = CacheStatus.ERROR
                        existing_entry.error_message = str(result)
                        return result

                # Update entry
                existing_entry.last_updated = datetime.now()
                existing_entry.last_accessed = datetime.now()
                existing_entry.status = CacheStatus.FRESH
                existing_entry.size_bytes = self._calculate_directory_size(cache_path)
                existing_entry.error_message = None

                return existing_entry

            # Create new cache entry
            entry = GitCacheEntry(
                name=name,
                source_url=source,
                cache_type=cache_type,
                cache_path=cache_path,
                created_at=datetime.now(),
                last_updated=datetime.now(),
                last_accessed=datetime.now(),
                status=CacheStatus.FRESH,
            )

            # Perform caching operation
            if cache_type == CacheType.GIT:
                result = await self._clone_repository_async(source, cache_path)
            else:
                result = await self._copy_local_directory_async(
                    Path(source), cache_path
                )

            if isinstance(result, Exception):
                entry.status = CacheStatus.ERROR
                entry.error_message = str(result)
                self.config.add_entry(entry)
                return result

            # Calculate size and add entry
            entry.size_bytes = self._calculate_directory_size(cache_path)
            self.config.add_entry(entry)

            logger.info(f"Successfully cached: {source} -> {cache_path}")
            return entry

        except Exception as e:
            return Exception(f"Cache operation failed: {str(e)}")

    def get_cached_repository(self, name: str) -> Union[Path, Exception]:
        """
        Get the path to a cached repository.

        Args:
            name: Cache entry name

        Returns:
            Path to cached repository or Exception if not found
        """
        entry = self.config.get_entry(name)
        if entry is None:
            return Exception(f"Cache entry not found: {name}")

        if not entry.cache_path.exists():
            entry.status = CacheStatus.MISSING
            return Exception(f"Cache path does not exist: {entry.cache_path}")

        # Update last accessed time
        entry.last_accessed = datetime.now()

        # Check if cache is stale
        if self.config.is_entry_stale(entry):
            entry.status = CacheStatus.STALE

        return entry.cache_path

    def list_cache_entries(self) -> List[GitCacheEntry]:
        """
        List all cache entries.

        Returns:
            List of cache entries
        """
        entries = self.config.list_entries()

        # Update status for each entry
        for entry in entries:
            if not entry.cache_path.exists():
                entry.status = CacheStatus.MISSING
            elif self.config.is_entry_stale(entry):
                entry.status = CacheStatus.STALE
            else:
                entry.status = CacheStatus.FRESH

        return entries

    def remove_cache_entry(self, name: str) -> Union[bool, Exception]:
        """
        Remove a cache entry and its files.

        Args:
            name: Cache entry name

        Returns:
            True if successful, Exception if failed
        """
        try:
            entry = self.config.get_entry(name)
            if entry is None:
                return Exception(f"Cache entry not found: {name}")

            # Remove cache directory
            if entry.cache_path.exists():
                shutil.rmtree(entry.cache_path)

            # Remove entry from config
            self.config.remove_entry(name)

            logger.info(f"Successfully removed cache entry: {name}")
            return True

        except Exception as e:
            return Exception(f"Failed to remove cache entry: {str(e)}")

    def refresh_cache_entry(self, name: str) -> Union[GitCacheEntry, Exception]:
        """
        Refresh a cache entry by re-caching the source.

        Args:
            name: Cache entry name

        Returns:
            Updated GitCacheEntry or Exception if failed
        """
        entry = self.config.get_entry(name)
        if entry is None:
            return Exception(f"Cache entry not found: {name}")

        # Re-cache the source
        return self.cache_repository(entry.source_url, name)

    async def refresh_cache_entry_async(
        self, name: str
    ) -> Union[GitCacheEntry, Exception]:
        """
        Refresh a cache entry by re-caching the source asynchronously.

        Args:
            name: Cache entry name

        Returns:
            Updated GitCacheEntry or Exception if failed
        """
        entry = self.config.get_entry(name)
        if entry is None:
            return Exception(f"Cache entry not found: {name}")

        # Re-cache the source
        return await self.cache_repository_async(entry.source_url, name)

    def clear_cache(self) -> Union[bool, Exception]:
        """
        Clear all cache entries and files.

        Returns:
            True if successful, Exception if failed
        """
        try:
            entries = self.config.list_entries()

            for entry in entries:
                if entry.cache_path.exists():
                    shutil.rmtree(entry.cache_path)

            self.config.clear_entries()

            logger.info("Successfully cleared all cache entries")
            return True

        except Exception as e:
            return Exception(f"Failed to clear cache: {str(e)}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        entries = self.config.list_entries()

        total_entries = len(entries)
        git_entries = sum(1 for e in entries if e.cache_type == CacheType.GIT)
        local_entries = sum(1 for e in entries if e.cache_type == CacheType.LOCAL)

        fresh_entries = sum(1 for e in entries if e.status == CacheStatus.FRESH)
        stale_entries = sum(1 for e in entries if e.status == CacheStatus.STALE)
        missing_entries = sum(1 for e in entries if e.status == CacheStatus.MISSING)
        error_entries = sum(1 for e in entries if e.status == CacheStatus.ERROR)

        total_size_bytes = self.config.get_cache_size_bytes()
        total_size_gb = self.config.get_cache_size_gb()

        return {
            "total_entries": total_entries,
            "git_entries": git_entries,
            "local_entries": local_entries,
            "fresh_entries": fresh_entries,
            "stale_entries": stale_entries,
            "missing_entries": missing_entries,
            "error_entries": error_entries,
            "total_size_bytes": total_size_bytes,
            "total_size_gb": total_size_gb,
            "max_size_gb": self.config.max_cache_size_gb,
            "cache_full": self.config.is_cache_full(),
        }
