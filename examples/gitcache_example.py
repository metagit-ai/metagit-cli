#!/usr/bin/env python
"""
Example script demonstrating the git cache management system.

This script shows how to use the GitCacheManager to cache both
git repositories and local directories with both sync and async operations.
"""

import asyncio
import tempfile
from pathlib import Path

from metagit.core.gitcache import GitCacheConfig, GitCacheManager


def create_sample_local_directory() -> Path:
    """Create a sample local directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create some sample files
    (temp_dir / "README.md").write_text(
        "# Sample Project\n\nThis is a sample project for testing."
    )
    (temp_dir / "main.py").write_text('print("Hello, World!")')
    (temp_dir / "config.json").write_text('{"name": "sample", "version": "1.0.0"}')

    # Create a subdirectory
    subdir = temp_dir / "src"
    subdir.mkdir()
    (subdir / "utils.py").write_text('def helper_function():\n    return "helper"')

    return temp_dir


def sync_example():
    """Demonstrate synchronous git cache operations."""
    print("=== Synchronous Git Cache Example ===\n")

    # Create configuration
    config = GitCacheConfig(
        cache_root=Path("./.metagit/.cache"),
        default_timeout_minutes=30,
        max_cache_size_gb=5.0,
    )

    # Create manager
    manager = GitCacheManager(config)

    # Example 1: Cache a git repository
    print("1. Caching a git repository...")
    try:
        entry = manager.cache_repository("https://github.com/octocat/Hello-World.git")
        if isinstance(entry, Exception):
            print(f"   Error: {entry}")
        else:
            print(f"   Successfully cached: {entry.name}")
            print(f"   Cache path: {entry.cache_path}")
            print(f"   Cache type: {entry.cache_type}")
            print(f"   Status: {entry.status}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 2: Cache a local directory
    print("2. Caching a local directory...")
    try:
        sample_dir = create_sample_local_directory()
        entry = manager.cache_repository(str(sample_dir), name="sample-project")
        if isinstance(entry, Exception):
            print(f"   Error: {entry}")
        else:
            print(f"   Successfully cached: {entry.name}")
            print(f"   Cache path: {entry.cache_path}")
            print(f"   Cache type: {entry.cache_type}")
            print(f"   Status: {entry.status}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 3: List cache entries
    print("3. Listing cache entries...")
    entries = manager.list_cache_entries()
    for entry in entries:
        print(f"   - {entry.name}: {entry.cache_type} ({entry.status})")

    print()

    # Example 4: Get cache statistics
    print("4. Cache statistics...")
    stats = manager.get_cache_stats()
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Git entries: {stats['git_entries']}")
    print(f"   Local entries: {stats['local_entries']}")
    print(f"   Total size: {stats['total_size_gb']:.2f} GB")
    print(f"   Cache full: {stats['cache_full']}")

    print()

    # Example 5: Get cached repository path
    print("5. Getting cached repository path...")
    try:
        cache_path = manager.get_cached_repository("Hello-World")
        if isinstance(cache_path, Exception):
            print(f"   Error: {cache_path}")
        else:
            print(f"   Cache path: {cache_path}")
            if cache_path.exists():
                print(f"   Directory exists: {cache_path.exists()}")
                print(f"   Contents: {list(cache_path.iterdir())}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 6: Refresh cache entry
    print("6. Refreshing cache entry...")
    try:
        entry = manager.refresh_cache_entry("Hello-World")
        if isinstance(entry, Exception):
            print(f"   Error: {entry}")
        else:
            print(f"   Successfully refreshed: {entry.name}")
            print(f"   Last updated: {entry.last_updated}")
    except Exception as e:
        print(f"   Error: {e}")


async def async_example():
    """Demonstrate asynchronous git cache operations."""
    print("=== Asynchronous Git Cache Example ===\n")

    # Create configuration
    config = GitCacheConfig(
        cache_root=Path("./.metagit/.cache"),
        default_timeout_minutes=30,
        max_cache_size_gb=5.0,
        enable_async=True,
    )

    # Create manager
    manager = GitCacheManager(config)

    # Example 1: Cache multiple repositories concurrently
    print("1. Caching multiple repositories concurrently...")
    repositories = [
        "https://github.com/octocat/Hello-World.git",
        "https://github.com/octocat/Spoon-Knife.git",
    ]

    tasks = []
    for repo_url in repositories:
        task = manager.cache_repository_async(repo_url)
        tasks.append(task)

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   Error caching {repositories[i]}: {result}")
            else:
                print(f"   Successfully cached: {result.name}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 2: Cache local directories concurrently
    print("2. Caching local directories concurrently...")
    try:
        sample_dir1 = create_sample_local_directory()
        sample_dir2 = create_sample_local_directory()

        # Add some unique content to distinguish them
        (sample_dir1 / "project.txt").write_text("Project 1")
        (sample_dir2 / "project.txt").write_text("Project 2")

        tasks = [
            manager.cache_repository_async(str(sample_dir1), name="project1"),
            manager.cache_repository_async(str(sample_dir2), name="project2"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   Error caching project{i+1}: {result}")
            else:
                print(f"   Successfully cached: {result.name}")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 3: Refresh multiple entries concurrently
    print("3. Refreshing multiple entries concurrently...")
    try:
        entries = manager.list_cache_entries()
        if entries:
            tasks = []
            for entry in entries[:2]:  # Refresh first 2 entries
                task = manager.refresh_cache_entry_async(entry.name)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"   Error refreshing {entries[i].name}: {result}")
                else:
                    print(f"   Successfully refreshed: {result.name}")
        else:
            print("   No entries to refresh")
    except Exception as e:
        print(f"   Error: {e}")


def cleanup_example():
    """Demonstrate cache cleanup operations."""
    print("=== Cache Cleanup Example ===\n")

    # Create configuration
    config = GitCacheConfig(
        cache_root=Path("./.metagit/.cache"),
        default_timeout_minutes=30,
        max_cache_size_gb=5.0,
    )

    # Create manager
    manager = GitCacheManager(config)

    # Example 1: Remove specific cache entry
    print("1. Removing specific cache entry...")
    try:
        result = manager.remove_cache_entry("Hello-World")
        if isinstance(result, Exception):
            print(f"   Error: {result}")
        else:
            print("   Successfully removed cache entry")
    except Exception as e:
        print(f"   Error: {e}")

    print()

    # Example 2: Clear all cache
    print("2. Clearing all cache...")
    try:
        result = manager.clear_cache()
        if isinstance(result, Exception):
            print(f"   Error: {result}")
        else:
            print("   Successfully cleared all cache")
    except Exception as e:
        print(f"   Error: {e}")


def main():
    """Run all examples."""
    print("Git Cache Management System Examples")
    print("=" * 50)
    print()

    # Run synchronous examples
    sync_example()

    print()
    print("=" * 50)
    print()

    # Run asynchronous examples
    asyncio.run(async_example())

    print()
    print("=" * 50)
    print()

    # Run cleanup examples
    cleanup_example()

    print()
    print("Examples completed!")


if __name__ == "__main__":
    main()
