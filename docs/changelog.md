# Changelog

## Unreleased

### Added
- Agent OS day-1 quickstart: [agents-quickstart.md](agents-quickstart.md), example workspace `examples/agent-aos-loop/`, and session-start / `metagit-aos` skill pointers to the canonical control loop.
- Run ledger read surface: `metagit run show|replay|export`, MCP `metagit_run_*`, and AOS commit `run_id` recording. See [reference/run-ledger.md](reference/run-ledger.md).

### Changed
- Bump uv override `pip` to `>=26.2.1` (PYSEC-2026-3721).


## [0.29.0] - 2026-08-23



### Added
- Azure DevOps as a declarative repo source (`azure_devops` in `workspace.projects[].sources[]` / `metagit project source sync`) with AppConfig `providers.azure_devops` and `METAGIT_AZURE_DEVOPS_*` / `AZURE_DEVOPS_EXT_PAT` token wiring.
- Durable agent-facing CI topology on managed repos (`ProjectPath.ci` / `RepoCiTarget`): `metagit project repo ci show|detect|set`, MCP `metagit_repo_ci_show` / `metagit_repo_ci_detect`, and `ci` summaries on tier-1 repo cards. See [docs/reference/ci-targets.md](reference/ci-targets.md).

## [0.28.3] - 2026-08-12



### Fixed
- AppConfig JSON schema generation now wraps root to accept `{"config": AppConfig}` format, matching the actual YAML file structure
- AppConfig JSON schema now allows legacy `default_profile` key (normalized away at load time)
- `metagit appconfig validate` now respects CLI `-c` flag context: explicit `--config-path` > CLI `-c` appconfig > CLI `-c` manifest's local `metagit.config.yaml` > internal default

## [0.28.0] - 2026-08-11



### Added
- Routing engine and run ledger foundations under `metagit.core.routing` with deterministic intent matching (`route query`), class catalog storage, run evidence records, and promotion policy evaluation with safety ceiling enforcement for mutating classes.
- New CLI command groups: `metagit route` (`query`, `list`, `show`), `metagit run` (`open`, `close`, `list`), and `metagit lane eval` for policy-driven tier updates.
- MCP parity tools: `metagit_route_query` and `metagit_lane_eval` with active-workspace gating and JSON schemas exposed in `tools/list`.

### Changed
- `.metagit.yml` schema now supports optional `routing` configuration (`catalog`, `runs`, `id_prefix`, and promotion policy defaults) used by CLI and MCP routing workflows.

## [0.27.0] - 2026-08-09



### Added
- `metagit context resume` to select the best objective to continue (prefers `in_progress`, then most recently updated) with optional substring filtering and `--json` output.
- `metagit context pause` as a low-friction capture command that creates or updates an `in_progress` objective with quick note fields.
- `metagit context objective edit` for direct field updates (`title`, `status`, `repos`, `acceptance`, `human_notes`, `agent_notes`) without JSON stdin.

### Changed
- `metagit context objective set` now accepts ADHD-friendly note capture flags (`--human-notes`, `--left-off`, `--next`, `--blockers`, `--notes-file`) alongside existing stdin JSON flow.
- Objective service now normalizes absolute in-workspace repo references to manifest-relative `./...` paths and preserves external absolute paths for portability across machines.
- MCP adds `metagit_context_resume` parity tooling, and docs/skills/modality registry now document the resume/pause workflow.

## [0.26.2] - 2026-08-07



### Added
- Config Studio display options (session-only): hide unassigned fields, list headers, element numbering, type labels (all default off); optional bottom YAML preview (default hidden); left chevron tree expand.
- New `metagit-stamp` skill for idempotent non-umbrella manifest stamping on target folders (local or git-backed).

### Fixed
- Global CLI `-c` detects `.metagit.yml` workspace manifests and loads bundled AppConfig while exposing `definition_path` on the Click context.
- FuzzyFinder non-preview mode uses full-width results (fixes empty project list in `metagit nav`).
- FuzzyFinder quit keys (`Ctrl+C`, `Esc`, `Ctrl+Q`) use priority bindings and treat `KeyboardInterrupt` as cancel so stuck pickers can exit.
- FuzzyFinder `get_item_opacity` no longer references nonexistent `self.config` (emptied `metagit nav` project list for string items).
- `metagit nav` expands `~` in `-c` manifest paths, homes relative `workspace.path` to the manifest directory, and honors global `-c` definition_path.
- AppConfig loading and `metagit appconfig validate` now reject unknown non-schema keys while still normalizing legacy `version` and `default_profile` metadata.
- Windows nav test coverage now seeds `USERPROFILE`/`HOMEDRIVE`/`HOMEPATH` alongside `HOME` so `Path("~")` expansion is deterministic in GitHub Actions.
- TUI project/repo pickers now initialize `ListView` selection index to the first row before focus, fixing Enter-key no-op transitions seen on Windows (`ProjectSelectScreen` staying active instead of pushing `RepoSelectScreen`).
- Project repo entries now enforce a single locator (`path` or `url`, not both), and metagit skill docs were updated to document that exact-one rule.
- Regenerated `schemas/metagit_config.schema.json` and `schemas/metagit_appconfig.schema.json` after skills/schema sync to keep generated artifacts current.
- Graph suggestion and GitNexus group-sync test fixtures now comply with the single-locator repository rule, preventing CI regressions from legacy dual-locator test data.
- Cross-project dependency service fixtures now use path-only repos under the single-locator rule while preserving declared/import edge coverage.
- Workspace health service fixtures now use path-only repos under the single-locator rule, fixing failing health-check unit coverage.
- Additional web/index/search/documentation test fixtures now avoid dual `path`+`url` repo definitions so CI reflects the enforced single-locator contract.

## [0.26.0] - 2026-08-04



### Changed
- Raise `aiohttp` floor to `>=3.14.3` and lock `pymdown-extensions` to `11.0.1` for current advisories.

### Added
- `metagit nav` / `metagit navigate`: FuzzyFinder project pick then repo pick, then open the configured editor.
- `metagit context switch`: agent bootstrap composing project context switch, tiered pack, `context-switch` prompt, and objective; shell-evalable exports by default (`--json` for full envelope).
- Prompt kind `context-switch` for mid-session workspace bootstrap (cold start remains `session-start`).
- MCP tool `metagit_context_switch` returning the same bootstrap envelope; lean `metagit_project_context_switch` unchanged.
- Docs: `docs/reference/context-switch.md` (tag conventions for `hermes_profile`, `working_dir`, `default_task_namespace`).

## [0.25.0] - 2026-08-03



### Added
- **Central state plane (RFC-0015):** pluggable `DocumentStore` with memory/local/http adapters and optional DynamoDB/MongoDB extras; extended `state` app-config and `gate/status` diagnostics; see `docs/reference/central-state-plane.md`.

### Changed
- **Coordination backend resolution:** `resolve_backend()` routes local and HTTP (as well as memory/DynamoDB/MongoDB) through `resolve_document_store()` + `coord_bundle` DocumentStore adapters; legacy `local_bundle` / `remote_bundle` remain available for direct callers and contract tests.

### Fixed
- **Ops whole-document state (Deployment B):** `OpsWebHandler` GET/PUT for objectives/handoffs/approvals (and handoff append) now uses `resolve_backend()` so DynamoDB/MongoDB/HTTP/memory DocumentStore planes are honored instead of always reading local files.
- **HTTP handoff append:** coord `_HandoffsAdapter.append` returns the server-normalized body from `DocumentStore.append` when it includes `id` (parity with prior `RemoteHttpBackend.append_handoff`).
- **Local document store hardening:** reject unsafe namespace/key paths, replace locked JSON files atomically, prevent mutations of the derived coordination events document, derive `get()` bodies and CAS tokens from one byte snapshot, and cold-import without the context/state cycle.
- **State identity cold imports:** organization/workspace identity helpers now live in an independent state module, avoiding the `state.base` ↔ `context` package initialization cycle.
- **Dependency security baseline:** require GitPython 3.1.55 and pymdown-extensions 11.0.0 or newer to resolve advisories reported by the pre-push audit.

## [0.24.0] - 2026-07-28



### Added
- **Manifest-homed workspace root:** when `-c` / `--config-path` targets a `.metagit.yml` outside the cwd, relative `workspace.path` resolves against that manifest’s directory (`resolve_workspace_root`) for `config graph suggest|export`, `workspace`, `project`, `prompt`, `skills`, and `gitnexus group sync`. JSON suggest output includes `workspace_root`.
- **`metagit config graph suggest|export`:** accept a leaf `--config-path/-c` (overrides the `config` group's manifest path); `suggest` gains `--verbose` for a logger-emitted summary (roots, candidate counts, prune stats) even with `--json`. `GraphSuggestResult.scan_stats` aggregates `ImportHintScanner` walk stats (`dirs_pruned`, `files_skipped_gitignore`, `files_yielded`), de-duplicated by repo path so a workspace repo is counted once no matter how many projects are scanned.
- **`metagit config graph suggest`:** report-only `GraphSuggestResult.stale_manual[]` flags active manual `graph.relationships` entries with no supporting inferred edge in the current scan (deprecated edges excluded; support is matched on endpoints, so a differing relationship type does not flag an edge); `graph-discover`/`graph-maintain` prompts, the `metagit-graph-maintain` skill, and `docs/reference/metagit-config.md` document the `status`/`provenance` lifecycle and the report-only `stale_manual` review step.
- **Ignore-aware recursive scanning:** new `metagit.core.utils.repo_walk.iter_repo_files()` always prunes the shared scaffold denylist (`SCAFFOLD_PATH_SEGMENTS`, moved to `metagit.core.utils.scaffold_paths`) and honors nested per-directory `.gitignore` files (git-scoped, pruned during the walk, not post-filtered), including `!pattern` negations. `ImportHintScanner._scan_terraform_modules` now uses this walker instead of unbounded `Path.rglob("*.tf")`, exposing per-scan `last_walk_stats`; `WorkspaceSearchService` imports the shared scaffold constant.
- **Durable `graph.relationships`:** `GraphRelationship` gains `status: Literal["active","deprecated","proposed"]` and `provenance: Literal["manual","promoted","imported"]` (both default consistent with existing manual entries); new `graph_validation.validate_graph_relationships()` requires a non-blank `id` and checks `from`/`to` endpoints against `workspace.projects[].repos`. `suggest --apply` validates the patched document (the exact model that would be written) and reports `validation_errors` instead of writing on failure.

### Changed
- **`metagit config validate` now exits 1 on invalid `graph.relationships`.** Manifests whose relationships lack an `id` or reference unknown projects/repos previously validated cleanly. *Migration:* add `id:` to existing `graph.relationships[]` entries and correct any endpoint that does not resolve to a `workspace.projects[].repos` entry.
- **`metagit config graph suggest` default output is a human summary** (counts plus a short candidate list) instead of a raw JSON dump, and no longer includes `operations`. *Migration:* pass `--json` for the previous machine-readable payload.
- **`graph.relationships[]` are written with the `from:` alias and explicit `status:`/`provenance:`.** Manifests previously round-tripped the internal `from_endpoint:` key, which fails `schemas/metagit_config.schema.json`. Both spellings still load; re-saving a manifest normalizes it to `from:`.

### Fixed
- **`iter_repo_files` gitignore precedence:** `.gitignore` rules are now evaluated in file order with last-match-wins, and a deeper directory's `.gitignore` overrides its ancestors' rules — matching `git check-ignore` instead of letting any ancestor `!` negation unconditionally beat a later deny pattern.
- **`metagit config graph suggest --apply`:** applying to a manifest with no `graph:` section no longer writes a placeholder `example-value` relationship that made the following `metagit config validate` fail. Promotion now issues a single `set graph.relationships` carrying the complete list, rebuilt from the manifest on disk.
- **`metagit config validate`:** graph and `agent_profile` rejections no longer print a misleading "Failed to load metagit configuration file:" line after the real reason.
- **Terraform import scanning:** `iter_repo_files` filters on `suffix` before running gitignore checks and caches each directory's ancestor rule chain, removing a large regression on repos with many non-matching files. `files_skipped_gitignore` / `files_skipped_scaffold` now count only suffix-matching files.
- **`metagit config example`:** generate valid values for `Literal`-typed fields (e.g. `graph.relationships[].status`/`provenance`) instead of a placeholder string, so the generated exemplar validates against `MetagitConfig`.

## [0.23.3] - 2026-07-17



### Fixed
- **`metagit skills install --scope project` / `metagit mcp install --scope project`:** resolve project-local destinations against the nearest git repository root (not a nested cwd), so installs from subdirectories land in `.cursor/skills`, `.claude/skills`, etc. at the repo root.
- **Hermes targeting:** honor `HERMES_HOME` (default `~/.hermes`) for `--target hermes` skills; write MCP into `$HERMES_HOME/config.yaml` under `mcp_servers` (not ignored `~/.config/hermes/mcp.json`); launch via the installed `metagit` binary (not `uvx metagit-cli`) and set `METAGIT_AGENT_MODE=true` on the Hermes MCP env block.
- **MCP stdio handshake:** speak newline-delimited JSON per the MCP stdio transport spec (accept legacy `Content-Length` frames on read). Fixes hangs where standard NDJSON clients never received an `initialize` response.

## [0.23.2] - 2026-07-16



### Changed
- Merge pull request #70 from metagit-ai/fix/mcp-stdio-stdout-pollution (6a5d818)
- fix(logging): route console sink to stderr so MCP stdio stays clean (ba58c1c)

## [0.23.1] - 2026-07-14



### Fixed
- **`metagit atlas validate`:** ship Atlas JSON Schemas under `metagit/data/schemas/atlas/` so installed wheels resolve schemas without the repo-root `schemas/atlas/` tree (fixes `FileNotFoundError` on PyPI 0.22.0).

## [0.23.0] - 2026-07-14



### Added
- **Derived projects:** `metagit project derived create|refresh|include|exclude` creates surgical `workspace.projects[]` subsets in the same umbrella manifest with frozen membership, `derived_from` provenance, and refreshable identity; default per-project dedupe shares sync mounts with source repos. MCP `metagit_project_derived_*`; docs `docs/reference/derived-projects.md`; example `examples/derived-workspace/`.
- **Skills surface:** `metagit skills surface` and MCP `metagit_skills_surface` inventory on-disk vendor skills plus declared `agent_profile.skills` across workspace/project/repo scopes; docs `docs/reference/skills-surface.md`.

## [0.22.0] - 2026-07-14



### Added
- **RFC-0014 Metagit Atlas (Phase 0–1 local MVP):** repository-local `.atlas/` schema and generated evidence with `metagit atlas init|generate|validate|status|query|refresh`; deterministic inventory, Python symbol, and test discovery; curated entity validation and local query index. MCP, federation, and optional adapters remain deferred.
- **TUI project → repository path:** home screen leads with in-app project then repo selection (auto-skips project pick for single-project manifests) without nested fuzzy finder suspend.

### Fixed
- **TUI quit/suspend noise:** quit bindings use priority `action_quit`; `KeyboardInterrupt` during teardown is swallowed; legacy interactive suspend failures notify in-app instead of dumping a traceback.
- **TUI repository picker:** Workspace “Select project → repository” now uses the in-app project/repo screens (no nested fuzzy suspend that appeared to do nothing).
- **`metagit project list`:** defaults to a workspace-style project catalog (definition/root/counts); use `-p`/`--detail` for single-project YAML.

## [0.21.1] - 2026-07-13



### Changed
- Merge pull request #66 from metagit-ai/cursor/rfc-0013-aos-plan-expansion (f4a14ed)
- Merge pull request #65 from metagit-ai/feat/rfc-0013-aos (482dfb3)
- docs(mex): refresh AOS, scheduler, and ACL series patterns (129de27)
- docs: expand RFC-0013 AOS composition design and TDD plan (28a3cd6)

### Fixed
- fix: merge updates (8d140fe)
- fix: update from last week (968f281)

## [0.21.0] - 2026-07-10



### Added
- **RFC-0013 Agent Operating System (composition):** thin `AosService` aggregates ACL, task graph, and optional 0009–0012 subsystems; CLI `metagit aos|coord status|doctor|next`; ACTIVE-gated `metagit_aos_*` / `metagit_coord_*` MCP tools; `SchedulerService.preview_next` for non-persisting peeks; modality `aos_status`.

## [0.20.0] - 2026-07-10



### Added
- **RFC-0012 Distributed Agent Scheduler:** `SchedulerService` scores ready task-graph nodes using priority, worktree affinity, token-cost heuristics, optional fairness, and soft merge-queue backpressure; persists `.metagit/schedule/{policy.json,decisions.jsonl}` and emits `source=scheduler` events.
- **RFC-0012 schedule CLI/MCP parity:** `metagit schedule policy show|set`, `metagit schedule next`, `metagit schedule status` plus ACTIVE-gated `metagit_schedule_next|status|policy` tools register the `agent_scheduler` modality markers.
- **RFC-0012 operator surface:** published agent scheduler reference, MkDocs nav entry, and agent quick-reference commands; additive optional `TaskNode.priority` / `estimated_tokens` fields.

### Fixed
- **Security:** bump transitive `soupsieve` to 2.8.4 (CVE-2026-49476 / CVE-2026-49477).
- **Bandit:** annotate intentional `shell=True` in merge validators (`nosec B602`) for opt-in platform-shell commands.

## [0.19.0] - 2026-07-09



### Added
- **RFC-0010 Semantic Repository Knowledge Graph:** `SemanticGraphService` can declare concept ownership, query concepts by id/name/alias, resolve path owners with ACL pattern overlap semantics, and emit `ConceptDeclared` events.
- **RFC-0010 SemanticGraphService:** advisory `conflicts(repository)` hints detect when multiple active ACL claim agents overlap the same semantic concept paths and emit `ConceptConflictHint` events.
- **RFC-0010 ACL claim advice:** `metagit claim check` / MCP claim checks now include advisory semantic `concept_hints` for overlapping concept ownership patterns without turning hints into claim conflicts.
- **RFC-0010 context events:** `metagit context events` now includes semantic graph lifecycle events with `source=semantic`.
- **RFC-0010 semantic CLI:** `metagit semantic declare|query|owners|conflicts|ingest|seed` exposes semantic concept ownership operations, including deterministic ingest hints and the optional seed catalog.
- **RFC-0010 semantic MCP parity:** ACTIVE-gated `metagit_semantic_declare|query|owners|conflicts|ingest` tools mirror the semantic service and register the `semantic_ownership` modality markers.
- **RFC-0010 semantic operator surface:** published semantic ownership reference, MkDocs nav entry, and agent quick-reference commands for CLI/MCP use; optional GitNexus import is documented as deferred.
- **RFC-0011 Merge Orchestrator:** local merge requests, JSON queue/store, clean GitPython conflict aborts, conflict records with ACL command hints only, opt-in validator commands, gated promote, and `source=merge` events.
- **RFC-0011 merge CLI/MCP parity:** `metagit merge enqueue|status|integrate|retry|promote` plus ACTIVE-gated `metagit_merge_enqueue|status|integrate|retry` MCP tools share `MergeOrchestrator` and register the `merge_orchestrator` modality markers.
- **RFC-0011 merge operator surface:** published merge orchestrator reference, MkDocs nav entry, agent quick-reference commands, bundled skill markers, and ACL series status updates.

### Changed
- Expanded **RFC-0010 Semantic Repository Knowledge Graph** design decisions and bite-sized TDD implementation plan under `docs/superpowers/` (next ACL series MR after 0008/0009).

### Fixed
- **RFC-0011 merge validators:** run opt-in command strings via the platform shell (`shell=True`) so Unix CI uses `/bin/sh` and Windows CI uses `ComSpec`, instead of hardcoding `/bin/zsh` or `/bin/sh`.
- **RFC-0010 SemanticGraphService:** `declare()` now returns validation errors for bad repositories or empty patterns instead of raising, preserving the service `T | Exception` contract.

## [0.18.1] - 2026-07-09



### Fixed
- **Docs CI (`mkdocs build --strict`):** replace relative links from `docs/metagit-rewrite-workspace.md` to `examples/metagit-rewrite/*` with GitHub blob URLs so MkDocs no longer aborts on out-of-tree targets.

## [0.18.0] - 2026-07-09



### Added
- **RFC-0009 Agent Context Compiler:** `metagit context compile` CLI + MCP `metagit_context_compile`; `ContextCompiler` reuses context-pack tiers with char/4 budget; artifacts under `.metagit/context/compiled/` or `.metagit/tasks/<graph>/context/`; stamps task node `compiled_context_path` / `context_budget`; `ContextCompiled` events (`source=context`). Docs: `docs/reference/context-compiler.md`.
- **RFC-0008 Task Graph & Intent Engine:** `metagit task` CLI (`create`, `expand`, `list`, `status`, `ready`, `start`, `block`, `complete`, `bind-acl`), MCP tools (`metagit_task_*`), persistence under `.metagit/tasks/`, lifecycle events in `metagit context events` (`source=taskgraph`), and ACL command hints without auto-running git. Docs: `docs/reference/task-graph.md`.

## [0.17.0] - 2026-07-09



### Added
- **RFC-0007 Agent Coordination Layer (foundation):** `metagit branch|lease|worktree|claim` CLI groups, MCP tools (`metagit_branch_*`, `metagit_lease_*`, `metagit_worktree_*`, `metagit_claim_*`), local persistence under `.metagit/{branches,leases,worktrees,claims,agents,events}/`, isolated checkouts under configurable `workspace.worktrees_path` (default `.worktrees/`, env `METAGIT_WORKSPACE_WORKTREES_PATH`), advisory file claims and repo presence, agent execution manifests on worktree create, ACL events in `metagit context events` (`source=acl`), and dispatch-plan `acl_commands` hints. Docs: `docs/reference/agent-coordination.md`. Bundled skill **`metagit-agent-coordination`**. Agent onboarding indexes (`llms.txt`, `AGENTS.md`, `docs/cli_reference.md`) list ACL commands and MCP tools. Worktrees/campaigns path basenames are reserved project names.
- **ACL RFC series build specs (0008–0013):** design + implementation plan per RFC under `docs/superpowers/`, indexed by `docs/superpowers/specs/2026-07-09-acl-rfc-series-index.md` (0008 fuller plan; 0009–0013 phased; 0013 composition-only).

### Fixed
- **PYTHONPATH shadowing:** `metagit/__init__.py` now prepends the interpreter's own `site-packages` (`sysconfig` purelib) before any other imports so a caller-injected `PYTHONPATH` (e.g. Hermes embedding metagit) cannot load a foreign `pydantic` and crash with `ModuleNotFoundError: pydantic_core._pydantic_core`. Does not clear or rewrite the `PYTHONPATH` env var.

## [0.16.0] - 2026-07-07



### Fixed
- **`metagit tui`:** remove the Context & agents command group from the hub menu; fix repository picker `RuntimeError: asyncio.run() cannot be called from a running event loop` by running nested Textual fuzzy finder apps in a worker thread when the hub already owns an asyncio loop.

### Added
- **Reference rewrite workspace:** `metagit-rewrite` init template, `examples/metagit-rewrite/` manifest with campaign and parity-registry conventions, `docs/metagit-rewrite-workspace.md`, bundled skill **`metagit-rewrite-campaign`** (orchestrator loop + script), and repomix profiles `rewrite-source` / `rewrite-target`.

## [0.15.1] - 2026-07-07



### Fixed
- **Test suite env independence:** an autouse fixture now clears `METAGIT_AGENT_MODE` before each test so a value exported in the caller's shell (common in agent/automation shells) can't disable interactive paths and cause spurious failures in CLI picker and appconfig-display tests. Tests needing the variable set it explicitly.

## [0.15.0] - 2026-07-07



### Added
- **Campaign schema superset:** `CampaignDocument` gains optional `goal`, `reference_impl`, `created`, and `updated` fields; `campaign new` accepts an explicit `--repo project/repo` (repeatable, frozen set — no query drift) as an alternative to `--query`, plus `--goal` and `--reference`; `campaign status` surfaces goal/reference.
- **Legacy overlay compatibility:** campaign documents authored before the native schema now load without a rewrite — integer `schema_version`, `status: complete` (→ `completed`), and list-form `selection.tags` (→ map) are coerced on load. Point native at an existing overlay dir via `workspace.campaigns_path` / `METAGIT_WORKSPACE_CAMPAIGNS_PATH`.

## [0.14.1] - 2026-07-07



### Changed
- Merge pull request #55 from metagit-ai/cursor/fix-docs-ci-modality-registry-links (85572c2)

### Fixed
- fix: repair modality registry link for MkDocs strict CI (8252d20)

## [0.14.0] - 2026-07-06



### Added
- **`agent_profile`:** structured inheritable blocks on `workspace`, project, and repo scopes (`skills`, `mcp`, `rules`, `vendors`, `tier`, `inherit`); `metagit agent profile show` and `metagit agent apply`; catalog validation in `metagit config validate`
- **Native campaigns:** `metagit campaign list|status|new|validate|set|expand` with diffable YAML under configurable `workspace.campaigns_path` (default `_campaigns/` at manifest root)
- **Multi-agent coordination:** handoff claim `--ttl`, `metagit context handoff heartbeat`, auto-release of expired claims; campaign/objective filters on `metagit context events`; objective `mr_url` and `approval_id` fields; capability hints on `agent dispatch-plan` from merged profiles
- **Modality registry:** master feature matrix in `docs/reference/modality-feature-registry.md` (from `scripts/modality-parity.yml`); reference docs `agent-profile.md`, `campaigns.md`; bundled skills `metagit-campaign` + updated `metagit-cli`, `metagit-context-pack`, `metagit-control-center`

## [0.13.0] - 2026-07-01



### Fixed
- **Repository Terrain:** detail panel state labels include branch name for non-default git states

### Added
- **Repository Terrain:** Three.js 3D operational map at `/terrain` — tiles encode git state (flat green synced main, bulge for local/unpushed work, depression when behind remote, branch colors); progressive load, per-project filter, layout modes, visual styles; `GET /v3/ops/terrain`

## [0.12.0] - 2026-07-01



### Added
- **Remote state backend:** pluggable `core/state/` package with `LocalFileBackend` (file locking + SHA-256 CAS tokens) and opt-in `RemoteHttpBackend` (stdlib `urllib`, `If-Match`/`ETag`); `state` app-config block and `METAGIT_STATE_*` env vars; whole-document ops routes; MCP `gate/status` `state_backend` diagnostics; events via `resolve_backend()`; skill `metagit-sharing-state`; docs at `docs/reference/sharing-state.md`

### Fixed
- **Windows CI:** guard optional `fcntl` import in `LocalFileBackend` so state modules load on platforms without advisory file locks
- **Windows state tokens:** write state JSON with `write_bytes` so CAS tokens match on-disk bytes (avoid CRLF translation from `write_text`)

## [0.11.0] - 2026-06-26



### Added
- **MCP layered resources (Phases 1–4):** token-efficient `resources/read` ladder (`metagit://catalog`, map, session/digest, objectives, approvals/pending, handoffs/open, events/recent, layered prompts, project/repo drill-down); MCP `prompts/list` + `prompts/get`; `handoff.mcp_resources` on dispatch plans; spec at `docs/reference/mcp-layered-resources-spec.md`; skill `metagit-mcp-resources`
- `metagit tui`: Textual hub to browse common CLI workflows, run commands, and configure `metagit.config.yaml` via an interactive wizard (`--wizard` opens the wizard directly)

### Fixed
- `metagit tui`: Esc/Back navigation on list screens; wizard Back button; correct manifest flags per CLI group (`workspace` uses `--config`, not `-c`); repo picker runs in-process with terminal suspend instead of hanging in a captured subprocess

## [0.10.0] - 2026-06-26



### Added
- Ops API session endpoints: `GET /v3/ops/session` (digest with `active_objective_id` + repo changes) and `POST /v3/ops/session/begin` (session bootstrap envelope)
- MCP parity tools for objective/session collaboration: `metagit_objective_edit` (partial objective updates) and `metagit_session_digest` (current session digest)

### Changed
- `PATCH /v3/ops/objectives/{id}` now supports partial edits of objective fields (`title`, `acceptance`, `human_notes`, `agent_notes`, `repos`, `status`) while preserving status-only behavior
- The web `/agents` route now includes `Templates`, `Objectives`, and `Sessions` sub-tabs with live refresh controls, collaborative objective editing, and a session digest/begin-session dashboard
- The web Objectives panel now supports inline status changes, a toggleable grouped/list layout, and per-row save actions; the CI/CD dashboard now understands SCP/SSH Git remotes and shows safe provider token metadata when the remote API exposes it

## [0.9.1] - 2026-06-24



### Changed
- Merge pull request #48 from metagit-ai/zloeber/web_cicd_feature (6c9958f)
- Merge remote-tracking branch 'origin/main' into zloeber/session_path (61104df)
- chore(skills): sync copilot skill assets and agent scaffolding (56de31d)
- feat(web,ops): add live CI/CD pipeline dashboard and status API (35c6cc6)

### Fixed
- fix: update local metagit for testing, accuracy (462a82f)

## [0.9.0] - 2026-06-23



### Added
- `metagit context session begin` and MCP `metagit_session_begin`: single-call deterministic session bootstrap envelope (pack, prompt, objectives, approvals, session metadata)
- `context pack --max-tokens`: greedy token-budgeted packer with `dropped_sections` explanation
- `schema_version: "1.0"` on all `--json` output and MCP tool responses
- Stable exit code constants (`NO_WORKSPACE`, `STALE_INDEX`, `LOCK_CONTENTION`, `NEEDS_APPROVAL`) in `cli/exit_codes.py`
- First-class handoff API: `metagit context handoff create|list|claim|complete` (CLI + MCP) with append-only audit trail
- Approval idempotency key support (`--idempotency-key` / `idempotency_key` MCP arg)
- `metagit context objective export|import` for portable, redaction-safe intent transfer
- Incremental workspace event feed: `metagit context events --since <cursor>` (CLI + MCP `metagit_events`) with `next_cursor` for polling
- `workspace.session_path` config key + `METAGIT_WORKSPACE_SESSION_PATH` env override for configurable session storage
- Live CI/CD status dashboard in the web workspace with provider/status/project filtering and periodic refresh
- Ops API endpoints for pipeline provider diagnostics and live pipeline status aggregation via `PipelineStatusService`

### Security
- Bump `aiohttp` override floor to `>=3.14.1` (fixes CVE-2026-54273 through CVE-2026-54280)
- Bump `msgpack` override floor to `>=1.2.1` (fixes GHSA-6v7p-g79w-8964)


## [0.7.0] - 2026-06-16


### Added

- **`metagit project source sync` enhancements:** include/ignore glob filters, `--ensure` / `--refresh-metadata` idempotency, provider topic enrichment into repo tags, default `namespaced` GitLab naming, `--json` agent output, `--sync` post-apply clone, MCP `metagit_project_source_sync`, `metagit workspace import` alias, declarative `workspace.projects[].sources[]` with `--from-manifest`, and approval-gated reconcile removals. **Web parity:** Config Studio `sources[]` editing, Workspace Console manifest sync (`POST /v3/ops/source-sync`), pending approvals panel, and shared `ApprovalResolveOrchestrator`.
- **Modality parity gate:** `scripts/modality-parity.yml` + `scripts/check_modality_parity.py` (wired into `task qa:prepush`) enforce declared CLI/MCP/web markers for operator-facing features.
- **`metagit version check`:** CLI and MCP `metagit_version_check` compare the installed package to the latest GitHub release (notes) and PyPI; available without an active workspace gate. Use `--json` or `include_notes: false` for agent-friendly output.
- **`metagit version upgrade`:** CLI and MCP `metagit_version_upgrade` detect the install channel (`uv tool`, `pip`, editable) and plan or run a self-update from PyPI. Defaults to dry-run; pass `--apply` or `apply: true` to execute. Refuses editable development installs.
- **Agent onboarding:** `llms.txt`, [docs/agents.md](agents.md), and README/AGENTS.md sections so agents landing on the GitHub repo can install and use Metagit with minimal tokens (context packs, skills, MCP).
- **`metagit-agent-access` skill:** On-demand optimizer (script + subagent prompt) to scaffold `llms.txt`, `AGENTS.md`, and hidden README HTML agent blocks for any repository.
- **Context packs Phase 2:** tier **2** session digest (`SessionDigestService`), workspace **objectives** (CLI/MCP/Web), **approval queue** for mutating ops, and **repomix context profiles** (`bugfix-local`, `config-edit`, `cross-repo-impact`) via `metagit context repomix` and `task repomix:profile`.
- **Context packs Phase 1:** tier 0 workspace map and tier 1 repo cards via `metagit context pack`, MCP `metagit_context_pack` / `metagit_repo_card`, and prompt kind `context-pack`.
- **Repomix context profiles:** `src/metagit/data/context_profiles.yaml` bundles scoped globs; `RepomixProfileService` runs `repomix --include/--ignore` for a repository directory.
- Top-level **graph** block for manual cross-repo **relationships** (merged into cross-project dependency maps and `graph_export_payload()` for GitNexus-style exports).
- Per-project `dedupe.enabled` override on `workspace.projects[]` in `.metagit.yml` (overrides app-config `workspace.dedupe.enabled` for sync and layout under that project).
- `metagit prompt` kind `repo-enrich` (repo scope): CLI workflow to discover repo metadata (`metagit detect`, `project source sync`) and merge into the workspace manifest entry.
- Bundled skill `metagit-cli`: CLI-only shortcuts for agents, including every `metagit prompt` kind and common catalog/detect/sync commands (no MCP or HTTP API).
- `metagit prompt` command group: `list`, `workspace`, `project`, and `repo` subcommands emit built-in operational prompts or composed manifest `agent_instructions` (`--kind`, `--json`, `--text-only`).
- Top-level `agent_mode` in app config (default false), overridable via `METAGIT_AGENT_MODE`; disables interactive UIs (fuzzy finder, prompts, editor, prune confirms) across CLI when enabled.
- `metagit appconfig show` prints the full active configuration with `--format yaml|json|minimal-yaml` (includes `workspace.dedupe` and effective `agent_mode`).

### Added

- `metagit project sync --hydrate` materializes symlink mounts into full directory copies with per-file tqdm progress.

### Changed

- `workspace.dedupe.enabled` defaults to **false** in app config; enable in `metagit.config.yaml` or per-project `dedupe.enabled` in `.metagit.yml` when canonical checkouts are desired.
- `load_config()` applies environment variable overrides (same as `AppConfig.load()`), including `METAGIT_AGENT_MODE` and `METAGIT_WORKSPACE_DEDUPE_ENABLED`.
- `metagit config show` prints the source `.metagit.yml` by default (preserves your formatting); use `--normalized` for a readable model round-trip (`|` blocks, Unicode not escaped) or `--json` for agents.

### Added

- Workspace layout rename/move: rename projects and repos (manifest + sync folders), move repos across projects; CLI (`workspace project rename`, `workspace repo rename|move`), MCP (`metagit_workspace_project_rename`, `metagit_workspace_repo_rename`, `metagit_workspace_repo_move`), HTTP v2 (`POST /v2/projects/{name}/rename`, `/v2/repos/.../rename|move`). Supports `--dry-run`, `--manifest-only`, dedupe symlink mounts, and session file migration on project rename. See `docs/reference/workspace-layout-api.md`.
- Workspace catalog CRUD with JSON output: CLI (`metagit workspace list|project|repo`, `metagit project list --all`, `project add|remove`, `project repo list|remove`, `--json` on catalog commands), MCP tools (`metagit_workspace_list`, `metagit_workspace_projects_list`, `metagit_workspace_project_add|remove`, `metagit_workspace_repos_list`, `metagit_workspace_repo_add|remove`), and HTTP API v2 (`/v2/workspace`, `/v2/projects`, `/v2/repos`). Manifest-only repo/project removal; use `project repo prune` to delete unmanaged directories on disk.
- Docs: [Hermes agents and organization-wide IaC](hermes-iac-workspace-guide.md) — illustrated controller/subagent workflow, manifest examples, and MCP tool map for platform IaC estates.
- Layered `agent_instructions` on `.metagit.yml` (file, workspace, project, repo/path); legacy `agent_prompt` accepted on load. `AgentInstructionsResolver` composes stacks for MCP project context (`instruction_layers`, `effective_agent_instructions`, per-repo `agent_instructions`).
- MCP `metagit_workspace_semantic_search` runs GitNexus `query` per managed repo (requires registry + index) for vector-ranked process results.
- MCP `metagit_workspace_health_check` includes branch age (`head_commit_age_days`, `merge_base_age_days`) when `check_stale_branches` is enabled, with thresholds `branch_head_warning_days` / `branch_head_critical_days` / `integration_stale_days` and summary counters for stale HEAD and integration drift.
- MCP Phase 3 workspace intelligence: `metagit_workspace_health_check`, `metagit_workspace_discover`, and `metagit_project_template_apply` (dry-run by default), plus resources `metagit://workspace/health` and `metagit://workspace/context`.
- MCP `metagit_cross_project_dependencies` to map declared, import-hint, and shared-config relationships between workspace projects with GitNexus index status per repo.
- MCP Phase 1 search/sync improvements: `metagit_repo_search` filters (`status`, `has_url`, `sync_enabled`, `sort`), `metagit_workspace_search` ripgrep-backed hits with `repos`/`paths`/`exclude`/`context_lines`/`intent`, and batch `metagit_workspace_sync` with `only_if` and `dry_run`.
- MCP project context tools: `metagit_project_context_switch`, `metagit_workspace_state_snapshot`, `metagit_workspace_state_restore`, and `metagit_session_update` for switching workspace projects with persisted session state under `.metagit/sessions/` and git-state snapshots under `.metagit/snapshots/`.
- Managed repository search across `.metagit.yml` workspace repos: CLI (`metagit search` / `metagit find`), MCP tool `metagit_repo_search`, and local JSON HTTP API (`metagit api serve` with `/v1/repos/search` and `/v1/repos/resolve`).
- `metagit project repo prune` to review and remove sync-folder directories not declared in `.metagit.yml` (with `--dry-run`, `--include-hidden`, and `--force` to skip prompts).
- `workspace.ui_ignore_hidden` in app config (default true) to hide dot-directories from the repo picker UI.

### Changed

- Removed redundant `config.version` from application config; use `metagit version` for the installed package. Legacy `version` keys in YAML are ignored on load. `api_version` remains for a future remote API contract (default empty; `METAGIT_API_VERSION` still applies).

### Fixed

- Workspace search: preset names that map to intent globs (e.g. `terraform`) now pass `**/*.tf` include globs to ripgrep; if ripgrep returns no hits while a `preset` or `intent` is set, the term-based filesystem fallback runs so Ubuntu/CI still gets matches when `rg` is installed but misbehaves or misparses.
- Workspace search fallback without `rg` matches preset-expanded terms (e.g. `preset=terraform`) instead of treating the composed `|` pattern as one literal string; fixes empty results when ripgrep is not installed.
- `task test` now runs `uv run pytest` so tests use the project virtualenv (fixes `ModuleNotFoundError: loguru` when `pytest` was not the venv binary).

## [0.2.2] - 2026-05-06


### Bug Fixes

* revamp release workflow ([cafd6da](https://github.com/metagit-ai/metagit-cli/commit/cafd6dac4777c8528cc1c996bb8f1a394c40d53d))
