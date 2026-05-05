#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.upstream_hints
"""

from metagit.core.mcp.services.upstream_hints import UpstreamHintService


def test_terraform_blocker_ranks_infra_repos_higher() -> None:
    service = UpstreamHintService()
    repo_context = [
        {
            "project_name": "platform",
            "repo_name": "shared-terraform-modules",
            "repo_path": "/tmp/shared-terraform-modules",
            "exists": True,
            "sync": True,
        },
        {
            "project_name": "ui",
            "repo_name": "frontend-app",
            "repo_path": "/tmp/frontend-app",
            "exists": True,
            "sync": False,
        },
    ]

    ranked = service.rank(
        blocker="terraform variable enable_private_endpoint is missing in module",
        repo_context=repo_context,
    )

    assert ranked[0]["repo_name"] == "shared-terraform-modules"
    assert ranked[0]["score"] > ranked[1]["score"]
