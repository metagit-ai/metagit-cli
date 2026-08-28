---
name: agent-reliability-series
description: Navigate or extend RFC-0019+ agent reliability / AOS hardening work (recovery, discovery, scenarios, policy).
last_updated: 2026-08-27
---

# Agent Reliability Series

## When to use
Working on post-AOS agent reliability: failure recovery, discovery/health surfaces, multi-agent scenario tests, mutation policy, federation polish, plugins, or workspace indexing — or when tempted to number a new RFC as 0016–0018.

## Steps
1. Read the series index: `docs/superpowers/specs/2026-08-27-agent-reliability-series-index.md`.
2. Confirm the RFC number is free: **0016–0018 belong to the central-state-plane series** — never reuse them.
3. For run ledger / evidence: extend shipped `metagit.core.routing` and/or [RFC-0017 harness](../../docs/superpowers/specs/2026-07-31-rfc-0017-agentic-workload-harness-design.md); do not open a parallel “RFC-0016 run ledger”.
4. Prefer report-only / dry-run first; mutating paths need explicit flags.
5. After design approval, write plans under `docs/superpowers/plans/` dated for the work day.
6. Update the series index status + `.mex/ROUTER.md` when a package ships.
7. Keep modality parity (`scripts/modality-parity.yml`), CLI/MCP/docs/skills, and `METAGIT_AGENT_MODE` JSON-first behavior.

## Verify
- Series index status table matches reality.
- No new design claims RFC numbers 0016–0018 for reliability work.
- Cross-links from central-state-plane and ACL indexes remain valid.
- `task qa:prepush` green after doc/code changes; `task gitnexus:analyze` last.
