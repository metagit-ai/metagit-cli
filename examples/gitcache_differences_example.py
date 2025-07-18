#!/usr/bin/env python
"""
Example demonstrating git cache differences functionality.

This example shows how the GitCacheManager now checks for differences
between local and remote repositories before pulling updates, and
includes detailed difference information in cache entries.
"""

import tempfile
from pathlib import Path

from metagit.core.gitcache import GitCacheConfig, GitCacheManager


def create_test_git_repo(path: Path) -> None:
    """Create a test git repository with some commits."""
    import os
    import subprocess

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=path, check=True)

    # Create initial file
    (path / "README.md").write_text("# Test Repository\n\nThis is a test repository.")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True)

    # Create another file
    (path / "main.py").write_text("print('Hello, World!')")
    subprocess.run(["git", "add", "main.py"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "Add main.py"], cwd=path, check=True)


def main():
    """Demonstrate git cache differences functionality."""
    print("=== Git Cache Differences Example ===\n")

    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        cache_root = temp_path / "cache"

        # Create configuration
        config = GitCacheConfig(
            cache_root=cache_root, default_timeout_minutes=30, max_cache_size_gb=1.0
        )

        # Create manager
        manager = GitCacheManager(config)

        # Create a test git repository
        test_repo_path = temp_path / "test_repo"
        test_repo_path.mkdir()
        create_test_git_repo(test_repo_path)

        print("1. Caching a local git repository...")
        entry = manager.cache_repository(str(test_repo_path), name="test-repo")

        if isinstance(entry, Exception):
            print(f"   Error: {entry}")
            return
        else:
            print(f"   Successfully cached: {entry.name}")
            print(f"   Cache path: {entry.cache_path}")
            print(
                f"   Local commit: {entry.local_commit_hash[:8] if entry.local_commit_hash else 'None'}"
            )
            print(f"   Local branch: {entry.local_branch}")
            print(f"   Has upstream changes: {entry.has_upstream_changes}")

        print("\n2. Getting detailed cache entry information...")
        details = manager.get_cache_entry_details("test-repo")

        if isinstance(details, Exception):
            print(f"   Error: {details}")
        else:
            print("   Cache Entry Details:")
            for key, value in details.items():
                if key not in ["metadata"]:  # Skip metadata for cleaner output
                    print(f"     {key}: {value}")

        print("\n3. Simulating upstream changes...")
        # Add a new commit to the original repository
        (test_repo_path / "new_file.txt").write_text(
            "This is a new file added after caching."
        )
        import subprocess

        subprocess.run(["git", "add", "new_file.txt"], cwd=test_repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file after caching"],
            cwd=test_repo_path,
            check=True,
        )

        print("   Added new commit to original repository")

        print("\n4. Re-caching to check for differences...")
        entry = manager.cache_repository(str(test_repo_path), name="test-repo")

        if isinstance(entry, Exception):
            print(f"   Error: {entry}")
        else:
            print(f"   Successfully updated: {entry.name}")
            print(
                f"   Local commit: {entry.local_commit_hash[:8] if entry.local_commit_hash else 'None'}"
            )
            print(
                f"   Remote commit: {entry.remote_commit_hash[:8] if entry.remote_commit_hash else 'None'}"
            )
            print(f"   Has upstream changes: {entry.has_upstream_changes}")
            print(f"   Changes summary: {entry.upstream_changes_summary}")

        print("\n5. Getting updated cache entry details...")
        details = manager.get_cache_entry_details("test-repo")

        if isinstance(details, Exception):
            print(f"   Error: {details}")
        else:
            print("   Updated Cache Entry Details:")
            for key, value in details.items():
                if key not in ["metadata"]:  # Skip metadata for cleaner output
                    print(f"     {key}: {value}")

        print("\n6. Listing all cache entries...")
        entries = manager.list_cache_entries()
        for entry in entries:
            print(f"   - {entry.name}: {entry.cache_type} ({entry.status})")
            if entry.cache_type == "git":
                print(
                    f"     Local: {entry.local_commit_hash[:8] if entry.local_commit_hash else 'None'}"
                )
                print(
                    f"     Remote: {entry.remote_commit_hash[:8] if entry.remote_commit_hash else 'None'}"
                )
                print(f"     Changes: {entry.has_upstream_changes}")

        print("\n7. Cache statistics...")
        stats = manager.get_cache_stats()
        print(f"   Total entries: {stats['total_entries']}")
        print(f"   Git entries: {stats['git_entries']}")
        print(f"   Local entries: {stats['local_entries']}")
        print(f"   Total size: {stats['total_size_gb']:.2f} GB")


if __name__ == "__main__":
    main()
