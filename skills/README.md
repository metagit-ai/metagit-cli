# Metagit skills

Metagit ships agent **skills** (`skills/metagit-*/SKILL.md`): short playbooks for when and how to use the CLI and MCP. All bundled skills use a `metagit-` prefix.

> **New here?** Read [For AI agents](agents.md) first — install, session start, and context packs.

## Install the CLI

```bash
uv tool install metagit-cli
uv tool install -U metagit-cli   # upgrade
metagit version
```

> PyPI package name: **`metagit-cli`** (not `metagit`).

## Install skills

```bash
metagit skills list
metagit skills show metagit-projects
metagit skills install
metagit skills install --scope user --target openclaw --target hermes
metagit skills install --skill metagit-projects --target openclaw
metagit skills install --skill metagit-projects --target openclaw --dry-run
```

Use `--skill` (repeatable) to install one or more bundled skills instead of the full set. Omit `--skill` to install every bundled skill. Add `--dry-run` to preview targets and paths without writing files.

Optional MCP registration:

```bash
metagit mcp install --scope user --target openclaw --target hermes
```

Other targets: `opencode`, `claude_code`, `github_copilot`.

## Skill catalog

| Skill | Use when |
|-------|----------|
| `metagit-context-pack` | Session start; tiered packs (map, cards, digest), objectives, approvals, repomix profiles |
| `metagit-cli` | CLI-only agent workflows: all `metagit prompt` kinds, catalog, detect, sync, layout (no MCP/API) |
| `metagit-agent-access` | On-demand: optimize any repo for minimal-token agent onboarding (`llms.txt`, hidden README comments, AGENTS.md) |
| `metagit-projects` | Starting work; check for existing projects/repos before new folders |
| `metagit-workspace-scope` | Session start; workspace boundaries; Hermes bootstrap wiring |
| `metagit-control-center` | Ongoing multi-repo coordination |
| `metagit-workspace-sync` | Guarded fetch/pull/clone |
| `metagit-config-refresh` | `.metagit.yml` missing or stale |
| `metagit-bootstrap` | Generate or refine config with discovery/MCP or CLI-only fallbacks |
| `metagit-gating` | MCP workspace gate status |
| `metagit-upstream-scan` | Search other managed repos for causes |
| `metagit-upstream-triage` | Rank upstream blockers |
| `metagit-repo-impact` | Plan cross-repo changes |
| `metagit-multi-repo` | Implement across several repos |
| `metagit-gitnexus` | GitNexus index and graph workflows |
| `metagit-release-audit` | Pre-push / release readiness |

For workspace vs project vs repo definitions, see [Terminology](terminology.md).

## Skill scripts and Hermes `skill_manage`

Bundled skills may include `scripts/` helpers (bash wrappers around `metagit` or small Python utilities).

| Install method | Scripts available? |
|----------------|-------------------|
| `metagit skills install --skill <name>` | Yes — full skill tree copied to agent config dir |
| PyPI package (`metagit-cli` installed) | Yes — under `metagit/data/skills/<name>/scripts/` |
| Hermes `skill_manage` (SKILL.md only) | **No** — use package path below or inline CLI in the skill |

Resolve package-bundled scripts (works whenever `metagit-cli` is installed):

```bash
SKILL_ROOT="$(python3 -c "import metagit, pathlib; print(pathlib.Path(metagit.__file__).parent / 'data/skills/metagit-SKILLNAME')")"
"$SKILL_ROOT/scripts/foo.sh" ...
```

Each affected skill documents an **inline CLI fallback** when scripts are unavailable.
Prefer `metagit skills install --scope user --target hermes` when you want scripts on disk
next to the Hermes skill copy.

## Source development

```bash
task skills:validate
task skills:sync    # mirrors into .cursor/skills/
```

Update both `skills/` and `src/metagit/data/skills/` when changing bundled skills.

Skill helper scripts under `*/scripts/*.sh` use **bash** (`#!/usr/bin/env bash`) for cross-platform compatibility; invoke them directly (`./scripts/foo.sh`) or via `bash scripts/foo.sh`.
