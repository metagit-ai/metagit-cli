#!/usr/bin/env python
"""Repository identity, resolution, and materialization."""

from metagit.core.repo.identity import github_identity, identity_from_git_url, parse_repository_ref
from metagit.core.repo.materialize import RepoMaterializeService
from metagit.core.repo.models import RepositoryNode
from metagit.core.repo.neighborhood import GraphNeighborhoodService
from metagit.core.repo.resolver import RepositoryResolver

__all__ = [
    "github_identity",
    "identity_from_git_url",
    "parse_repository_ref",
    "RepoMaterializeService",
    "RepositoryNode",
    "GraphNeighborhoodService",
    "RepositoryResolver",
]
