# Agent OS quickstart (day-1 control loop)

Canonical **10-minute** path from install to finishing one unit of coordinated work.
Prefer this page over reading every RFC reference on day one.

Full agent guide: [agents.md](agents.md). Deep AOS reference: [reference/aos.md](reference/aos.md).
Reliability roadmap: [superpowers/specs/2026-08-27-agent-reliability-series-index.md](superpowers/specs/2026-08-27-agent-reliability-series-index.md).

> PyPI package: **`metagit-cli`**. Always set `METAGIT_AGENT_MODE=true` for non-interactive JSON-first CLI.

## Install

```bash
uv tool install metagit-cli
export METAGIT_AGENT_MODE=true
metagit version check --json
```

Optional playbooks:

```bash
metagit skills install --scope user
metagit mcp install --scope user
metagit skills show metagit-aos
```

## Control loop (diagram)

```text
install + METAGIT_AGENT_MODE
        │
        ▼
context pack (tier 0→2)  +  prompt session-start
        │
        ▼
aos status / doctor          (health; report-only)
        │
        ▼
aos next [--commit]          (preview, then record decision)
        │
        ▼
context compile              (budgeted pack for the chosen work)
        │
        ▼
ACL bind                     (branch / lease / worktree / claim)
        │
        ▼
agent work in isolated checkout
        │
        ▼
task complete  →  merge enqueue (when ready)
```

AOS **never launches models**. Preview before `--commit`. Doctor `--fix` needs `--yes` and only runs safe ACL GC.

## Day-1 commands (copy/paste)

Run from the umbrella repo that owns `.metagit.yml` (or pass `-c path/to/.metagit.yml`).

### 1. Orient

```bash
metagit context pack --tier 2 --json
metagit prompt workspace --kind session-start --text-only
```

Token-tight: `--tier 0` instead of 2.

### 2. Health

```bash
metagit aos status --json
metagit aos doctor --json
```

### 3. Next work (preview first)

```bash
metagit aos next --json
# when ready to record a schedule decision:
metagit aos next --commit --json
```

Alias: `metagit coord …` ≡ `metagit aos …`.

### 4. Compile + isolate

Use project/repo/task ids from the `next` payload (or create a task first — see below).

```bash
metagit context compile --project P --repo R --task-id NODE --json

metagit branch allocate --agent-id agent-1 --json
metagit lease acquire --allocate --agent-id agent-1 --json
# or apply ACL hints from next:
metagit aos next --apply-hints --agent-id agent-1 --json
```

`--apply-hints` never runs compile and never launches models.

### 5. Finish the unit

```bash
metagit task complete --node-id NODE --json
metagit merge enqueue --json   # when the change is ready to integrate
```

If no task graph exists yet, create a minimal node before `aos next` can rank work:

```bash
metagit task create --title "First coordinated change" --project P --repo R --json
metagit task ready --json
```

## Minimal example workspace

See [examples/agent-aos-loop/](https://github.com/metagit-ai/metagit-cli/blob/main/examples/agent-aos-loop/) — a tiny umbrella manifest whose `agent_instructions` encode this loop.

```bash
cd examples/agent-aos-loop
export METAGIT_AGENT_MODE=true
metagit config validate -c .metagit.yml
metagit prompt workspace --kind session-start --text-only -c .metagit.yml
metagit aos status --json --definition .metagit.yml
```

(Without cloned repos or a task graph, `aos next` may return an empty ready set — that is expected for the dry example.)

## When to read more

| Need | Doc / skill |
|------|-------------|
| Full command catalog | [agents.md](agents.md) |
| ACL primitives | [reference/agent-coordination.md](reference/agent-coordination.md) · skill `metagit-agent-coordination` |
| Task graph | [reference/task-graph.md](reference/task-graph.md) |
| Context compile | [reference/context-compiler.md](reference/context-compiler.md) |
| Scheduler | [reference/agent-scheduler.md](reference/agent-scheduler.md) |
| AOS flags & MCP | [reference/aos.md](reference/aos.md) · skill `metagit-aos` |
| Feature registry | [reference/modality-feature-registry.md](reference/modality-feature-registry.md) |

## MCP shortcut

When the workspace gate is **ACTIVE**:

| Step | Tool |
|------|------|
| Pack | `metagit_context_pack` |
| Status / doctor / next | `metagit_aos_status` · `metagit_aos_doctor` · `metagit_aos_next` |
| Compile | `metagit_context_compile` |

Resource ladder: `metagit://catalog` → `workspace/map` → `prompt/workspace/session-start?instructions=0`.
