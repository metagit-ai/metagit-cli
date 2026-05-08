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
last_updated: 2026-05-05
---

# Session Bootstrap

If you haven't already read `AGENTS.md`, read it now — it contains the project identity, non-negotiables, and commands.

Then read this file fully before doing anything else in this session.

## Current Project State
**Working:**
- Core CLI command surface (`config`, `detect`, `project`, `record`, `workspace`, `mcp`) with shared app config + logger bootstrapping.
- `.metagit.yml` manager/model pipeline for load/create/save/validate operations.
- MCP runtime with state-aware gating, tool/resource handlers, protocol-framed stdio loop, and runtime tests.
- Workspace index/search/upstream hint services and guarded repo inspect/sync flows.
- Skill scaffold + local wrapper scripts in `skills/*/scripts` for token-efficient agent workflows.
- Runtime packaging compatibility path for version lookup and `python -m metagit` entrypoint behavior in minimal Python environments.
- Docs build path resolves CLI imports correctly in CI by including interactive prompt runtime dependency.
- `release-please` now manages semantic release PRs/tags from conventional commits on `main`, and tag pushes drive PyPI/TestPyPI publish workflows.
- Cross-agent token-optimized pre-push gate is available via `scripts/prepush-gate.py` (with `scripts/prepush-gate.zsh` wrapper) and is expected during session closeout.
- Provider source sync is available via `metagit project source sync` for GitHub org/user and GitLab group recursive discovery with discover/additive/reconcile modes.

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
6. **SESSION CLOSEOUT** — Run `task qa:prepush` before ending the session. If it fails, fix issues and re-run until green (or document blockers explicitly).

## Commit Message Semantics
- Use `fix:` by default (patch-level intent).
- Use `feat:` only for additive backward-compatible behavior.
- Use breaking-change markers (`type(scope)!:` or `BREAKING CHANGE:`) only when intentionally breaking schema/config compatibility (for example `.metagit.yml` or app configuration schema changes).
