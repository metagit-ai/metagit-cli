#!/usr/bin/env python
"""Repository identity, resolution, and materialization."""

from metagit.core.repo.identity import github_identity, identity_from_git_url, parse_repository_ref
from metagit.core.repo.models import RepositoryNode

__all__ = [
    "github_identity",
    "identity_from_git_url",
    "parse_repository_ref",
    "RepositoryNode",
]
