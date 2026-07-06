---
name: agents
description: Always-loaded project anchor. Read this first. Contains project identity, non-negotiables, commands, and pointer to .mex/ROUTER.md for full context. Use GitNexus MCP tools for all structural and impact analysis.
last_updated: [YYYY-MM-DD]
---

# Metagit

## What This Is
Metagit gives you situational awareness across Git repositories. It helps multi-repo projects feel manageable, discoverable, and cohesive. It captures cross-repository relationships and project knowledge in easy to understand version controlled manifests.

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

**Session start** (from repo with `.metagit.yml`):

```bash
metagit context pack --tier 2 --json
metagit prompt workspace --kind session-start --text-only
```

**Skills:** `metagit skills install --scope user` · **MCP:** `metagit mcp install --scope user`

| Need | Command |
|------|---------|
| Workspace map / repo cards | `metagit context pack --tier 0\|1\|2 --json` |
| Find managed repo | `metagit search "…" --json` |
| Search repo file contents | `metagit workspace grep "…" --json` |
| Grep backend (ripgrep) | `metagit workspace grep info --json` |
| Catalog | `metagit workspace list --json` |
| Operational prompts | `metagit prompt list` |
| Scoped repo text | `metagit context repomix --profile bugfix-local --project P --repo R` |
| Latest release / notes | `metagit version check --json` |
| Self-update | `metagit version upgrade --apply --json` |
| Agent profile / apply | `metagit agent profile show` / `metagit agent apply --vendor cursor` |
| Campaigns | `metagit campaign list` · `metagit campaign new` · `metagit campaign expand` |
| Feature registry (all modalities) | [docs/reference/modality-feature-registry.md](docs/reference/modality-feature-registry.md) |

Full guide: [docs/agents.md](docs/agents.md) · Index: [llms.txt](llms.txt) · Skills: [docs/skills.md](docs/skills.md) · Docs: <https://metagit-ai.github.io/metagit-cli/agents/>

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **metagit-cli** (10131 symbols, 17401 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/metagit-cli/context` | Codebase overview, check index freshness |
| `gitnexus://repo/metagit-cli/clusters` | All functional areas |
| `gitnexus://repo/metagit-cli/processes` | All execution flows |
| `gitnexus://repo/metagit-cli/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
