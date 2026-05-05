# Metagit Skills Index

This index maps Metagit skills to concrete MCP tool usage and reusable invocation prompts.

## Skills Overview

- `metagit-mcp-gating`: Enforce `.metagit.yml`-based activation and safe tool exposure.
- `metagit-mcp-bootstrap`: Generate/refine local `.metagit.yml` using deterministic discovery plus MCP sampling.
- `metagit-upstream-discovery`: Find likely upstream repositories/files for cross-repo blockers.
- `metagit-control-center`: Run Metagit as a multi-repo operational control plane for ongoing agent tasks.

## Local Agent Wrapper Scripts

Use these first for token-efficient automation:
- `skills/metagit-mcp-gating/scripts/gate-status.zsh`
- `skills/metagit-mcp-bootstrap/scripts/bootstrap-config.zsh`
- `skills/metagit-upstream-discovery/scripts/upstream-scan.zsh`
- `skills/metagit-control-center/scripts/control-cycle.zsh`

## Tool Mapping by Skill

### `metagit-mcp-gating`

**Primary MCP tools**
- `metagit_workspace_status`
- `metagit_bootstrap_config_plan_only`

**Secondary MCP tools (active state only)**
- `metagit_workspace_index`
- `metagit_workspace_search`
- `metagit_upstream_hints`
- `metagit_repo_inspect`
- `metagit_repo_sync`
- `metagit_bootstrap_config`

**When to use**
- Before enabling any mutation-capable operations
- When tool visibility should depend on `.metagit.yml` validity
- When debugging why a workspace appears inactive

**Prompt example**
```text
Use metagit-mcp-gating to verify whether this workspace is active. If inactive, tell me exactly why and what I should do next to activate it.
```

### `metagit-mcp-bootstrap`

**Primary MCP tools**
- `metagit_bootstrap_config`
- `metagit_bootstrap_config_plan_only`

**Supporting MCP capability**
- `sampling/createMessage` (when client supports MCP sampling)

**When to use**
- No `.metagit.yml` exists in a target workspace
- Existing `.metagit.yml` is incomplete or low quality
- You need discovery-driven config generation with schema validation feedback

**Prompt example**
```text
Use metagit-mcp-bootstrap to discover this repository and generate a draft .metagit.yml. Validate it and only write the final file if I confirm.
```

### `metagit-upstream-discovery`

**Primary MCP tools**
- `metagit_workspace_index`
- `metagit_workspace_search`
- `metagit_upstream_hints`

**Optional MCP tools**
- `metagit_repo_inspect`
- `metagit_repo_sync` (only when sync is required)

**When to use**
- A fix likely exists outside the current repository
- Terraform input/module mismatch appears upstream
- Docker base image or infrastructure issue is likely shared across repos

**Prompt example**
```text
Use metagit-upstream-discovery for this blocker: "terraform input var enable_private_endpoint is missing". Rank the most likely upstream repos and files to inspect first.
```

### `metagit-control-center`

**Primary MCP tools/resources**
- `metagit_workspace_status`
- `metagit_workspace_index`
- `metagit_workspace_search`
- `metagit_upstream_hints`
- `metagit_repo_sync`
- `metagit://workspace/config`
- `metagit://workspace/repos/status`
- `metagit://workspace/ops-log`

**When to use**
- Working on an objective spanning multiple repositories
- Maintaining ongoing operational awareness for long-running tasks
- Coordinating selective repo sync and issue triage

**Prompt example**
```text
Use metagit-control-center for this feature objective. Build a repo impact map, identify upstream dependencies, sync only repos required for implementation, and keep an operations trail.
```

## Suggested Invocation Patterns

- Start with `metagit-mcp-gating` in every new workspace session.
- If inactive, run `metagit-mcp-bootstrap` to produce a valid config baseline.
- For blockers that look external, switch to `metagit-upstream-discovery`.
- For sustained multi-repo development, use `metagit-control-center` as the default operating workflow.

## Safety Defaults

- Keep mutation operations disabled unless explicitly requested.
- Prefer `fetch` over `pull`/`clone` unless task context requires synchronization.
- Restrict search/sync scope to repositories declared in active workspace configuration.
