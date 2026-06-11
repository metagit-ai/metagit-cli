#!/usr/bin/env python
"""
Tests for source sync input model validation.
"""

import pytest
from pydantic import ValidationError

from metagit.core.project.source_models import (
    SourceProvider,
    SourceSpec,
    SourceSyncPlan,
    SourceSyncResult,
)


def test_source_spec_accepts_github_org() -> None:
    spec = SourceSpec(provider=SourceProvider.GITHUB, org="metagit-ai")
    assert spec.namespace_key == "metagit-ai"


def test_source_spec_rejects_invalid_github_scope() -> None:
    with pytest.raises(ValueError):
        SourceSpec(provider=SourceProvider.GITHUB, org="metagit-ai", user="zach")


def test_source_spec_accepts_gitlab_group() -> None:
    spec = SourceSpec(provider=SourceProvider.GITLAB, group="my-group/sub-group")
    assert spec.namespace_key == "my-group/sub-group"


def test_source_spec_accepts_filter_fields() -> None:
    spec = SourceSpec(
        provider=SourceProvider.GITHUB,
        org="acme",
        include_patterns=["acme/platform-*"],
        ignore_patterns=["**/deprecated/**"],
        visibility="private",
        name_strategy="namespaced",
        ensure=True,
        refresh_metadata=False,
        enrich_topics=True,
    )
    assert spec.ensure is True
    assert spec.name_strategy == "namespaced"


def test_source_spec_visibility_invalid_raises() -> None:
    with pytest.raises(ValidationError):
        SourceSpec(provider=SourceProvider.GITHUB, org="acme", visibility="secret")


def test_source_sync_result_defaults() -> None:
    result = SourceSyncResult(
        plan=SourceSyncPlan(discovered_count=1, filtered_count=1),
    )
    assert result.ok is True
    assert result.applied is False
    assert result.errors == []
