#!/usr/bin/env python
"""CLI tests for metagit atlas (RFC-0014)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.atlas.paths import capabilities_file, semantic_to_evidence_file
from metagit.core.atlas.serialize import dump_yaml

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "atlas" / "python_toy"

_REFUND_CAPABILITY = {
  "apiVersion": "atlas.metagit.dev/v1alpha1",
  "kind": "Capability",
  "metadata": {
    "id": "capability:refund.issue",
    "name": "Issue refund",
    "lifecycle": "active",
    "classification": "internal",
    "provenance": {"source": "curated"},
  },
  "spec": {"purpose": "Issue a refund for an order"},
}

_REFUND_MAPPING = {
  "mappings": [
    {
      "semantic": "capability:refund.issue",
      "relation": "maps_to",
      "evidence": [
        "evidence:symbol:src/toy/refunds.py#RefundService.issue",
      ],
    },
  ],
}


def _copy_toy_into(root: Path) -> None:
  shutil.copytree(FIXTURE, root, dirs_exist_ok=True)


def _seed_capability_and_mapping(root: Path) -> None:
  capabilities_file(root).write_text(
    dump_yaml({"entities": [_REFUND_CAPABILITY]}),
    encoding="utf-8",
  )
  semantic_to_evidence_file(root).write_text(
    dump_yaml(_REFUND_MAPPING),
    encoding="utf-8",
  )


def test_atlas_cli_mvp_json_flow() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem() as tmp:
    root = Path(tmp)
    _copy_toy_into(root)

    init = runner.invoke(
      cli,
      ["atlas", "init", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert init.exit_code == 0, init.output
    init_payload = json.loads(init.output)
    assert init_payload["ok"] is True

    generate = runner.invoke(
      cli,
      ["atlas", "generate", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert generate.exit_code == 0, generate.output
    assert json.loads(generate.output)["ok"] is True

    _seed_capability_and_mapping(root)

    validate = runner.invoke(
      cli,
      ["atlas", "validate", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert validate.exit_code == 0, validate.output
    validate_payload = json.loads(validate.output)
    assert validate_payload["ok"] is True

    status = runner.invoke(
      cli,
      ["atlas", "status", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert status.exit_code == 0, status.output
    status_payload = json.loads(status.output)
    assert status_payload["ok"] is True
    assert status_payload["initialized"] is True
    assert status_payload["generated"] is True

    query = runner.invoke(
      cli,
      [
        "atlas",
        "query",
        'Capability[id="capability:refund.issue"]',
        "--path",
        ".",
        "--json",
      ],
      catch_exceptions=False,
    )
    assert query.exit_code == 0, query.output
    query_payload = json.loads(query.output)
    assert query_payload["ok"] is True
    entity = query_payload["entity"]
    assert entity is not None
    metadata = entity.get("metadata") if isinstance(entity, dict) else None
    entity_id = metadata.get("id") if isinstance(metadata, dict) else entity.get("id")
    assert entity_id == "capability:refund.issue"

    refresh = runner.invoke(
      cli,
      ["atlas", "refresh", "src/toy/refunds.py", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert refresh.exit_code == 0, refresh.output
    refresh_payload = json.loads(refresh.output)
    assert refresh_payload["ok"] is True
    assert "src/toy/refunds.py" in (refresh_payload.get("invalidation_reason") or "")


def test_atlas_validate_dangling_ref_exits_nonzero() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem() as tmp:
    root = Path(tmp)
    _copy_toy_into(root)

    init = runner.invoke(
      cli,
      ["atlas", "init", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert init.exit_code == 0, init.output

    generate = runner.invoke(
      cli,
      ["atlas", "generate", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert generate.exit_code == 0, generate.output

    dangling_capability = {
      **_REFUND_CAPABILITY,
      "spec": {"invariants": ["invariant:missing"]},
    }
    capabilities_file(root).write_text(
      dump_yaml({"entities": [dangling_capability]}),
      encoding="utf-8",
    )

    validate_json = runner.invoke(
      cli,
      ["atlas", "validate", "--path", ".", "--json"],
      catch_exceptions=False,
    )
    assert validate_json.exit_code == 1, validate_json.output
    validate_payload = json.loads(validate_json.output)
    assert validate_payload["ok"] is False
    assert any(issue.get("code") == "dangling_ref" for issue in validate_payload["issues"])

    validate_human = runner.invoke(
      cli,
      ["atlas", "validate", "--path", "."],
      catch_exceptions=False,
    )
    assert validate_human.exit_code == 1, validate_human.output
    assert "validation failed" in validate_human.output
