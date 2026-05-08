#!/usr/bin/env python
"""
Tests for source sync input model validation.
"""

import pytest

from metagit.core.project.source_models import SourceProvider, SourceSpec


def test_source_spec_accepts_github_org() -> None:
    spec = SourceSpec(provider=SourceProvider.GITHUB, org="metagit-ai")
    assert spec.namespace_key == "metagit-ai"


def test_source_spec_rejects_invalid_github_scope() -> None:
    with pytest.raises(ValueError):
        SourceSpec(provider=SourceProvider.GITHUB, org="metagit-ai", user="zach")


def test_source_spec_accepts_gitlab_group() -> None:
    spec = SourceSpec(provider=SourceProvider.GITLAB, group="my-group/sub-group")
    assert spec.namespace_key == "my-group/sub-group"
