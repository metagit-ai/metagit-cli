---
name: metagit-aos
description: >-
  Compose ACL, task graph, scheduler, merge, and related coordination
  subsystems via metagit aos|coord status|doctor|next. Use when an operator
  or orchestrator needs one snapshot of coordination health or the next
  work envelope without launching models. Start with the day-1 quickstart
  for the canonical control loop.
metadata:
  internal: true
---
# Metagit Agent Operating System (AOS)

<!-- modality:aos_status -->
<!-- modality:run_ledger -->

Use when you need a **composed** view of coordination state, or a preview of
what should run next across ACL + task graph + optional 0009–0012.

**Day-1 control loop (start here):**
[docs/agents-quickstart.md](../../../../docs/agents-quickstart.md)

Full reference: [docs/reference/aos.md](../../../../docs/reference/aos.md)
Run ledger: [docs/reference/run-ledger.md](../../../../docs/reference/run-ledger.md)

Minimal practice workspace: [examples/agent-aos-loop/](../../../../examples/agent-aos-loop/)

## Control loop

```bash
export METAGIT_AGENT_MODE=true

metagit context pack --tier 2 --json
metagit prompt workspace --kind session-start --text-only

metagit aos status --json
metagit aos doctor --json
metagit aos next --json                 # preview (no schedule record)
metagit aos next --commit --json        # record schedule decision
# then compile / ACL / work / complete / merge enqueue as separate steps
metagit context compile --project P --repo R --task-id NODE --json
metagit aos next --apply-hints --agent-id agent-1 --json   # ACL APIs only
metagit task complete --node-id NODE --json
```

Alias: `metagit coord …` is identical to `metagit aos …`.

## Rules

- Doctor `--fix` requires `--yes` and only runs lease expire-on-list + worktree gc.
- `next --apply-hints` never launches models and never runs compile.
- Prefer `aos next` preview before `--commit` when exploring.

## Related

- ACL primitives: skill `metagit-agent-coordination`
- Scheduler alone: `metagit schedule next`
- Quickstart: `docs/agents-quickstart.md`
