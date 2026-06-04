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
last_updated: 2026-06-04
---

# Session Bootstrap

If you haven't already read `AGENTS.md`, read it now — it contains the project identity, non-negotiables, and commands.

Then read this file fully before doing anything else in this session.

## Current Project State
**Working:**
- Core CLI command surface (`config`, `detect`, `project`, `record`, `workspace`, `mcp`, `search` / `find`, `api serve` for local JSON v1 search + **v2 catalog CRUD**, `project repo prune` for sync-folder cleanup) with shared app config + logger bootstrapping.
- **Workspace catalog** (`WorkspaceCatalogService`): list/add/remove projects and repos in `.metagit.yml` via CLI (`--json`), MCP (`metagit_workspace_*` catalog tools), and HTTP `/v2/*`. **`workspace.projects[]`** supports `protected`, `tags`, `documentation`, `metadata`; repo **`kind`** removed from `ProjectPath` (use tags). **`dependencies[]`** uses dedicated `Dependency` model with `DependencyKind` (`docker_image`, `repository`, etc.). Project tags inherit into index/search; protected projects block catalog/layout/repo mutations without `force`.
- **`metagit prompt`**: scoped prompt emission (`workspace` / `project` / `repo`) for agents — manifest instructions plus operational templates (session-start, catalog-edit, sync-safe, **repo-enrich**, **context-pack** tier-0/tier-1 guidance, etc.). Bundled **`metagit-cli`** skill documents CLI-only shortcuts (all prompt kinds; no MCP/API). Bundled **`metagit-context-pack`** skill documents tier 0/1/2 packs, digest, objectives, approvals, repomix, Hermes session bootstrap, and multi-instance Syncthing guidance.
- **`agent_mode`** / **`METAGIT_AGENT_MODE`**: disables interactive CLI (fuzzy finder, prompts, editor); `metagit appconfig show --format json` exposes full config including `workspace.dedupe` (default **disabled**).
- **Workspace layout** (`WorkspaceLayoutService`): rename/move projects and repos (manifest + sync folders, dedupe-aware, session migration); CLI, MCP, HTTP v2 — see `docs/reference/workspace-layout-api.md`.
- `.metagit.yml` manager/model pipeline for load/create/save/validate operations.
- MCP runtime with state-aware gating, tool/resource handlers (search, **semantic search**, sync, cross-project dependencies, project context, snapshots, health check with branch-age staleness, file discover, template apply, **context packs** `metagit_context_pack` / `metagit_repo_card`), resources for health/context, protocol-framed stdio loop, and runtime tests.
- Workspace index/search/upstream hint services, `ManagedRepoSearchService` for managed-only repo matching, local read-only HTTP routes under `metagit.core.api` (**`GET /v2/workspace/grep`** + **`GET /v2/workspace/grep/info`** via `GrepApiHandler`), **`metagit workspace grep`** CLI group (search + `info`), MCP **`metagit_workspace_search`** / **`metagit_workspace_grep_info`**, bundled **`metagit-workspace-grep`** skill, and guarded repo inspect/sync flows.
- Skill scaffold + local wrapper scripts in `skills/*/scripts` for token-efficient agent workflows, including `metagit-projects` for OpenClaw/Hermes workspace project lifecycle (check-before-create, register in `.metagit.yml`).
- `docs/skills.md` documents global install, `metagit skills install`, and bundled skill overview.
- Runtime packaging compatibility path for version lookup and `python -m metagit` entrypoint behavior in minimal Python environments.
- Docs build path resolves CLI imports correctly in CI by including interactive prompt runtime dependency.
- **`task docs:links`** validates markdown links in `README.md` and `docs/**/*.md` via lychee (`scripts/check-doc-links.zsh`, `lychee.toml`); CI runs the same check on Ubuntu in `.github/workflows/test.yaml`. `docs/index.md` is a separate MkDocs home page (not a symlink to README) with docs-relative asset paths.
- A semantic-release workflow now computes and pushes tags from conventional commits on `main`, and tag pushes drive PyPI/TestPyPI publish workflows.
- **`task qa:prepush`** (via `scripts/prepush-gate.py` / `prepush-gate.zsh`) is mandatory in the behavioural contract whenever a session modifies tracked files — not optional “session closeout only.” Includes **`manifest_fixtures`** step validating curated manifests listed in `scripts/manifest-fixtures.yml` (`.metagit.yml`, `.metagit.example.yml`, `examples/hermes-orchestrator/.metagit.yml`, …).
- **Skill helper scripts:** bundled `skills/*/scripts/*.sh` use bash for cross-platform wrappers around `uv run python` (zsh retained only for local dev gate script).
- Provider source sync is available via `metagit project source sync` for GitHub org/user and GitLab group recursive discovery with discover/additive/reconcile modes.
- Fuzzy finder repo selection UX now shows result counters, keeps full scrollable match sets, respects project `.gitignore` entries during filesystem candidate discovery, and provides richer repo metadata in preview.
- New `skills` CLI command (`list`, `show`, `install`) plus `mcp install` now support auto-detected agent targets across project/user scopes, with bundled package skills deployed from `src/metagit/data/skills`.
- Focused `graphify` runs on subtrees produce `graphify-out/` HTML/report artifacts quickly enough to use for local command-surface exploration without analyzing the entire repository.
- **Workspace dedupe:** `workspace.dedupe` in app config (default disabled); optional per-project `workspace.projects[].dedupe.enabled` in `.metagit.yml` overrides the flag. `metagit project sync --hydrate` materializes symlink mounts into full copies.
- **`metagit config example`:** generates `docs/reference/metagit-config.full-example.yml` (via `task generate:schema`) with field-description comments.
- **Hermes orchestrator template:** `hermes-orchestrator` under `src/metagit/data/templates/`, example manifest at `examples/hermes-orchestrator/.metagit.yml`, guide at `docs/hermes-orchestrator-workspace.md`.
- **`metagit init`:** bundled init templates (`application`, `umbrella`, `hermes-orchestrator`) with copier-style `{{ var }}` rendering, `--answers-file`, `--no-prompt`, all `ProjectKind` values via `--minimal`; idempotent when a valid `.metagit.yml` already exists (`--force` to overwrite).
- **Shell tab completion:** `metagit completion show|install|doctor` for zsh/bash/fish; dynamic `--project` / `--repo` / repomix `--profile` completion when a manifest is present (`src/metagit/cli/shell_completion.py`, `docs/install.md`).
- **`metagit fmt` / `metagit format`:** schema-ordered, readable YAML for `.metagit.yml` and `metagit.config.yaml`; preserves comments, injects yaml-language-server schema directive, 2-space indent, **88-column string wrapping** (`yaml_display`, `yaml_roundtrip`). **Default formatting omits schema-default optional fields** (empty lists/dicts, false, etc.); use **`--include-defaults`** to retain them. Web Config Studio and `metagit config patch --save` default to **auto-format on save** (`auto_format` / `--no-format`).
- **`metagit web serve` groundwork:** Pydantic request/response models for the local web UI API live in `src/metagit/core/web/models.py` (`ConfigTreeResponse`, sync job shapes, config patch types). Thread-safe in-memory sync job tracking + SSE event buffers live in `src/metagit/core/web/job_store.py` (`SyncJobStore`).
- **`metagit web serve` config HTTP:** `build_web_server` in `src/metagit/core/web/server.py` exposes v3 config tree/patch/validate routes via `ConfigWebHandler` (`metagit` + `appconfig` targets, `SchemaTreeService` mutations). PATCH with `save=true` returns HTTP 422 and skips disk write when validation fails; masked sensitive tokens are preserved on noop set.
- **`metagit web serve` ops HTTP:** `OpsWebHandler` (`src/metagit/core/web/ops_handler.py`) — POST health/prune/sync, GET `/v3/ops/objectives`, POST upsert objectives, PATCH status, GET `/v3/ops/approvals`, POST resolve approvals, GET sync job status, SSE sync events; wired in `build_web_server` with workspace root from appconfig.
- **`metagit web serve` static + full server:** `StaticWebHandler` serves packaged SPA from `src/metagit/data/web/`; `build_web_server` dispatches static, v2 catalog/layout, v3 config/ops; CLI `metagit web serve` (`src/metagit/cli/commands/web.py`).
- **Context packs (tier 1 repo cards):** `RepoCardService` (`src/metagit/core/context/repo_card_service.py`) merges workspace index rows, `inspect_repo_state`, manifest fields, stack root hints (`_stack_hints`), layered agent instruction excerpts (`AgentInstructionsResolver`), and `_health_flags` (`missing_clone`, `dirty`, `behind_remote`, `stale_head_30d`). Tests under `tests/core/context/test_repo_card_service.py`.
- **Metagit Web UI scaffold:** Vite + React + TypeScript in `web/` (build output → `src/metagit/data/web/`); typed API client, router shell, Taskfile `web:*` tasks.
- **Metagit Web Config Studio:** schema tree + field editor for `/config/metagit` and `/config/appconfig` (TanStack Query PATCH flow, theme toggle, `enum_options` on schema nodes).
- **Metagit Web:** local `metagit web serve` + packaged SPA (**Config Studio** on `/config/*`, **Workspace Console** on `/workspace` with repo table, **content grep** search tab, graph view, ops panel) with `task web:dev` / `task web:build` workflow documented in [`docs/reference/metagit-web.md`](../docs/reference/metagit-web.md).
- **Context packs — T0 map:** pydantic envelopes in `metagit.core.context.models` plus `WorkspaceMapService` (`workspace_map_service.py`) building `WorkspaceMapResult` from `WorkspaceCatalogService.list_workspace(..., include_index=True)` / `repos_index` rows mapped to `WorkspaceMapEntry`.
- **Context packs CLI:** `metagit context pack --tier 0|1|2` (map; map+cards; map+cards+digest+touches session boundary) plus `repomix` / `context objective|approval …` helpers in `src/metagit/cli/commands/context.py`, backed by `ContextPackService.pack` (`context_pack_service.py`); CLI tests in `tests/cli/commands/test_context.py`; service unit tests in `tests/core/context/test_context_pack_service.py`.
- **Context packs MCP:** ACTIVE-state tools `metagit_context_pack` (required `tier` 0, 1, or 2), `metagit_objective_list`, `metagit_objective_upsert`, `metagit_approval_request`, `metagit_approval_list`, `metagit_approval_resolve`, and `metagit_repo_card` (required `project_name`, `repo_name`), returning JSON via `model_dump(mode="json")`; coverage in `tests/core/mcp/test_runtime.py`.
- **Repomix context profiles:** bundled `src/metagit/data/context_profiles.yaml` (`bugfix-local`, `config-edit`, `cross-repo-impact`); `RepomixProfileService` (`repomix_profile_service.py`) loads include/exclude globs and runs `repomix` with `--include` / `--ignore` for a repo path. Unit tests in `tests/core/context/test_repomix_profile_service.py`.
- **Context packs — T2 session digest:** `SessionDigestService` (`src/metagit/core/context/session_digest_service.py`) emits `SessionDigestResult`: first session when `since` is omitted; otherwise per-repo `git rev-list --count` / `git log --oneline -n 3` after an ISO boundary plus `manifest_changed` from config mtime vs `since`. Tests in `tests/core/context/test_session_digest_service.py`.
- **Workspace objectives:** `ObjectiveService` + `ObjectiveStore` persist objectives to `.metagit/sessions/objectives.json`; models and validators live in `metagit.core.context.models`; tests in `tests/core/context/test_objective_service.py`.
- **Approval queue:** `ApprovalService` (`approval_service.py`) with `ApprovalStore` writing `.metagit/approvals/pending.json`; models `ApprovalRequest` / `ApprovalListResult`; CLI **`metagit context approval request`** (stdin JSON) plus list/approve/deny; tests `tests/core/context/test_approval_service.py`.
- **Workspace root resolution:** `root_resolver.py` splits **sync root** (repo mounts under `appconfig.workspace.path`) from **session root** (manifest directory for `.metagit/sessions` + objectives/approvals). Context pack tier-2 uses both; fixes `active_objective_id` when sync path ≠ manifest root.
- **Objective partial upsert:** `ObjectiveService.upsert_partial` deep-merges by id (`title` required on create only); `notes` aliases to append-only `agent_notes`.
- **Manifest-root repo paths:** `WorkspaceIndexService` resolves `path: ./` or `.` to the definition root (self-referencing coordinator repos).
- **`metagit config validate -c`:** subcommand accepts `-c`/`--config-path` after `validate`.
- **Documentation entry tags:** `documentation[].tags` is canonical **`list[str]`** (legacy map input normalized on load via `normalize_documentation_tags`); project/repo tags remain `dict[str, str]`.
- **Web Config Studio unsaved edits:** `SchemaTreeService._navigate_parent(..., mutate=True)` materializes null list/object parents before REMOVE/APPEND; React `SchemaTree` sends cumulative `pendingOps` on each PATCH so preview removes work before disk save.

**Not yet built:**
- **`task repomix:profile` automation:** bundled profiles + CLI `metagit context repomix` ship in code; repo Taskfile wrappers may remain future scope (see design note in `docs/superpowers/specs/2026-05-21-context-packs-phase2-design.md`).
- **Metagit Web hardened/exposed deployments:** intentional v1 localhost-only framing; authentication and safe non-local binds are future scope.
- Full production-grade MCP lifecycle extras (e.g., richer notifications, broader method surface, advanced capability negotiation details).
- End-to-end enterprise mode features described in README (continuous org-wide code mining).
- Matured sampling execution path with robust timeout/retry/error telemetry across diverse MCP hosts.

**Known issues:**
- Local `black` execution path is unstable in this environment; project lint path currently relies on Ruff workflow.
- Some MCP schema/tool contracts are still evolving and may require downstream client adjustments.
- Pydantic deprecation warnings are present in test output due to existing class-based config usage.
- **`metagit project list` / `select`:** manifest-driven project resolution (`layout_resolver`) — no synthetic in-memory `default` workspace project; optional app-config `default_project` preference; `local` for application manifests without `workspace.projects`.

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
7. **GITNEXUS (always last)** — Run `task gitnexus:analyze` from the repo root as the final step before hand-off whenever this session changed tracked files (including after QA passes). Skip only for strictly read‑only exploration with no writes.

## Commit Message Semantics
- Use `fix:` by default (patch-level intent).
- Use `feat:` only for additive backward-compatible behavior.
- Use breaking-change markers (`type(scope)!:` or `BREAKING CHANGE:`) only when intentionally breaking schema/config compatibility (for example `.metagit.yml` or app configuration schema changes).
