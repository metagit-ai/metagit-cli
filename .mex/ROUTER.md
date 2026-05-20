---
name: router
description: Session bootstrap and navigation hub. Read at the start of every session before any task. Contains project state, routing table, and behavioural contract.
edges:
  - target: context/architecture.md
    condition: when working on system design, integrations, or understanding how components connect
  - target: context/stack.md
    condition: when working with specific technologies, libraries, or making tech decisions
  - target: context/conventions.md
    condition: when writing new code, reviewing code, or unsure about project patterns
  - target: context/decisions.md
    condition: when making architectural choices or understanding why something is built a certain way
  - target: context/setup.md
    condition: when setting up the dev environment or running the project for the first time
  - target: context/mcp-runtime.md
    condition: when implementing MCP runtime, tool schemas, resource handlers, or protocol behavior
  - target: patterns/INDEX.md
    condition: when starting a task — check the pattern index for a matching pattern file
last_updated: 2026-05-19
---

# Session Bootstrap

If you haven't already read `AGENTS.md`, read it now — it contains the project identity, non-negotiables, and commands.

Then read this file fully before doing anything else in this session.

## Current Project State
**Working:**
- Core CLI command surface (`config`, `detect`, `project`, `record`, `workspace`, `mcp`, `search` / `find`, `api serve` for local JSON v1 search + **v2 catalog CRUD**, `project repo prune` for sync-folder cleanup) with shared app config + logger bootstrapping.
- **Workspace catalog** (`WorkspaceCatalogService`): list/add/remove projects and repos in `.metagit.yml` via CLI (`--json`), MCP (`metagit_workspace_*` catalog tools), and HTTP `/v2/*`.
- **`metagit prompt`**: scoped prompt emission (`workspace` / `project` / `repo`) for agents — manifest instructions plus operational templates (session-start, catalog-edit, sync-safe, **repo-enrich**, etc.). Bundled **`metagit-cli`** skill documents CLI-only shortcuts (all prompt kinds; no MCP/API).
- **`agent_mode`** / **`METAGIT_AGENT_MODE`**: disables interactive CLI (fuzzy finder, prompts, editor); `metagit appconfig show --format json` exposes full config including `workspace.dedupe` (default **enabled**).
- **Workspace layout** (`WorkspaceLayoutService`): rename/move projects and repos (manifest + sync folders, dedupe-aware, session migration); CLI, MCP, HTTP v2 — see `docs/reference/workspace-layout-api.md`.
- `.metagit.yml` manager/model pipeline for load/create/save/validate operations.
- MCP runtime with state-aware gating, tool/resource handlers (search, **semantic search**, sync, cross-project dependencies, project context, snapshots, health check with branch-age staleness, file discover, template apply), resources for health/context, protocol-framed stdio loop, and runtime tests.
- Workspace index/search/upstream hint services, `ManagedRepoSearchService` for managed-only repo matching, local read-only HTTP routes under `metagit.core.api`, and guarded repo inspect/sync flows.
- Skill scaffold + local wrapper scripts in `skills/*/scripts` for token-efficient agent workflows, including `metagit-projects` for OpenClaw/Hermes workspace project lifecycle (check-before-create, register in `.metagit.yml`).
- `docs/skills.md` documents global install, `metagit skills install`, and bundled skill overview.
- Runtime packaging compatibility path for version lookup and `python -m metagit` entrypoint behavior in minimal Python environments.
- Docs build path resolves CLI imports correctly in CI by including interactive prompt runtime dependency.
- A semantic-release workflow now computes and pushes tags from conventional commits on `main`, and tag pushes drive PyPI/TestPyPI publish workflows.
- **`task qa:prepush`** (via `scripts/prepush-gate.py` / `prepush-gate.zsh`) is mandatory in the behavioural contract whenever a session modifies tracked files — not optional “session closeout only.”
- Provider source sync is available via `metagit project source sync` for GitHub org/user and GitLab group recursive discovery with discover/additive/reconcile modes.
- Fuzzy finder repo selection UX now shows result counters, keeps full scrollable match sets, respects project `.gitignore` entries during filesystem candidate discovery, and provides richer repo metadata in preview.
- New `skills` CLI command (`list`, `show`, `install`) plus `mcp install` now support auto-detected agent targets across project/user scopes, with bundled package skills deployed from `src/metagit/data/skills`.
- Focused `graphify` runs on subtrees produce `graphify-out/` HTML/report artifacts quickly enough to use for local command-surface exploration without analyzing the entire repository.
- **Workspace dedupe:** `workspace.dedupe` in app config (default enabled); optional per-project `workspace.projects[].dedupe.enabled` in `.metagit.yml` overrides the flag for sync/layout under that project only.
- **`metagit config example`:** generates `docs/reference/metagit-config.full-example.yml` (via `task generate:schema`) with field-description comments.
- **Hermes orchestrator template:** `hermes-orchestrator` under `src/metagit/data/templates/`, example manifest at `examples/hermes-orchestrator/.metagit.yml`, guide at `docs/hermes-orchestrator-workspace.md`.
- **`metagit init`:** bundled init templates (`application`, `umbrella`, `hermes-orchestrator`) with copier-style `{{ var }}` rendering, `--answers-file`, `--no-prompt`, all `ProjectKind` values via `--minimal`.

**Not yet built:**
- Full production-grade MCP lifecycle extras (e.g., richer notifications, broader method surface, advanced capability negotiation details).
- End-to-end enterprise mode features described in README (continuous org-wide code mining).
- Matured sampling execution path with robust timeout/retry/error telemetry across diverse MCP hosts.

**Known issues:**
- Local `black` execution path is unstable in this environment; project lint path currently relies on Ruff workflow.
- Some MCP schema/tool contracts are still evolving and may require downstream client adjustments.
- Pydantic deprecation warnings are present in test output due to existing class-based config usage.

## Routing Table

Load the relevant file based on the current task. Always load `context/architecture.md` first if not already in context this session.

| Task type | Load |
|-----------|------|
| Understanding how the system works | `context/architecture.md` |
| Working with a specific technology | `context/stack.md` |
| Writing or reviewing code | `context/conventions.md` |
| Making a design decision | `context/decisions.md` |
| Setting up or running the project | `context/setup.md` |
| Working on MCP runtime/tools/resources/protocol | `context/mcp-runtime.md` |
| Any specific task | Check `patterns/INDEX.md` for a matching pattern |

## Behavioural Contract

For every task, follow this loop:

1. **CONTEXT** — Load the relevant context file(s) from the routing table above. Check `patterns/INDEX.md` for a matching pattern. If one exists, follow it. Narrate what you load: "Loading architecture context..."
2. **BUILD** — Do the work. If a pattern exists, follow its Steps. If you are about to deviate from an established pattern, say so before writing any code — state the deviation and why.
3. **VERIFY** — Load `context/conventions.md` and run the Verify Checklist item by item. State each item and whether the output passes. Do not summarise — enumerate explicitly.
4. **DEBUG** — If verification fails or something breaks, check `patterns/INDEX.md` for a debug pattern. Follow it. Fix the issue and re-run VERIFY.
5. **GROW** — After completing the task:
   - If no pattern exists for this task type, create one in `patterns/` using the format in `patterns/README.md`. Add it to `patterns/INDEX.md`. Flag it: "Created `patterns/<name>.md` from this session."
   - If a pattern exists but you deviated from it or discovered a new gotcha, update it with what you learned.
   - If any `context/` file is now out of date because of this work, update it surgically — do not rewrite entire files.
   - Update the "Current Project State" section above if the work was significant.
6. **QA GATE (mandatory for any delivered work)** — If you changed or added tracked project files in this conversation, run `task qa:prepush` from the repo root before reporting the task as finished. Fix failures and re-run until green. Also run `task skills:sync generate:schema` when bundled skills/schemas need to stay mirrored (see conventions). Omit the QA gate only for strictly read‑only exploration (no file writes) or when the user explicitly waived it in this thread. Document any intentional blockers plainly.

## Commit Message Semantics
- Use `fix:` by default (patch-level intent).
- Use `feat:` only for additive backward-compatible behavior.
- Use breaking-change markers (`type(scope)!:` or `BREAKING CHANGE:`) only when intentionally breaking schema/config compatibility (for example `.metagit.yml` or app configuration schema changes).
