#!/usr/bin/env python
"""Tests for work item ref parsing."""

from metagit.core.workitem import ExternalWorkRef, parse_work_item_ref


def test_parse_provider_prefix() -> None:
    ref = parse_work_item_ref("azure_devops:12345")
    assert ref.provider == "azure_devops"
    assert ref.id == "12345"


def test_parse_ado_url() -> None:
    ref = parse_work_item_ref("https://dev.azure.com/contoso/platform/_workitems/edit/88")
    assert ref.provider == "azure_devops"
    assert ref.id == "88"
    assert ref.organization == "contoso"
    assert ref.project == "platform"


def test_parse_github_issue_url() -> None:
    ref = parse_work_item_ref("https://github.com/acme/api/issues/12")
    assert ref.provider == "github"
    assert ref.id == "12"
    assert ref.organization == "acme"
    assert ref.project == "api"


def test_package_exports_parse() -> None:
    ref = parse_work_item_ref("azure_devops:1")
    assert isinstance(ref, ExternalWorkRef)
    assert ref.id == "1"
