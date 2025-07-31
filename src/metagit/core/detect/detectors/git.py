#!/usr/bin/env python3
"""
Git repository detection plugin.

This module provides functionality to detect Git repository information
including branch checksum, tags, last commit timestamp, origin branch count,
and local dirty status.
"""

from datetime import datetime
from typing import Optional
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

from metagit.core.detect.models import Detector, ProjectScanContext, DiscoveryResult


class GitDetector(Detector):
    """Git repository detection plugin."""

    name = "git"

    def should_run(self, ctx: ProjectScanContext) -> bool:
        """
        Determine if this detector should run on the given context.

        Args:
            ctx: Project scan context

        Returns:
            bool: True if the path is a Git repository
        """
        try:
            # Check if the path is a Git repository
            _ = Repo(str(ctx.root_path))
            return True
        except (InvalidGitRepositoryError, NoSuchPathError):
            return False

    def run(self, ctx: ProjectScanContext) -> Optional[DiscoveryResult]:
        """
        Run Git repository detection.

        Args:
            ctx: Project scan context

        Returns:
            DiscoveryResult with Git repository information
        """

        if not self.should_run(ctx):
            return None

        repo = Repo(str(ctx.root_path))

        # Get current branch
        try:
            current_branch = repo.active_branch.name
        except TypeError:
            # Handle detached HEAD state
            current_branch = "HEAD"

        # Get current branch checksum (commit hash)
        checksum = repo.head.commit.hexsha

        # Get last commit timestamp
        last_commit_timestamp = datetime.fromtimestamp(repo.head.commit.committed_date)

        # Get tags
        tags = [tag.name for tag in repo.tags]

        # Get remote branch count
        origin_branch_count = 0
        try:
            if repo.remotes:
                origin = repo.remotes.origin
                origin.fetch()
                origin_branch_count = len(list(origin.refs))
        except (AttributeError, IndexError):
            # No origin remote or no refs
            pass

        # Check for local dirty status
        is_dirty = repo.is_dirty()

        # Create structured data
        data = {
            "current_branch": current_branch,
            "checksum": checksum,
            "last_commit_timestamp": last_commit_timestamp.isoformat(),
            "tags": tags,
            "origin_branch_count": origin_branch_count,
            "is_dirty": is_dirty,
            "total_branches": len(repo.branches),
            "total_remotes": len(repo.remotes),
        }

        # Create tags for the discovery result
        discovery_tags = ["git", "vcs", "repository"]
        if is_dirty:
            discovery_tags.append("dirty")
        if tags:
            discovery_tags.append("tagged")

        return DiscoveryResult(
            name="Git Repository",
            description=f"Git repository on branch '{current_branch}'",
            tags=discovery_tags,
            confidence=1.0,
            data=data,
        )
