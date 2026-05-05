# Metagit MCP Gated Workspace and Upstream Discovery Design

## Goal

Build a Metagit MCP server that only exposes high-trust tooling and context when a valid `.metagit.yml` exists at the resolved workspace root. When active, it gives agents structured multi-repo awareness, guarded repository synchronization, and issue-driven upstream discovery to resolve cross-repository blockers.

## Scope

This design covers:
- Workspace gating and activation semantics
- MCP sampling-driven `.metagit.yml` bootstrap workflow
- Multi-repo awareness and search features for upstream issue resolution
- Safe repository sync and control-center-style operations
- Resources, observability, and safety controls

This design does not cover:
- Full semantic/embedding index implementation
- Remote orchestration beyond local filesystem and git access
- Automatic writes to unrelated repos without explicit approval

## Architecture

The feature is implemented as a new MCP server runtime exposed from metagit CLI:
- `metagit mcp serve` (stdio mode first)
- Shared config loading through existing Metagit config and workspace models
- Tool registration controlled by a runtime gate that validates `.metagit.yml`

Core layers:
1. **Workspace Resolver**: Determines effective root from `METAGIT_WORKSPACE_ROOT`, CLI `--root`, or upward directory walk.
2. **Config Gate**: Loads and validates `.metagit.yml`; emits active/inactive status.
3. **Tool Registry**: Registers only safe baseline tools when inactive; full toolset when active.
4. **Workspace Services**: Repo inventory, search, sync orchestration, and upstream hinting.
5. **Sampling Orchestrator**: Uses MCP `sampling/createMessage` for config generation and refinement.
6. **Resource Publisher**: Exposes workspace snapshots and diagnostics as MCP resources.

## Activation and Gating Rules

### Root Resolution
Order of precedence:
1. `METAGIT_WORKSPACE_ROOT`
2. `metagit mcp serve --root <path>`
3. Walk up from process working directory until `.metagit.yml` is found

### Activation States
- **inactive_missing_config**: no `.metagit.yml` found
- **inactive_invalid_config**: file present but fails parse/validation
- **active**: valid config loaded and normalized

### Tool Exposure Policy
When inactive, expose only low-risk introspection tools:
- `metagit_workspace_status`
- `metagit_bootstrap_config_plan_only`

When active, expose full feature set:
- `metagit_workspace_status`
- `metagit_workspace_index`
- `metagit_workspace_search`
- `metagit_upstream_hints`
- `metagit_repo_inspect`
- `metagit_repo_sync`
- `metagit_bootstrap_config`

## MCP Sampling for `.metagit.yml` Generation

### Objective
Allow an agent to request high-quality local `.metagit.yml` generation from discovered project facts without requiring the MCP server to own model credentials.

### Workflow
1. `metagit_bootstrap_config` runs deterministic discovery over repository files and metadata.
2. Server composes strict instructions (schema requirements, output contract, discovery evidence).
3. Server calls MCP `sampling/createMessage` if client advertises sampling capability.
4. Generated YAML is validated against Metagit config models.
5. On failure, server issues bounded retry with validation feedback.
6. Successful output is returned as:
   - `draft_yaml` text
   - optional write target (`.metagit.generated.yml` by default)
   - optional explicit write to `.metagit.yml` only when `confirm_write=true`

### Discovery Inputs for Sampling Prompt
- Languages and frameworks inferred from source structure
- Dependency signals from lockfiles, build files, and package manifests
- CI/CD workflows and Docker image usage
- Terraform modules and provider usage
- Existing config fragments and workspace repo hints

### Sampling Fallback
If client lacks sampling support:
- Return the exact prompt package plus deterministic discovery summary
- Provide guided next action for manual generation path

## Upstream Issue Resolution and Workspace Discovery

### Objective
Help agents identify related repositories and likely root causes for blockers originating outside the current repo.

### Supported Use Cases
1. Missing Terraform variable/input in a shared module
2. Docker base image/version mismatch or policy conflict
3. Upstream infrastructure configuration mismatch
4. CI runner or reusable workflow issues in shared pipeline repos

### Proposed Tools

#### `metagit_workspace_index`
Returns normalized map of workspace projects and repos:
- resolved local path
- git remote URL
- branch and cleanliness
- sync policy and availability

#### `metagit_workspace_search`
Cross-repo text search with safe boundaries:
- scope: selected repos or all configured repos
- glob filters and max result caps
- presets: `terraform`, `docker`, `infra`, `ci`

#### `metagit_upstream_hints`
Issue-oriented ranking service:
- input: short blocker statement, optional files or stack trace
- output: ranked candidate repos, likely files, and rationale

#### `metagit_repo_sync`
Controlled synchronization:
- modes: `fetch`, `pull`, `clone`
- default safe mode: `fetch`
- mutating modes require explicit allow controls

## Resource Surface

Expose these MCP resources when active:
- `metagit://workspace/config` (sanitized active configuration)
- `metagit://workspace/repos/status` (repo snapshot)
- `metagit://workspace/last-search` (most recent search summary)
- `metagit://workspace/ops-log` (bounded operational event log)

## Security and Safety

- No full toolset when gate is inactive
- Mutations disabled by default (`pull`, `clone`, writes)
- Mutations require explicit env toggle and tool parameter confirmation
- Path validation ensures all operations stay within configured repo boundaries
- Secret-like values in generated YAML are redacted or represented as placeholders
- Strict timeout and result-size caps for cross-repo searches

## Operational Knowledge and Control Center Behavior

The MCP server should maintain lightweight operational memory for the current workspace:
- recent repo sync events
- recently searched issue patterns and targeted repos
- unresolved upstream blockers tagged by category

This memory remains local and bounded, and is surfaced as resources/tools for ongoing agent sessions.

## Testing Strategy

### Unit Tests
- root resolution precedence
- inactive vs active tool registry behavior
- sampling prompt packaging and retry handling
- repo boundary validation and sync mode guards

### Integration Tests
- temporary multi-repo workspace with synthetic `.metagit.yml`
- Terraform/Docker/infra upstream issue scenarios
- search ranking sanity checks

### Contract Tests
- MCP tool schema stability
- resource payload schema snapshots

## Rollout Plan

1. Ship gating + workspace status + index
2. Add workspace search and upstream hints
3. Add sampling bootstrap (plan-only fallback first)
4. Add guarded sync mutations
5. Add operational memory resources

## Success Criteria

- Agent cannot invoke high-risk metagit tools unless `.metagit.yml` is valid and loaded
- Agent can generate a high-quality draft `.metagit.yml` from project discovery with sampling-enabled clients
- Agent can locate likely upstream repo/file candidates for Terraform, Docker, and infrastructure blockers within one workflow
- Sync actions remain explicit, auditable, and safe by default
