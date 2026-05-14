# Managed repo search design

## Goal
Add a managed repository resolver to Metagit so users and agents can look up a repository that is already declared in `.metagit.yml`, confirm its current local sync status, and get the correct local path to work in.

This is not a general discovery feature. It is a fast, reliable way to answer a narrower question: "Which managed repo should I work in, and where is it on disk right now?"

## Scope
The first pass covers three surfaces:

- CLI: `metagit search` with `metagit find` as an alias
- MCP: a read-only tool that returns structured search results
- HTTP API: a small local JSON API for automation

The search corpus is limited to repositories already managed in `.metagit.yml`.

The search service matches against:

- workspace project name
- repo name
- repo URL
- configured repo path
- resolved local path
- metadata tags stored on the repo entry

The service also returns current repo status, especially whether the resolved local path exists and whether the repo is effectively synced and usable.

## Non-goals
- No live provider discovery during search
- No search across unmanaged filesystem repos
- No search across source-discovered repos that have not been written into `.metagit.yml`
- No broad code search or content search inside repositories
- No automatic repo selection when the result set is ambiguous

## Why this exists
Agents need a safe way to move from a task description to the correct local repository.

A typical example:

1. An agent is told to work on "abacus" and check a Terraform deployment path.
2. `metagit search abacus` returns one or more managed repo matches with project, repo, path, tags, and sync state.
3. The agent uses the returned local path to validate that it is in the right repo before making changes.
4. If a second managed repo is needed, such as a shared Terraform module, the agent searches again by repo name, source URL, configured path, or metadata tags.
5. The agent works in that target repo, submits a merge request, and waits for approval before continuing.

This workflow only works if search results are deterministic, explainable, and tied to the current local workspace state.

## Design summary
Introduce one shared core service for managed repo lookup and reuse it everywhere.

- CLI stays thin and prints either human-readable output or JSON
- MCP calls the same service and returns stable JSON
- HTTP API calls the same service and returns the same result shape

The shared service is responsible for:

- loading `.metagit.yml`
- enumerating managed repos
- resolving each repo's effective local path
- computing status fields from the local filesystem
- matching and ranking results
- returning clear reasons for each match

## Core data model

### Extend `ProjectPath`
Add a flat metadata tag map to `ProjectPath`.

Suggested field:

```python
tags: dict[str, str] = Field(default_factory=dict, description="Flat metadata tags")
```

This keeps tags generic and practical. They behave like AWS resource tags: string keys, string values, no nesting.

Examples:

```yaml
repos:
  - name: abacus-app
    path: services/abacus-app
    url: https://github.com/example/abacus-app.git
    tags:
      code: abacus
      domain: terraform
      env: dev
      team: platform
```

### Add runtime-only search models
Search output should not reuse raw config models directly. Add dedicated runtime models under a new module, likely `src/metagit/core/project/search_models.py`.

Suggested models:

- `ManagedRepoQuery`
- `ManagedRepoMatch`
- `ManagedRepoStatus`
- `ManagedRepoSearchResult`
- `ManagedRepoResolveResult`

Suggested `ManagedRepoMatch` shape:

```python
class ManagedRepoStatus(BaseModel):
  resolved_path: str
  exists: bool
  is_git_repo: bool
  sync_enabled: bool
  status: str  # synced | configured_missing | path_unresolved


class ManagedRepoMatch(BaseModel):
  project_name: str
  repo_name: str
  url: str | None = None
  configured_path: str | None = None
  tags: dict[str, str] = Field(default_factory=dict)
  status: ManagedRepoStatus
  match_reasons: list[str] = Field(default_factory=list)
  score: int
```

The status model is the safety layer. Agents should not act on `resolved_path` alone without also checking whether it exists and whether it looks like a git repo.

## Core service boundary
Add `src/metagit/core/project/search_service.py` with a single responsibility: search managed repos from config and resolve their local state.

Suggested public methods:

```python
def search(
  self,
  config: MetagitConfig,
  workspace_root: str,
  query: str,
  *,
  project: str | None = None,
  exact: bool = False,
  synced_only: bool = False,
  tags: dict[str, str] | None = None,
  limit: int = 10,
) -> ManagedRepoSearchResult:
  ...


def resolve_one(
  self,
  config: MetagitConfig,
  workspace_root: str,
  query: str,
  *,
  project: str | None = None,
  exact: bool = False,
  synced_only: bool = True,
  tags: dict[str, str] | None = None,
) -> ManagedRepoResolveResult:
  ...
```

### Reuse existing logic
`WorkspaceIndexService` already resolves repo paths from config and workspace root. Do not create a second competing path-resolution implementation.

Refactor path resolution into one shared helper or expand `WorkspaceIndexService` into a reusable repo-row builder. The search service should consume that shared representation.

That keeps `repo_path`, sync status, and existence checks consistent between MCP index output and managed repo search output.

## Matching rules
The search should be direct and predictable.

### Fields searched
- project name
- repo name
- full repo URL
- partial repo URL
- configured path
- resolved path
- tag keys
- tag values
- exact `key=value` tag filter pairs

### Ranking
Use a simple scoring system instead of fuzzy "AI-like" ranking.

Suggested precedence:

1. exact repo name match
2. exact project name match
3. exact URL match
4. exact configured or resolved path match
5. exact tag value match
6. partial repo name match
7. partial project name match
8. partial URL or path match
9. partial tag key or value match

Each match should include `match_reasons`, for example:

```json
[
  "repo_name:exact",
  "tags.code:exact",
  "project_name:partial"
]
```

This matters for agent workflows. If an agent picks the wrong repo, the result should make it obvious why that happened.

## CLI surface
Add a new top-level command module, likely `src/metagit/cli/commands/search.py`.

Register it in `src/metagit/cli/main.py`.

Expose `find` as an alias to the same handler.

### Commands

```bash
metagit search abacus
metagit find abacus
```

### Suggested options

```bash
metagit search <query>
  --project <name>
  --exact
  --synced-only
  --tag key=value        # repeatable
  --limit <n>
  --json
  --path-only
```

### CLI behavior
- default output: compact human-readable list
- `--json`: full structured result
- `--path-only`: print only the resolved path when there is exactly one usable match
- if zero matches: exit non-zero with a clear "not found" message
- if `--path-only` and multiple usable matches exist: exit non-zero with an "ambiguous match" message and a short candidate list

Example default output:

```text
1. project=platform repo=abacus-app
   path=/workspace/platform/abacus-app
   status=synced exists=true git=true sync=true
   matched=repo_name:exact,tags.code:exact
```

## MCP surface
Add a new tool, likely `metagit_repo_search`.

Suggested schema:

```json
{
  "type": "object",
  "required": ["query"],
  "properties": {
    "query": {"type": "string"},
    "project": {"type": "string"},
    "exact": {"type": "boolean"},
    "synced_only": {"type": "boolean"},
    "limit": {"type": "integer", "minimum": 1},
    "tags": {
      "type": "object",
      "additionalProperties": {"type": "string"}
    }
  },
  "additionalProperties": false
}
```

Return shape:

```json
{
  "matches": [
    {
      "project_name": "platform",
      "repo_name": "abacus-app",
      "url": "https://github.com/example/abacus-app.git",
      "configured_path": "services/abacus-app",
      "tags": {"code": "abacus", "domain": "terraform"},
      "status": {
        "resolved_path": "/workspace/platform/abacus-app",
        "exists": true,
        "is_git_repo": true,
        "sync_enabled": true,
        "status": "synced"
      },
      "match_reasons": ["repo_name:exact", "tags.code:exact"],
      "score": 100
    }
  ]
}
```

This tool should only be available when the workspace is active and `.metagit.yml` is valid, same as the current managed workspace tools.

## HTTP API surface
This repo does not currently have an API layer, so the first pass should stay small and local.

Add an `api` command group with a `serve` subcommand, for example:

```bash
metagit api serve --host 127.0.0.1 --port 7878
```

Use a minimal local JSON server in v1. Do not turn this into a broader web service platform yet.

### Endpoints

```text
GET /v1/repos/search?q=abacus
GET /v1/repos/resolve?q=abacus
```

Supported query parameters:

- `q`
- `project`
- `exact`
- `synced_only`
- `limit`
- repeated `tag` values in `key=value` form

### Endpoint semantics
- `/search` returns a ranked list
- `/resolve` returns exactly one usable repo or a typed error

Example `/resolve` error:

```json
{
  "error": {
    "kind": "ambiguous_match",
    "message": "Search matched more than one managed repository.",
    "matches": [
      {"project_name": "platform", "repo_name": "abacus-app"},
      {"project_name": "shared", "repo_name": "abacus-module"}
    ]
  }
}
```

## Error handling
The feature should optimize for safe agent behavior.

### Search results
- zero matches is not a silent success
- ambiguous matches are first-class results, not something the caller has to infer
- missing local paths should be surfaced directly in status
- non-git paths should be surfaced directly in status

### Resolve behavior
`resolve_one()` should return:

- one usable result
- `not_found`
- `ambiguous_match`
- `not_synced` when the repo is configured but the caller requested `synced_only`

The error kind should be stable across CLI JSON output, MCP output, and HTTP API output.

### Safety rule
Agents should use `resolved_path` only after checking:

- `exists == true`
- `is_git_repo == true`
- `status == "synced"`

That gives the agent a clear stop point before it starts editing in the wrong place.

## Testing strategy
Follow the repo pattern of thin command handlers with core behavior tested separately.

### Unit tests
Add targeted tests for the new search service:

- exact repo name match
- partial repo name match
- URL match
- path match
- tag filter match
- project filter scoping
- synced-only filtering
- ambiguous resolve result
- missing path status
- non-git path status

Likely file:

`tests/test_project_search_service.py`

### CLI tests
Add focused CLI tests for:

- `metagit search <query>`
- `metagit find <query>`
- `--json`
- `--path-only`
- ambiguous exit behavior

Likely file:

`tests/cli/commands/test_search.py`

### MCP tests
Extend MCP tests for:

- tool visibility in active workspace state
- valid `tools/call` response
- invalid argument handling
- ambiguous results returned as structured data

Likely file:

`tests/core/mcp/test_runtime.py` or the current MCP test files if that pattern already exists in this repo

### API tests
Add focused tests for:

- `/v1/repos/search`
- `/v1/repos/resolve`
- tag query parsing
- typed error payloads

Likely file:

`tests/api/test_repo_search_api.py`

## Implementation boundaries
The implementation should be split like this:

- `src/metagit/core/project/search_models.py`
- `src/metagit/core/project/search_service.py`
- `src/metagit/cli/commands/search.py`
- `src/metagit/cli/commands/api.py`
- `src/metagit/core/api/...` for the local HTTP server and handlers

Shared code should stay in core. CLI, MCP, and API should be wrappers around the same service.

## Open questions resolved during design
- Search scope: managed repos only
- Freshness model: local manifest state only
- Tags: supported now as flat metadata tags
- Main job of the feature: resolve the correct local repo path and current sync status for users and agents

## Rollout notes
This feature should ship as a safe lookup layer first. Provider-backed discovery, unmanaged repo scanning, and broader workspace cataloging can come later if the managed-repo resolver proves useful.

The important part in v1 is trust. When `metagit search abacus` returns a result, the caller should know why it matched, where the repo lives, and whether it is actually ready to work in.
