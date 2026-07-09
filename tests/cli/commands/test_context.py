#!/usr/bin/env python
"""CLI tests for metagit context pack and repo-card."""

import json
import os
from pathlib import Path

from click.testing import CliRunner
from git import Repo

from metagit.cli.main import cli


def _env_workspace_root(root: Path) -> dict[str, str]:
    workspace = str(root.resolve())
    return {**os.environ, "METAGIT_WORKSPACE_PATH": workspace}


def test_context_pack_tier_zero_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=False)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["context", "pack", "--tier", "0", "--json"],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert '"tier": 0' in result.output
    assert '"workspace_name": "ctx-cli"' in result.output


def test_context_pack_tier_one_human_summary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "context",
            "pack",
            "--tier",
            "1",
            "--project",
            "demo",
            "--repo",
            "svc",
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "tier: 1" in result.output
    assert "cards: 1 repo card(s)" in result.output
    assert "demo/svc:" in result.output


def test_context_repo_card_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "context",
            "repo-card",
            "--project",
            "demo",
            "--repo",
            "svc",
            "--json",
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert '"tier": 1' in result.output
    assert '"repo_name": "svc"' in result.output


def test_context_repo_card_unknown_repo_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "context",
            "repo-card",
            "--project",
            "demo",
            "--repo",
            "nope",
            "--json",
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code != 0


def test_context_objective_list_after_set(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=False)
    runner = CliRunner()
    env = _env_workspace_root(tmp_path)
    r1 = runner.invoke(
        cli,
        ["context", "objective", "set", "--id", "g1", "--title", "Goal one"],
        env=env,
        catch_exceptions=False,
    )
    assert r1.exit_code == 0
    r2 = runner.invoke(
        cli,
        ["context", "objective", "list"],
        env=env,
        catch_exceptions=False,
    )
    assert r2.exit_code == 0
    assert "g1" in r2.output
    assert "[pending]" in r2.output


def test_context_pack_tier_two_json_contains_digest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)
    runner = CliRunner()
    env = _env_workspace_root(tmp_path)
    assert (
        runner.invoke(
            cli,
            [
                "context",
                "objective",
                "set",
                "--id",
                "active-q",
                "--title",
                "Q",
                "--status",
                "in_progress",
            ],
            env=env,
            catch_exceptions=False,
        ).exit_code
        == 0
    )
    result = runner.invoke(
        cli,
        ["context", "pack", "--tier", "2", "--project", "demo", "--repo", "svc", "--json"],
        env=env,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert '"tier": 2' in result.output
    assert '"digest"' in result.output
    assert '"active_objective_id": "active-q"' in result.output


def test_context_objective_partial_update_without_title(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=False)
    runner = CliRunner()
    env = _env_workspace_root(tmp_path)
    create = runner.invoke(
        cli,
        [
            "context",
            "objective",
            "set",
            "--id",
            "keep-repos",
            "--title",
            "Initial",
            "--repo",
            "demo/svc",
        ],
        env=env,
        catch_exceptions=False,
    )
    assert create.exit_code == 0
    update = runner.invoke(
        cli,
        ["context", "objective", "set", "--id", "keep-repos", "--status", "in_progress"],
        env=env,
        catch_exceptions=False,
    )
    assert update.exit_code == 0
    assert "demo/svc" in update.output
    assert "Initial" in update.output


def test_context_approval_request_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=False)
    runner = CliRunner()
    env = _env_workspace_root(tmp_path)
    result = runner.invoke(
        cli,
        [
            "context",
            "approval",
            "request",
            "--action",
            "repo_sync",
            "--requested-by",
            "hermes",
            "--payload",
            '{"project":"demo","repo":"svc"}',
        ],
        env=env,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert '"status": "pending"' in result.output
    assert '"action": "repo_sync"' in result.output


def test_context_session_begin_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)
    runner = CliRunner()
    env = _env_workspace_root(tmp_path)
    result = runner.invoke(
        cli,
        ["context", "session", "begin", "--json"],
        env=env,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["workspace_name"] == "ctx-cli"
    assert payload["pack"]["tier"] == 2


def test_context_session_begin_missing_workspace_definition_exit_code(tmp_path: Path) -> None:
    runner = CliRunner()
    missing = tmp_path / "missing.metagit.yml"
    result = runner.invoke(
        cli,
        [
            "context",
            "session",
            "begin",
            "--json",
            "--definition",
            str(missing),
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 10


def test_context_pack_max_tokens_reports_drops(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["context", "pack", "--tier", "2", "--json", "--max-tokens", "1"],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["max_tokens"] == 1
    assert len(payload["dropped_sections"]) >= 1


def test_context_approval_request_idempotency_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=False)
    runner = CliRunner()
    env = _env_workspace_root(tmp_path)
    for _ in range(2):
        result = runner.invoke(
            cli,
            [
                "context",
                "approval",
                "request",
                "--action",
                "repo_sync",
                "--requested-by",
                "hermes",
                "--idempotency-key",
                "idem-1",
                "--payload",
                '{"project":"demo","repo":"svc"}',
            ],
            env=env,
            catch_exceptions=False,
        )
        assert result.exit_code == 0

    listed = runner.invoke(
        cli,
        ["context", "approval", "list", "--json", "--status", "pending"],
        env=env,
        catch_exceptions=False,
    )
    assert listed.exit_code == 0
    payload = json.loads(listed.output)
    assert len(payload["requests"]) == 1
    assert payload["requests"][0]["idempotency_key"] == "idem-1"


def test_context_objective_export_import_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=False)
    runner = CliRunner()
    env = _env_workspace_root(tmp_path)

    create = runner.invoke(
        cli,
        ["context", "objective", "set", "--id", "exp-1", "--title", "Export me"],
        env=env,
        catch_exceptions=False,
    )
    assert create.exit_code == 0

    out_file = tmp_path / "objectives.json"
    exported = runner.invoke(
        cli,
        ["context", "objective", "export", "--output", str(out_file)],
        env=env,
        catch_exceptions=False,
    )
    assert exported.exit_code == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["objectives"][0]["id"] == "exp-1"

    cleared = runner.invoke(
        cli,
        ["context", "objective", "import", "--input", str(out_file)],
        env=env,
        catch_exceptions=False,
    )
    assert cleared.exit_code == 0
    summary = json.loads(cleared.output)
    assert summary["ok"] is True
    assert summary["imported"] >= 1


def test_context_compile_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "context",
            "compile",
            "--project",
            "demo",
            "--repo",
            "svc",
            "--tier",
            "1",
            "--budget",
            "20000",
            "--profile",
            "bugfix-local",
            "--json",
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["inputs"]["project"] == "demo"
    assert payload["inputs"]["repo"] == "svc"
    assert Path(payload["artifact_path"]).is_file()
    assert "bugfix-local" in (payload.get("suggested_repomix_command") or "")


def _write_workspace(root: Path, *, with_git_repo: bool) -> None:
    (root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: ctx-cli",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    svc = root / "demo" / "svc"
    svc.mkdir(parents=True)
    if with_git_repo:
        Repo.init(svc)
        (svc / "README.md").write_text("# svc\n", encoding="utf-8")
