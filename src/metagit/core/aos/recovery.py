#!/usr/bin/env python
"""AOS recovery recipe builders (RFC-0019)."""

from __future__ import annotations

from metagit.core.aos.models import AosFinding, AosRecoveryRecipe, AosSubsystemSection


def build_recovery_recipes(
    findings: list[AosFinding],
    *,
    agent_id: str | None = None,
) -> list[AosRecoveryRecipe]:
    """Map doctor findings to structured recovery recipes."""
    agent = agent_id or "<agent-id>"
    recipes: list[AosRecoveryRecipe] = []
    codes = {item.code for item in findings}

    if "stale_lease" in codes:
        recipes.append(
            AosRecoveryRecipe(
                code="stale_lease",
                action="expire_leases",
                description="Expire stale leases via list side effect",
                command=f"metagit lease list --agent-id {agent} --json",
                safe_default=True,
                subsystem="acl",
            )
        )
    if "orphan_worktree_risk" in codes or "stale_lease" in codes:
        recipes.append(
            AosRecoveryRecipe(
                code="orphan_worktree_risk",
                action="gc_worktrees",
                description="Garbage-collect orphan worktrees",
                command="metagit worktree gc",
                safe_default=True,
                subsystem="acl",
            )
        )
    if codes & {"stale_lease", "orphan_worktree_risk", "stuck_running_task", "orphan_claim"}:
        recipes.append(
            AosRecoveryRecipe(
                code="recover_bundle",
                action="recover_agent",
                description="Safe agent-scoped recover (GC + stuck task reset)",
                command=f"metagit aos recover --agent-id {agent} --yes",
                safe_default=True,
                subsystem="aos",
            )
        )
    if "orphan_claim" in codes:
        recipes.append(
            AosRecoveryRecipe(
                code="orphan_claim",
                action="release_orphan_claims",
                description="Release orphan claims (explicit flag required)",
                command=f"metagit aos recover --agent-id {agent} --yes --release-orphan-claims",
                safe_default=False,
                requires_flag="release_orphan_claims",
                subsystem="acl",
            )
        )
    if "stale_merge_running" in codes or "merge_pressure" in codes:
        recipes.append(
            AosRecoveryRecipe(
                code="stale_merge_running",
                action="cancel_stale_merge",
                description="Cancel stale merges (explicit flag required)",
                command=f"metagit aos recover --agent-id {agent} --yes --cancel-stale-merges",
                safe_default=False,
                requires_flag="cancel_stale_merges",
                subsystem="merge",
            )
        )
    if "stuck_running_task" in codes:
        recipes.append(
            AosRecoveryRecipe(
                code="stuck_running_task",
                action="reset_stuck_task",
                description="Reset stuck running tasks to ready via aos recover",
                command=f"metagit aos recover --agent-id {agent} --yes",
                safe_default=True,
                subsystem="taskgraph",
            )
        )
    return recipes


def enrich_findings(subsystems: dict[str, AosSubsystemSection]) -> list[AosFinding]:
    """Extra findings beyond the baseline AosService._analyze set."""
    findings: list[AosFinding] = []
    acl = subsystems.get("acl")
    if acl and acl.available:
        orphan_claims = int(acl.summary.get("claims_orphan") or 0)
        if orphan_claims > 0:
            findings.append(
                AosFinding(
                    severity="warning",
                    code="orphan_claim",
                    message=f"{orphan_claims} orphan claim(s) without active lease",
                    subsystem="acl",
                )
            )
    task = subsystems.get("taskgraph")
    if task and task.available:
        stuck = int(task.summary.get("running") or 0)
        # Without lease cross-join, treat long-running count as sticky signal when
        # leases_expired also present; collector may later add stuck_running.
        stuck_explicit = int(task.summary.get("stuck_running") or 0)
        if stuck_explicit > 0 or (stuck > 0 and int((acl.summary.get("leases_expired") if acl else 0) or 0) > 0):
            count = stuck_explicit or stuck
            findings.append(
                AosFinding(
                    severity="warning",
                    code="stuck_running_task",
                    message=f"{count} running task node(s) may be stuck",
                    subsystem="taskgraph",
                )
            )
    merge = subsystems.get("merge")
    if merge and merge.available:
        stale_running = int(merge.summary.get("stale_running") or 0)
        if stale_running > 0:
            findings.append(
                AosFinding(
                    severity="warning",
                    code="stale_merge_running",
                    message=f"{stale_running} stale running merge(s)",
                    subsystem="merge",
                )
            )
    return findings


__all__ = ["build_recovery_recipes", "enrich_findings"]
