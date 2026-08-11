#!/usr/bin/env python
"""CLI tests for routing route/run/lane commands."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _env(root: Path) -> dict[str, str]:
    return {**os.environ, "METAGIT_WORKSPACE_PATH": str(root.resolve())}


def _write_manifest(root: Path) -> None:
    (root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "routing:",
                "  catalog: knowledge/requests/entries",
                "  runs: knowledge/requests/runs",
                "  id_prefix: REQ",
                "  policy:",
                "    promote_after_clean: 5",
                "    demote_on:",
                "      - bounced",
                "      - noop",
                "    retain_success_days: 60",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_class(root: Path, class_id: str = "REQ-CERT") -> None:
    entry = root / "knowledge" / "requests" / "entries"
    entry.mkdir(parents=True, exist_ok=True)
    (entry / f"{class_id}.yml").write_text(
        "\n".join(
            [
                f"id: {class_id}",
                "title: Rotate certificate",
                "triggers:",
                "  - rotate certificate",
                "  - renew cert",
                "skill: cert-rotation",
                "lane: operations",
                "artifact: updated cert",
                "gates:",
                "  - ci",
                "tier: skilled",
                "mutates: false",
                "executor: cert.rotate",
                "promotion_state: stable",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_landed_runs(root: Path, class_id: str, count: int) -> None:
    runs_dir = root / "knowledge" / "requests" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(count):
        second = f"0{idx}" if idx < 10 else str(idx)
        run_id = f"RUN-20260810-1200{second}-{class_id}"
        opened = f"2026-08-10T12:00:{second}Z"
        (runs_dir / f"{run_id}.yml").write_text(
            "\n".join(
                [
                    f"id: {run_id}",
                    f"class: {class_id}",
                    "tier: skilled",
                    "lane: operations",
                    "actor: agent:test",
                    "dispatch: {}",
                    "outcome: landed",
                    "artifact: {}",
                    "evidence: {}",
                    f"opened: '{opened}'",
                    f"closed: '{opened}'",
                ]
            )
            + "\n",
            encoding="utf-8",
        )


def test_route_query_json_success() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_manifest(root)
        _write_class(root)

        result = runner.invoke(
            cli,
            ["route", "query", "rotate expired certificate", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["matches"][0]["id"] == "REQ-CERT"


def test_route_query_miss_non_zero() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_manifest(root)
        _write_class(root)

        result = runner.invoke(
            cli,
            ["route", "query", "refactor payment webhook retries"],
            env=_env(root),
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "catalog" in result.output.lower()


def test_run_open_close_list_happy_path() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_manifest(root)
        _write_class(root)

        opened = runner.invoke(
            cli,
            [
                "run",
                "open",
                "--class",
                "REQ-CERT",
                "--actor",
                "agent:test",
                "--session-id",
                "S-1",
                "--branch",
                "feat/cert-rotation",
                "--json",
            ],
            env=_env(root),
            catch_exceptions=False,
        )
        assert opened.exit_code == 0, opened.output
        open_payload = json.loads(opened.output)
        run_id = open_payload["id"]

        closed = runner.invoke(
            cli,
            [
                "run",
                "close",
                "--id",
                run_id,
                "--outcome",
                "landed",
                "--mr-url",
                "https://example.com/mr/1",
                "--gate",
                "ci",
                "--json",
            ],
            env=_env(root),
            catch_exceptions=False,
        )
        assert closed.exit_code == 0, closed.output
        closed_payload = json.loads(closed.output)
        assert closed_payload["outcome"] == "landed"

        listed = runner.invoke(
            cli,
            ["run", "list", "--class", "REQ-CERT", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert listed.exit_code == 0, listed.output
        list_payload = json.loads(listed.output)
        assert len(list_payload["runs"]) == 1
        assert list_payload["runs"][0]["id"] == run_id


def test_run_close_refuses_second_close() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_manifest(root)
        _write_class(root)

        opened = runner.invoke(
            cli,
            ["run", "open", "--class", "REQ-CERT", "--actor", "agent:test", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        run_id = json.loads(opened.output)["id"]

        first_close = runner.invoke(
            cli,
            ["run", "close", "--id", run_id, "--outcome", "landed"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert first_close.exit_code == 0, first_close.output

        second_close = runner.invoke(
            cli,
            ["run", "close", "--id", run_id, "--outcome", "bounced"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert second_close.exit_code != 0
        assert "already closed" in second_close.output


def test_lane_eval_updates_tier_and_promotion_state() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_manifest(root)
        _write_class(root)
        _write_landed_runs(root, class_id="REQ-CERT", count=5)

        evaluated = runner.invoke(
            cli,
            ["lane", "eval", "--id", "REQ-CERT", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert evaluated.exit_code == 0, evaluated.output
        payload = json.loads(evaluated.output)
        assert payload["updated"][0]["tier"] == "deterministic"
        assert payload["updated"][0]["promotion_state"] == "stable"
