#!/usr/bin/env python
"""Tests for RFC-0022 mutation policy MVP."""

from __future__ import annotations

import json

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.policy.engine import MutationPolicy, PolicyRule, evaluate_action


def test_agent_mode_denies_high_risk_by_default() -> None:
    decision = evaluate_action("merge_integrate", env={"METAGIT_AGENT_MODE": "true"})
    assert decision.effect == "deny"
    assert decision.agent_mode is True


def test_explicit_rule_allows_high_risk() -> None:
    policy = MutationPolicy(
        rules=[PolicyRule(action="merge_integrate", effect="allow", reason="ops approved")]
    )
    decision = evaluate_action(
        "merge_integrate",
        policy,
        env={"METAGIT_AGENT_MODE": "true"},
    )
    assert decision.effect == "allow"
    assert decision.matched_rule is True


def test_policy_eval_cli_json() -> None:
    runner = CliRunner(env={"METAGIT_AGENT_MODE": "true"})
    result = runner.invoke(cli, ["policy", "eval", "--action", "catalog_edit", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["action"] == "catalog_edit"
    assert payload["effect"] == "deny"
