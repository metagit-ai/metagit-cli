#!/usr/bin/env python
"""
Unit tests for git cache management system.

This module contains comprehensive tests for the GitCacheConfig,
GitCacheEntry, and GitCacheManager classes.
"""

import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from metagit.core.gitcache.config import (
    CacheStatus,
    CacheType,
    GitCacheConfig,
    GitCacheEntry,
)
from metagit.core.gitcache.manager import GitCacheManager


class TestGitCacheEntry(unittest.TestCase):
    """Test cases for GitCacheEntry model."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = Path(self.temp_dir) / "test_cache"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_git_cache_entry_creation(self):
        """Test creating a GitCacheEntry."""
        entry = GitCacheEntry(
            name="test-repo",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=self.cache_path,
        )

        self.assertEqual(entry.name, "test-repo")
        self.assertEqual(entry.source_url, "https://github.com/test/repo.git")
        self.assertEqual(entry.cache_type, CacheType.GIT)
        self.assertEqual(entry.cache_path, self.cache_path)
        self.assertEqual(entry.status, CacheStatus.FRESH)
        self.assertIsNone(entry.error_message)

    def test_git_cache_entry_with_string_path(self):
        """Test creating GitCacheEntry with string path."""
        entry = GitCacheEntry(
            name="test-repo",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=str(self.cache_path),
        )

        self.assertEqual(entry.cache_path, self.cache_path)

    def test_git_cache_entry_metadata(self):
        """Test GitCacheEntry with metadata."""
        metadata = {"branch": "main", "commit": "abc123"}
        entry = GitCacheEntry(
            name="test-repo",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=self.cache_path,
            metadata=metadata,
        )

        self.assertEqual(entry.metadata, metadata)


class TestGitCacheConfig(unittest.TestCase):
    """Test cases for GitCacheConfig model."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_git_cache_config_defaults(self):
        """Test GitCacheConfig with default values."""
        config = GitCacheConfig()

        self.assertEqual(config.cache_root, Path("./.metagit/.cache"))
        self.assertEqual(config.default_timeout_minutes, 60)
        self.assertEqual(config.max_cache_size_gb, 10.0)
        self.assertTrue(config.enable_async)
        self.assertEqual(config.entries, {})

    def test_git_cache_config_custom_values(self):
        """Test GitCacheConfig with custom values."""
        cache_root = Path(self.temp_dir) / "custom_cache"
        config = GitCacheConfig(
            cache_root=cache_root,
            default_timeout_minutes=120,
            max_cache_size_gb=5.0,
            enable_async=False,
        )

        self.assertEqual(config.cache_root, cache_root)
        self.assertEqual(config.default_timeout_minutes, 120)
        self.assertEqual(config.max_cache_size_gb, 5.0)
        self.assertFalse(config.enable_async)

    def test_git_cache_config_cache_root_creation(self):
        """Test that cache root directory is created."""
        cache_root = Path(self.temp_dir) / "new_cache"
        config = GitCacheConfig(cache_root=cache_root)

        self.assertTrue(cache_root.exists())
        self.assertTrue(cache_root.is_dir())

    def test_git_cache_config_validation(self):
        """Test GitCacheConfig validation."""
        with self.assertRaises(ValueError):
            GitCacheConfig(default_timeout_minutes=0)

        with self.assertRaises(ValueError):
            GitCacheConfig(max_cache_size_gb=0)

    def test_git_cache_config_get_cache_path(self):
        """Test getting cache path for entry."""
        config = GitCacheConfig(cache_root=Path(self.temp_dir))
        cache_path = config.get_cache_path("test-repo")

        self.assertEqual(cache_path, Path(self.temp_dir) / "test-repo")

    def test_git_cache_config_entry_management(self):
        """Test entry management methods."""
        config = GitCacheConfig()
        entry = GitCacheEntry(
            name="test-repo",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=Path("/tmp/test"),
        )

        # Test adding entry
        config.add_entry(entry)
        self.assertIn("test-repo", config.entries)
        self.assertEqual(config.entries["test-repo"], entry)

        # Test getting entry
        retrieved_entry = config.get_entry("test-repo")
        self.assertEqual(retrieved_entry, entry)

        # Test getting non-existent entry
        self.assertIsNone(config.get_entry("non-existent"))

        # Test listing entries
        entries = config.list_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        # Test removing entry
        self.assertTrue(config.remove_entry("test-repo"))
        self.assertNotIn("test-repo", config.entries)

        # Test removing non-existent entry
        self.assertFalse(config.remove_entry("non-existent"))

    def test_git_cache_config_stale_detection(self):
        """Test stale entry detection."""
        config = GitCacheConfig(default_timeout_minutes=60)

        # Fresh entry
        fresh_entry = GitCacheEntry(
            name="fresh",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=Path("/tmp/fresh"),
            last_updated=datetime.now(),
        )
        self.assertFalse(config.is_entry_stale(fresh_entry))

        # Stale entry
        stale_entry = GitCacheEntry(
            name="stale",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=Path("/tmp/stale"),
            last_updated=datetime.now() - timedelta(hours=2),
        )
        self.assertTrue(config.is_entry_stale(stale_entry))


class TestGitCacheManager(unittest.TestCase):
    """Test cases for GitCacheManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_root = Path(self.temp_dir) / "cache"
        self.config = GitCacheConfig(cache_root=self.cache_root)
        self.manager = GitCacheManager(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_git_cache_manager_initialization(self):
        """Test GitCacheManager initialization."""
        self.assertEqual(self.manager.config, self.config)
        self.assertEqual(self.manager._providers, {})

    def test_git_cache_manager_provider_registration(self):
        """Test provider registration."""
        mock_provider = MagicMock()
        mock_provider.get_name.return_value = "test-provider"

        self.manager.register_provider(mock_provider)

        self.assertIn("test-provider", self.manager._providers)
        self.assertEqual(self.manager._providers["test-provider"], mock_provider)

    def test_git_cache_manager_generate_cache_name(self):
        """Test cache name generation."""
        # Git URL
        git_url = "https://github.com/test/repo.git"
        name = self.manager._generate_cache_name(git_url)
        self.assertEqual(name, "repo")

        # Git URL without .git extension
        git_url_no_ext = "https://github.com/test/repo"
        name = self.manager._generate_cache_name(git_url_no_ext)
        self.assertEqual(name, "repo")

        # Local path
        local_path = "/path/to/directory"
        name = self.manager._generate_cache_name(local_path)
        self.assertEqual(name, "directory")

    def test_git_cache_manager_url_detection(self):
        """Test URL type detection."""
        # Git URLs
        self.assertTrue(self.manager._is_git_url("https://github.com/test/repo.git"))
        self.assertTrue(self.manager._is_git_url("http://github.com/test/repo.git"))
        self.assertTrue(self.manager._is_git_url("git://github.com/test/repo.git"))
        self.assertTrue(self.manager._is_git_url("ssh://git@github.com/test/repo.git"))

        # Non-git URLs
        self.assertFalse(self.manager._is_git_url("/path/to/directory"))
        self.assertFalse(self.manager._is_git_url("file:///path/to/directory"))

    def test_git_cache_manager_local_path_detection(self):
        """Test local path detection."""
        # Create a temporary directory
        temp_dir = Path(self.temp_dir) / "test_dir"
        temp_dir.mkdir()

        self.assertTrue(self.manager._is_local_path(str(temp_dir)))
        self.assertFalse(self.manager._is_local_path("/non/existent/path"))

    @patch("subprocess.run")
    def test_git_cache_manager_clone_repository(self, mock_run):
        """Test repository cloning."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        cache_path = Path(self.temp_dir) / "test_repo"
        result = self.manager._clone_repository(
            "https://github.com/test/repo.git", cache_path
        )

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_git_cache_manager_clone_repository_failure(self, mock_run):
        """Test repository cloning failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Authentication failed"

        cache_path = Path(self.temp_dir) / "test_repo"
        result = self.manager._clone_repository(
            "https://github.com/test/repo.git", cache_path
        )

        self.assertIsInstance(result, Exception)
        self.assertIn("Authentication failed", str(result))

    def test_git_cache_manager_copy_local_directory(self):
        """Test local directory copying."""
        # Create source directory with some files
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("test content")

        cache_path = Path(self.temp_dir) / "cache_copy"
        result = self.manager._copy_local_directory(source_dir, cache_path)

        self.assertTrue(result)
        self.assertTrue(cache_path.exists())
        self.assertTrue((cache_path / "test.txt").exists())
        self.assertEqual((cache_path / "test.txt").read_text(), "test content")

    def test_git_cache_manager_copy_local_directory_failure(self):
        """Test local directory copying failure."""
        non_existent_path = Path("/non/existent/path")
        cache_path = Path(self.temp_dir) / "cache_copy"
        result = self.manager._copy_local_directory(non_existent_path, cache_path)

        self.assertIsInstance(result, Exception)

    def test_git_cache_manager_calculate_directory_size(self):
        """Test directory size calculation."""
        # Create test directory with files
        test_dir = Path(self.temp_dir) / "size_test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        size = self.manager._calculate_directory_size(test_dir)
        self.assertGreater(size, 0)

    def test_git_cache_manager_cache_stats(self):
        """Test cache statistics."""
        # Add some test entries
        entry1 = GitCacheEntry(
            name="repo1",
            source_url="https://github.com/test/repo1.git",
            cache_type=CacheType.GIT,
            cache_path=Path("/tmp/repo1"),
        )
        entry2 = GitCacheEntry(
            name="repo2",
            source_url="/path/to/local/repo",
            cache_type=CacheType.LOCAL,
            cache_path=Path("/tmp/repo2"),
        )

        self.config.add_entry(entry1)
        self.config.add_entry(entry2)

        stats = self.manager.get_cache_stats()

        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["git_entries"], 1)
        self.assertEqual(stats["local_entries"], 1)
        self.assertEqual(stats["fresh_entries"], 2)

    def test_git_cache_manager_remove_cache_entry(self):
        """Test removing cache entry."""
        # Create a test cache directory
        cache_path = Path(self.temp_dir) / "test_cache"
        cache_path.mkdir()
        (cache_path / "test.txt").write_text("test")

        entry = GitCacheEntry(
            name="test-repo",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=cache_path,
        )
        self.config.add_entry(entry)

        result = self.manager.remove_cache_entry("test-repo")

        self.assertTrue(result)
        self.assertNotIn("test-repo", self.config.entries)
        self.assertFalse(cache_path.exists())

    def test_git_cache_manager_remove_nonexistent_entry(self):
        """Test removing non-existent cache entry."""
        result = self.manager.remove_cache_entry("non-existent")

        self.assertIsInstance(result, Exception)
        self.assertIn("not found", str(result))

    def test_git_cache_manager_rejects_non_git_directory(self):
        """Test that non-git directories cannot be cached as local repositories."""
        # Create a plain directory (not a git repo)
        non_git_dir = Path(self.temp_dir) / "plain_dir"
        non_git_dir.mkdir()
        (non_git_dir / "file.txt").write_text("not a repo")

        result = self.manager.cache_repository(str(non_git_dir))
        self.assertIsInstance(result, Exception)
        self.assertIn("must be a git URL or local git repository", str(result))

    def test_git_cache_manager_accepts_local_git_repository(self):
        """Test that a valid local git repository can be cached."""
        # Create a git repo
        git_dir = Path(self.temp_dir) / "git_repo"
        git_dir.mkdir()
        (git_dir / "file.txt").write_text("repo file")
        # Initialize git
        import subprocess

        subprocess.run(["git", "init"], cwd=git_dir, check=True)

        result = self.manager.cache_repository(str(git_dir))
        self.assertIsInstance(result, GitCacheEntry)
        self.assertEqual(result.cache_type, CacheType.LOCAL)
        self.assertEqual(result.source_url, str(git_dir))


class TestGitCacheManagerAsync(unittest.IsolatedAsyncioTestCase):
    """Test cases for GitCacheManager async operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_root = Path(self.temp_dir) / "cache"
        self.config = GitCacheConfig(cache_root=self.cache_root)
        self.manager = GitCacheManager(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("asyncio.create_subprocess_exec")
    async def test_git_cache_manager_clone_repository_async(
        self, mock_create_subprocess
    ):
        """Test async repository cloning."""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_create_subprocess.return_value = mock_process

        cache_path = Path(self.temp_dir) / "test_repo"
        result = await self.manager._clone_repository_async(
            "https://github.com/test/repo.git", cache_path
        )

        self.assertTrue(result)
        mock_create_subprocess.assert_called_once()

    @patch("asyncio.create_subprocess_exec")
    async def test_git_cache_manager_clone_repository_async_failure(
        self, mock_create_subprocess
    ):
        """Test async repository cloning failure."""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"Authentication failed")
        mock_process.returncode = 1
        mock_create_subprocess.return_value = mock_process

        cache_path = Path(self.temp_dir) / "test_repo"
        result = await self.manager._clone_repository_async(
            "https://github.com/test/repo.git", cache_path
        )

        self.assertIsInstance(result, Exception)
        self.assertIn("Authentication failed", str(result))

    async def test_git_cache_manager_copy_local_directory_async(self):
        """Test async local directory copying."""
        # Create source directory with some files
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("test content")

        cache_path = Path(self.temp_dir) / "cache_copy"
        result = await self.manager._copy_local_directory_async(source_dir, cache_path)

        self.assertTrue(result)
        self.assertTrue(cache_path.exists())
        self.assertTrue((cache_path / "test.txt").exists())

    async def test_git_cache_manager_copy_local_directory_async_failure(self):
        """Test async local directory copying failure."""
        non_existent_path = Path("/non/existent/path")
        cache_path = Path(self.temp_dir) / "cache_copy"
        result = await self.manager._copy_local_directory_async(
            non_existent_path, cache_path
        )

        self.assertIsInstance(result, Exception)

    @patch("metagit.core.gitcache.manager.GitCacheManager._clone_repository_async")
    async def test_git_cache_manager_cache_repository_async(self, mock_clone):
        """Test async repository caching."""
        mock_clone.return_value = True

        result = await self.manager.cache_repository_async(
            "https://github.com/test/repo.git"
        )

        self.assertIsInstance(result, GitCacheEntry)
        self.assertEqual(result.name, "repo")
        self.assertEqual(result.source_url, "https://github.com/test/repo.git")
        self.assertEqual(result.cache_type, CacheType.GIT)

    @patch("metagit.core.gitcache.manager.GitCacheManager._copy_local_directory_async")
    async def test_git_cache_manager_cache_local_directory_async(self, mock_copy):
        """Test async local directory caching."""
        mock_copy.return_value = True

        # Create a temporary directory
        temp_dir = Path(self.temp_dir) / "test_dir"
        temp_dir.mkdir()

        result = await self.manager.cache_repository_async(str(temp_dir))

        self.assertIsInstance(result, GitCacheEntry)
        self.assertEqual(result.cache_type, CacheType.LOCAL)

    @patch("metagit.core.gitcache.manager.GitCacheManager.cache_repository_async")
    async def test_git_cache_manager_refresh_cache_entry_async(self, mock_cache):
        """Test async cache entry refresh."""
        # Create test entry
        entry = GitCacheEntry(
            name="test-repo",
            source_url="https://github.com/test/repo.git",
            cache_type=CacheType.GIT,
            cache_path=Path("/tmp/test"),
        )
        self.config.add_entry(entry)

        mock_cache.return_value = entry

        result = await self.manager.refresh_cache_entry_async("test-repo")

        self.assertEqual(result, entry)
        mock_cache.assert_called_once_with(
            "https://github.com/test/repo.git", "test-repo"
        )


if __name__ == "__main__":
    unittest.main()
