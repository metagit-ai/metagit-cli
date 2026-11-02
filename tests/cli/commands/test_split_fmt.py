#!/usr/bin/env python
"""config split output is already acceptable to fmt --check."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli
from tests.core.config.test_raw_flatten import FIDELITY


def test_split_then_fmt_check_is_clean(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(FIDELITY, encoding="utf-8")
    before = yaml.safe_load(FIDELITY)
    runner = CliRunner()
    split = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "split", "--by", "all"],
    )
    assert split.exit_code == 0, split.output
    check = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "fmt", "-t", "metagit", "--metagit-path", str(manifest), "--check"],
    )
    assert check.exit_code == 0, check.output
    from metagit.manifest import load_composed

    composed = load_composed(manifest)
    composed.pop("includes", None)
    assert composed["graph"]["relationships"][0]["from_endpoint"]["project"] == "billing"
    assert composed["workspace"]["projects"][0]["tags"]["team"] == "pay"
    assert before["name"] == composed["name"]
