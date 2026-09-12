#!/usr/bin/env python
"""Tests for Git remote identity mapping used by campaign context."""

from metagit.core.integrations.everroom.source_identity import (
    canonical_git_identity,
    identities_match,
    identity_haystack,
)


def test_canonical_git_identity_https_and_ssh() -> None:
    assert canonical_git_identity("https://github.com/org/terraform-network.git") == "github.com/org/terraform-network"
    assert canonical_git_identity("git@github.com:org/terraform-network.git") == "github.com/org/terraform-network"


def test_canonical_git_identity_rejects_filesystem_paths() -> None:
    assert canonical_git_identity("/home/agent/src/terraform-network") is None
    assert canonical_git_identity("./terraform-network") is None
    assert canonical_git_identity("file:///tmp/terraform-network") is None
    assert canonical_git_identity("") is None
    assert canonical_git_identity(None) is None


def test_identities_match_requires_host_path() -> None:
    haystack = identity_haystack(["github.com/org/terraform-network", "terraform-network"])
    assert identities_match("github.com/org/terraform-network", haystack)
    assert not identities_match("terraform-network", haystack)
    assert not identities_match(None, haystack)
