---
name: agents
description: Always-loaded project anchor. Read this first. Contains project identity, non-negotiables, commands, and pointer to .mex/ROUTER.md for full context. Use GitNexus MCP tools for all structural and impact analysis.
last_updated: 2026-09-06
---

# Metagit

## What This Is
Metagit gives you situational awareness across Git repositories. It helps multi-repo projects feel manageable, discoverable, and cohesive. It captures cross-repository relationships and project knowledge in easy to understand version controlled manifests.

**Day-1 Agent OS loop:** [docs/agents-quickstart.md](docs/agents-quickstart.md) — install → context pack → `aos next` → compile/ACL → complete.

## After Every Task
After meaningful work, run GROW:
- Prepare: Run `task qa:prepush` and resolve any errors. Rerun until all failures are resolved.
- Ground: what changed in reality?
- Record: update `.mex/ROUTER.md` and relevant `.mex/context/` files
- Orient: create or update a `.mex/patterns/` runbook if this can recur
- Write: bump `last_updated` on changed scaffold files and run `mex log` when rationale matters

## Navigation
At the start of every session, read `.mex/ROUTER.md` before doing anything else.
For full project context, patterns, and task guidance — everything is there.

# Metagit — agent quick reference

For agents instructed to **use Metagit** (not necessarily to contribute to this repository).

**Install:** `uv tool install metagit-cli` · set `METAGIT_AGENT_MODE=true` · PyPI name **`metagit-cli`**.

**Quickstart:** [docs/agents-quickstart.md](docs/agents-quickstart.md) · example [examples/agent-aos-loop/](examples/agent-aos-loop/)

**Session start** (from repo with `.metagit.yml`):

```bash
metagit -c .metagit.yml context pack --tier 2 --json
metagit -c .metagit.yml prompt workspace --kind session-start --text-only
```

**Skills:** `metagit skills install --scope user` · **MCP:** `metagit mcp install --scope user`

| Need | Command |
|------|---------|
| Workspace map / repo cards | `metagit context pack --tier 0\|1\|2 --json` |
| Find managed repo | `metagit search "…" --json` |
| Repo CI topology | `metagit project repo ci show` / `detect` / `set` (`--json`) |
| Search repo file contents | `metagit workspace grep "…" --json` |
| Grep backend (ripgrep) | `metagit workspace grep info --json` |
| Catalog | `metagit workspace list --json` |
| Operational prompts | `metagit prompt list` |
| Scoped repo text | `metagit context repomix --profile bugfix-local --project P --repo R` |
| Latest release / notes | `metagit version check --json` |
| Self-update | `metagit version upgrade --apply --json` |
| Agent profile / apply | `metagit agent profile show` / `metagit agent apply --vendor cursor` |
| Campaigns | `metagit campaign list` · `metagit campaign new` · `metagit campaign expand` |
| Derived surgical project | `metagit project derived create -n N --from P/R` · `refresh` · `include` · `exclude` |
| Skills surface | `metagit skills surface --json` |
| ACL isolate agent checkout | `metagit branch allocate` · `metagit lease acquire --allocate` · `metagit worktree create` |
| ACL file claims | `metagit claim declare` · `metagit claim check` |
| Task graph / intent | `metagit task create` · `metagit task expand` · `metagit task ready` · `metagit task complete` |
| Context compile | `metagit context compile --project P --repo R [--task-id N] --json` |
| Components (RFC-0026/0027/0028) | Nested `repos[].components[]`; `metagit component list|show|resolve|graph`; MCP `metagit_component_*`; `metagit config validate` · [docs/concepts/components.md](docs/concepts/components.md) |
| Context switch | `metagit context switch <project> [<repo>]` · `--json` · MCP `metagit_context_switch` |
| Nav (human) | `metagit nav` / `navigate` [-p PROJECT] [--repo REPO] |
| Semantic ownership | `metagit semantic declare` · `metagit semantic owners` · `metagit semantic conflicts` |
| Merge orchestration | `metagit merge enqueue` · `metagit merge integrate` · `metagit merge status` |
| Agent scheduler | `metagit schedule next` · `metagit schedule status` · `metagit schedule policy show` |
| Agent OS (composition) | `metagit aos status` · `metagit aos doctor` · `metagit aos next` (`coord` alias) |
| Local Atlas | `metagit atlas init` · `metagit atlas generate` · `metagit atlas validate` · `metagit atlas query` |
| Agent coordination skill | `metagit skills show metagit-agent-coordination` |
| Agent OS skill | `metagit skills show metagit-aos` |
| Agent coordination (ACL) | [docs/reference/agent-coordination.md](docs/reference/agent-coordination.md) |
| Task graph (RFC-0008) | [docs/reference/task-graph.md](docs/reference/task-graph.md) |
| Context compiler (RFC-0009) | [docs/reference/context-compiler.md](docs/reference/context-compiler.md) |
| Semantic ownership (RFC-0010) | [docs/reference/semantic-ownership.md](docs/reference/semantic-ownership.md) |
| Merge orchestrator (RFC-0011) | [docs/reference/merge-orchestrator.md](docs/reference/merge-orchestrator.md) |
| Agent scheduler (RFC-0012) | [docs/reference/agent-scheduler.md](docs/reference/agent-scheduler.md) |
| Agent OS (RFC-0013) | [docs/reference/aos.md](docs/reference/aos.md) |
| Metagit Atlas (RFC-0014) | [docs/reference/atlas.md](docs/reference/atlas.md) |
| Feature registry (all modalities) | [docs/reference/modality-feature-registry.md](docs/reference/modality-feature-registry.md) |

Full guide: [docs/agents.md](docs/agents.md) · Index: [llms.txt](llms.txt) · Skills: [docs/skills.md](docs/skills.md) · Docs: <https://metagit-ai.github.io/metagit-cli/agents/>

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **metagit-cli** (17846 symbols, 38515 relationships, 1008 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/metagit-cli/context` | Codebase overview, check index freshness |
| `gitnexus://repo/metagit-cli/clusters` | All functional areas |
| `gitnexus://repo/metagit-cli/processes` | All execution flows |
| `gitnexus://repo/metagit-cli/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
