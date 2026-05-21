#!/usr/bin/env python
"""Tests for workspace graph web view builder."""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.web.graph_service import WorkspaceGraphService


def test_build_view_includes_manual_and_structure(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    (workspace_root / "alpha" / "api").mkdir(parents=True)

    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "from": {"project": "alpha", "repo": "api"},
                    "to": {"project": "beta", "repo": "lib"},
                    "type": "depends_on",
                    "label": "uses lib",
                }
            ]
        },
        workspace={
            "projects": [
                {
                    "name": "alpha",
                    "repos": [{"name": "api", "url": "https://example.com/a.git"}],
                },
                {
                    "name": "beta",
                    "repos": [{"name": "lib", "url": "https://example.com/b.git"}],
                },
            ]
        },
    )
    view = WorkspaceGraphService().build_view(
        config,
        str(workspace_root),
        include_inferred=False,
    )
    assert view.ok
    assert len(view.nodes) >= 4
    manual = [edge for edge in view.edges if edge.source == "manual"]
    assert len(manual) == 1
    assert manual[0].label == "uses lib"
    structure = [edge for edge in view.edges if edge.source == "structure"]
    assert len(structure) >= 1
