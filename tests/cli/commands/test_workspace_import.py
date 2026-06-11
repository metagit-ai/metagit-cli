#!/usr/bin/env python
"""
CLI tests for workspace import alias.
"""

from click.testing import CliRunner

from metagit.cli.main import cli


def test_workspace_import_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["workspace", "import", "--help"])
    assert result.exit_code == 0
    assert "--provider" in result.output
    assert "--project" in result.output


def test_workspace_import_invokes_source_sync(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(
        """
name: test-project
workspace:
  projects:
    - name: platform
      repos: []
""".strip()
    )

    calls: list[dict] = []

    def _fake_run_source_sync(**kwargs):
        calls.append(kwargs)
        request = kwargs["request"]
        from metagit.core.project.source_models import SourceSyncResult, SourceSyncPlan

        return SourceSyncResult(
            ok=True,
            applied=True,
            plan=SourceSyncPlan(discovered_count=0, filtered_count=0),
        )

    monkeypatch.setattr(
        "metagit.cli.commands.project_source.run_source_sync",
        _fake_run_source_sync,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "workspace",
            "--config",
            str(config_path),
            "import",
            "--project",
            "platform",
            "--provider",
            "github",
            "--org",
            "acme",
            "--no-sync",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert len(calls) == 1
    request = calls[0]["request"]
    assert request.project_name == "platform"
    assert request.spec.org == "acme"
    assert request.spec.ensure is True
    assert request.mode.value == "additive"
    assert request.apply is True
