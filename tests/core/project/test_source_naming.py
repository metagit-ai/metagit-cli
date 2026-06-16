#!/usr/bin/env python
"""
Tests for manifest naming strategies during source sync.
"""

from metagit.core.project.source_models import DiscoveredRepo, SourceProvider
from metagit.core.project.source_naming import resolve_manifest_names


def _repo(full_name: str, name: str, clone_url: str) -> DiscoveredRepo:
    return DiscoveredRepo(
        provider=SourceProvider.GITLAB,
        namespace="acme",
        full_name=full_name,
        name=name,
        clone_url=clone_url,
    )


def test_namespaced_collision_uses_parent_segment() -> None:
    repos = [
        _repo("acme/a/foo", "foo", "u1"),
        _repo("acme/b/foo", "foo", "u2"),
    ]
    names = resolve_manifest_names(repos, strategy="namespaced")
    assert names["u1"] == "foo"
    assert names["u2"] == "b-foo"


def test_short_strategy_uses_repo_name() -> None:
    repos = [_repo("o/r", "r", "u")]
    assert resolve_manifest_names(repos, strategy="short")["u"] == "r"
