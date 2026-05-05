<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **metagit-cli** (3672 symbols, 5447 relationships, 73 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
| Work in the Examples area (87 symbols) | `.claude/skills/generated/examples/SKILL.md` |
| Work in the Mcp area (40 symbols) | `.claude/skills/generated/mcp/SKILL.md` |
| Work in the Commands area (38 symbols) | `.claude/skills/generated/commands/SKILL.md` |
| Work in the Record area (26 symbols) | `.claude/skills/generated/record/SKILL.md` |
| Work in the Services area (20 symbols) | `.claude/skills/generated/services/SKILL.md` |
| Work in the Providers area (16 symbols) | `.claude/skills/generated/providers/SKILL.md` |
| Work in the Cluster_45 area (11 symbols) | `.claude/skills/generated/cluster-45/SKILL.md` |
| Work in the Cluster_53 area (11 symbols) | `.claude/skills/generated/cluster-53/SKILL.md` |
| Work in the Cluster_41 area (8 symbols) | `.claude/skills/generated/cluster-41/SKILL.md` |
| Work in the Detect area (8 symbols) | `.claude/skills/generated/detect/SKILL.md` |
| Work in the Gitcache area (8 symbols) | `.claude/skills/generated/gitcache/SKILL.md` |
| Work in the Detectors area (7 symbols) | `.claude/skills/generated/detectors/SKILL.md` |
| Work in the Config area (6 symbols) | `.claude/skills/generated/config/SKILL.md` |
| Work in the Project area (6 symbols) | `.claude/skills/generated/project/SKILL.md` |
| Work in the Tests area (6 symbols) | `.claude/skills/generated/tests/SKILL.md` |
| Work in the Appconfig area (5 symbols) | `.claude/skills/generated/appconfig/SKILL.md` |
| Work in the Cluster_58 area (5 symbols) | `.claude/skills/generated/cluster-58/SKILL.md` |
| Work in the Cli area (4 symbols) | `.claude/skills/generated/cli/SKILL.md` |
| Work in the Cluster_52 area (4 symbols) | `.claude/skills/generated/cluster-52/SKILL.md` |

<!-- gitnexus:end -->
