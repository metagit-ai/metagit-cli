#!/usr/bin/env python
"""
Tests for source discovery filter pipeline.
"""

from metagit.core.project.source_filters import apply_source_filters
from metagit.core.project.source_models import DiscoveredRepo, SourceProvider, SourceSpec


def _repo(
    full_name: str,
    *,
    archived: bool = False,
    fork: bool = False,
    private: bool | None = None,
    language: str | None = None,
) -> DiscoveredRepo:
    return DiscoveredRepo(
        provider=SourceProvider.GITLAB,
        namespace="acme",
        full_name=full_name,
        name=full_name.split("/")[-1],
        clone_url=f"https://example.com/{full_name}.git",
        archived=archived,
        fork=fork,
        private=private,
        language=language,
    )


def test_ignore_pattern_drops_match() -> None:
    spec = SourceSpec(
        provider=SourceProvider.GITLAB,
        group="acme",
        ignore_patterns=["**/deprecated/**"],
    )
    repos = [_repo("acme/good"), _repo("acme/deprecated/old")]
    filtered = apply_source_filters(spec, repos)
    assert [item.full_name for item in filtered] == ["acme/good"]


def test_include_pattern_allowlist() -> None:
    spec = SourceSpec(
        provider=SourceProvider.GITHUB,
        org="acme",
        include_patterns=["acme/platform-*"],
    )
    repos = [_repo("acme/platform-api"), _repo("acme/other")]
    filtered = apply_source_filters(spec, repos)
    assert len(filtered) == 1
    assert filtered[0].full_name == "acme/platform-api"


def test_visibility_private_filter() -> None:
    spec = SourceSpec(
        provider=SourceProvider.GITHUB,
        org="acme",
        visibility="private",
    )
    repos = [_repo("acme/private", private=True), _repo("acme/public", private=False)]
    filtered = apply_source_filters(spec, repos)
    assert len(filtered) == 1
    assert filtered[0].full_name == "acme/private"


def test_ignore_language_filter() -> None:
    spec = SourceSpec(
        provider=SourceProvider.GITHUB,
        org="acme",
        ignore_languages=["Go"],
    )
    repos = [_repo("acme/py", language="Python"), _repo("acme/go", language="go")]
    filtered = apply_source_filters(spec, repos)
    assert [item.full_name for item in filtered] == ["acme/py"]
