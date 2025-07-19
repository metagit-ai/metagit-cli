#!/usr/bin/env python
"""
CLI commands for git cache management.

This module provides command-line interface for managing git cache operations.
"""

import asyncio
from pathlib import Path
from typing import Optional

import click

from metagit.core.gitcache import GitCacheConfig, GitCacheManager


@click.group()
def gitcache():
    """Git cache management commands."""
    pass


@gitcache.command()
@click.argument("source")
@click.option("--name", "-n", help="Custom cache name")
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
@click.option("--timeout", "-t", default=60, help="Cache timeout in minutes")
@click.option("--max-size", "-s", default=10.0, help="Maximum cache size in GB")
@click.option("--async", "use_async", is_flag=True, help="Use async operations")
def cache(
    source: str,
    name: Optional[str],
    cache_root: str,
    timeout: int,
    max_size: float,
    use_async: bool,
):
    """Cache a repository or local directory."""
    try:
        config = GitCacheConfig(
            cache_root=Path(cache_root),
            default_timeout_minutes=timeout,
            max_cache_size_gb=max_size,
            enable_async=use_async,
        )

        manager = GitCacheManager(config)

        if use_async:
            entry = asyncio.run(manager.cache_repository_async(source, name))
        else:
            entry = manager.cache_repository(source, name)

        if isinstance(entry, Exception):
            click.echo(f"Error: {entry}", err=True)
            return

        click.echo(f"Successfully cached: {entry.name}")
        click.echo(f"Cache path: {entry.cache_path}")
        click.echo(f"Cache type: {entry.cache_type}")
        click.echo(f"Status: {entry.status}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@gitcache.command()
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
def list(cache_root: str):
    """List all cache entries."""
    try:
        config = GitCacheConfig(cache_root=Path(cache_root))
        manager = GitCacheManager(config)

        entries = manager.list_cache_entries()

        if not entries:
            click.echo("No cache entries found.")
            return

        click.echo("Cache entries:")
        for entry in entries:
            click.echo(f"  - {entry.name}: {entry.cache_type} ({entry.status})")
            click.echo(f"    Source: {entry.source_url}")
            click.echo(f"    Path: {entry.cache_path}")
            if entry.size_bytes:
                click.echo(f"    Size: {entry.size_bytes / (1024 * 1024):.2f} MB")

            # Show git information for git repositories
            if entry.cache_type == "git":
                if entry.local_commit_hash:
                    click.echo(f"    Local: {entry.local_commit_hash[:8]}...")
                if entry.remote_commit_hash:
                    click.echo(f"    Remote: {entry.remote_commit_hash[:8]}...")
                if entry.has_upstream_changes:
                    click.echo(
                        f"    ⚠️  Has upstream changes: {entry.upstream_changes_summary}"
                    )

            click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@gitcache.command()
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
def stats(cache_root: str):
    """Show cache statistics."""
    try:
        config = GitCacheConfig(cache_root=Path(cache_root))
        manager = GitCacheManager(config)

        stats = manager.get_cache_stats()

        click.echo("Cache Statistics:")
        click.echo(f"  Total entries: {stats['total_entries']}")
        click.echo(f"  Git entries: {stats['git_entries']}")
        click.echo(f"  Local entries: {stats['local_entries']}")
        click.echo(f"  Fresh entries: {stats['fresh_entries']}")
        click.echo(f"  Stale entries: {stats['stale_entries']}")
        click.echo(f"  Missing entries: {stats['missing_entries']}")
        click.echo(f"  Error entries: {stats['error_entries']}")
        click.echo(f"  Total size: {stats['total_size_gb']:.2f} GB")
        click.echo(f"  Max size: {stats['max_size_gb']:.2f} GB")
        click.echo(f"  Cache full: {stats['cache_full']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@gitcache.command()
@click.argument("name")
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
@click.option("--async", "use_async", is_flag=True, help="Use async operations")
def refresh(name: str, cache_root: str, use_async: bool):
    """Refresh a cache entry."""
    try:
        config = GitCacheConfig(cache_root=Path(cache_root))
        manager = GitCacheManager(config)

        if use_async:
            entry = asyncio.run(manager.refresh_cache_entry_async(name))
        else:
            entry = manager.refresh_cache_entry(name)

        if isinstance(entry, Exception):
            click.echo(f"Error: {entry}", err=True)
            return

        click.echo(f"Successfully refreshed: {entry.name}")
        click.echo(f"Last updated: {entry.last_updated}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@gitcache.command()
@click.argument("name")
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
def remove(name: str, cache_root: str):
    """Remove a cache entry."""
    try:
        config = GitCacheConfig(cache_root=Path(cache_root))
        manager = GitCacheManager(config)

        result = manager.remove_cache_entry(name)

        if isinstance(result, Exception):
            click.echo(f"Error: {result}", err=True)
            return

        click.echo(f"Successfully removed cache entry: {name}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@gitcache.command()
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def clear(cache_root: str, yes: bool):
    """Clear all cache entries."""
    try:
        if not yes:
            if not click.confirm("Are you sure you want to clear all cache entries?"):
                return

        config = GitCacheConfig(cache_root=Path(cache_root))
        manager = GitCacheManager(config)

        result = manager.clear_cache()

        if isinstance(result, Exception):
            click.echo(f"Error: {result}", err=True)
            return

        click.echo("Successfully cleared all cache entries")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@gitcache.command()
@click.argument("name")
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
def path(name: str, cache_root: str):
    """Get the path to a cached repository."""
    try:
        config = GitCacheConfig(cache_root=Path(cache_root))
        manager = GitCacheManager(config)

        cache_path = manager.get_cached_repository(name)

        if isinstance(cache_path, Exception):
            click.echo(f"Error: {cache_path}", err=True)
            return

        click.echo(f"Cache path: {cache_path}")

        if cache_path.exists():
            click.echo(f"Directory exists: {cache_path.exists()}")
            contents = list(cache_path.iterdir())
            click.echo(f"Contents: {[item.name for item in contents]}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@gitcache.command()
@click.argument("name")
@click.option(
    "--cache-root", "-c", default="./.metagit/.cache", help="Cache root directory"
)
def details(name: str, cache_root: str):
    """Get detailed information about a cache entry."""
    try:
        config = GitCacheConfig(cache_root=Path(cache_root))
        manager = GitCacheManager(config)

        details = manager.get_cache_entry_details(name)

        if isinstance(details, Exception):
            click.echo(f"Error: {details}", err=True)
            return

        click.echo(f"Cache Entry Details for '{name}':")
        click.echo("=" * 50)

        # Basic information
        click.echo(f"Name: {details['name']}")
        click.echo(f"Source URL: {details['source_url']}")
        click.echo(f"Cache Type: {details['cache_type']}")
        click.echo(f"Cache Path: {details['cache_path']}")
        click.echo(f"Status: {details['status']}")
        click.echo(f"Exists: {details['exists']}")
        click.echo(f"Is Stale: {details['is_stale']}")

        if details["error_message"]:
            click.echo(f"Error: {details['error_message']}")

        # Size information
        if details["size_bytes"]:
            click.echo(f"Size: {details['size_mb']} MB ({details['size_bytes']} bytes)")

        # Timestamps
        click.echo(f"Created: {details['created_at']}")
        click.echo(f"Last Updated: {details['last_updated']}")
        click.echo(f"Last Accessed: {details['last_accessed']}")

        # Git-specific information
        if details["cache_type"] == "git":
            click.echo("\nGit Information:")
            click.echo("-" * 20)

            if details.get("local_commit_hash"):
                click.echo(f"Local Commit: {details['local_commit_hash'][:8]}...")
            if details.get("local_branch"):
                click.echo(f"Local Branch: {details['local_branch']}")
            if details.get("remote_commit_hash"):
                click.echo(f"Remote Commit: {details['remote_commit_hash'][:8]}...")
            if details.get("remote_branch"):
                click.echo(f"Remote Branch: {details['remote_branch']}")

            click.echo(
                f"Has Upstream Changes: {details.get('has_upstream_changes', False)}"
            )

            if details.get("upstream_changes_summary"):
                click.echo(f"Changes Summary: {details['upstream_changes_summary']}")

            if details.get("last_diff_check"):
                click.echo(f"Last Diff Check: {details['last_diff_check']}")

            # Current information (if different from stored)
            if "current_local_commit_hash" in details:
                click.echo("\nCurrent Git Information:")
                click.echo("-" * 25)
                click.echo(
                    f"Current Local Commit: {details['current_local_commit_hash'][:8]}..."
                )
                click.echo(f"Current Local Branch: {details['current_local_branch']}")
                click.echo(
                    f"Current Remote Commit: {details['current_remote_commit_hash'][:8]}..."
                )
                click.echo(f"Current Remote Branch: {details['current_remote_branch']}")
                click.echo(
                    f"Current Has Changes: {details['current_has_upstream_changes']}"
                )
                click.echo(
                    f"Current Changes Summary: {details['current_upstream_changes_summary']}"
                )
                click.echo(f"Diff Check Time: {details['diff_check_timestamp']}")

            if "diff_check_error" in details:
                click.echo(f"Diff Check Error: {details['diff_check_error']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
