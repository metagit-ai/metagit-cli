---
name: aos-composition
description: Recurring runbook for RFC-0013 AOS composition façade (status/doctor/next).
last_updated: 2026-07-09
---

# AOS composition

## When

Operator or orchestrator needs one coordination snapshot or next-work envelope.

## Steps

1. `metagit aos status --json` (or `coord`) — check `subsystems.*.available`.
2. `metagit aos doctor --json` — review findings; use `--fix --yes` only for ACL GC.
3. `metagit aos next --json` — preview; add `--commit` to record schedule decision.
4. Run compile / ACL / work as separate commands; `--apply-hints` is ACL-only.

## Gotchas

- Doctor `--fix` without `--yes` errors by design.
- Preview must not append `decisions.jsonl`; only `--commit` does.
- Never treat AOS as a model launcher.
