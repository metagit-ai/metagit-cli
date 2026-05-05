# Metagit MCP Gated Workspace and Upstream Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an MCP server runtime for Metagit that is gated by `.metagit.yml`, supports cross-repo upstream discovery, and offers sampling-assisted `.metagit.yml` bootstrap workflows.

**Architecture:** Add a new MCP service layer under `src/metagit/core/mcp/` with explicit boundaries for root resolution, gating, tool registry, repo services, and sampling orchestration. Expose the runtime through a new CLI command path and cover behavior with unit/integration tests.

**Tech Stack:** Python 3.12, Click CLI, Pydantic models, GitPython, pytest, ripgrep subprocess boundary (if needed), MCP server SDK used by project.

---

### Task 1: MCP Package Skeleton and Core Protocol Contracts

**Files:**
- Create: `src/metagit/core/mcp/__init__.py`
- Create: `src/metagit/core/mcp/models.py`
- Create: `src/metagit/core/mcp/protocols.py`
- Test: `tests/core/mcp/test_models.py`

- [ ] **Step 1: Write failing model tests for MCP state and DTOs**

```python
from metagit.core.mcp.models import McpActivationState


def test_activation_state_values() -> None:
  assert McpActivationState.ACTIVE.value == "active"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/mcp/test_models.py -v`
Expected: FAIL with import/module not found errors

- [ ] **Step 3: Add minimal models/protocol definitions**

```python
from enum import Enum
from pydantic import BaseModel


class McpActivationState(str, Enum):
  ACTIVE = "active"
  INACTIVE_MISSING_CONFIG = "inactive_missing_config"
  INACTIVE_INVALID_CONFIG = "inactive_invalid_config"


class WorkspaceStatus(BaseModel):
  state: McpActivationState
  root_path: str | None = None
  reason: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/mcp/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/__init__.py src/metagit/core/mcp/models.py src/metagit/core/mcp/protocols.py tests/core/mcp/test_models.py
git commit -m "feat: add mcp core state and contract models"
```

### Task 2: Workspace Root Resolver and Gate Evaluator

**Files:**
- Create: `src/metagit/core/mcp/root_resolver.py`
- Create: `src/metagit/core/mcp/gate.py`
- Test: `tests/core/mcp/test_root_resolver.py`
- Test: `tests/core/mcp/test_gate.py`

- [ ] **Step 1: Write failing tests for root precedence and missing config state**

```python
def test_env_root_has_highest_precedence(monkeypatch, tmp_path) -> None:
  monkeypatch.setenv("METAGIT_WORKSPACE_ROOT", str(tmp_path))
  # assert resolver picks env path first
```

- [ ] **Step 2: Run tests to verify failures**

Run: `uv run pytest tests/core/mcp/test_root_resolver.py tests/core/mcp/test_gate.py -v`
Expected: FAIL for missing resolver/gate implementations

- [ ] **Step 3: Implement resolver and gate using existing config manager**

```python
class WorkspaceRootResolver:
  def resolve(self, cwd: str, cli_root: str | None = None) -> str | None:
    # precedence: env, cli_root, upward walk
    ...


class WorkspaceGate:
  def evaluate(self, root_path: str | None) -> WorkspaceStatus:
    # load .metagit.yml and validate using MetagitConfigManager
    ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/core/mcp/test_root_resolver.py tests/core/mcp/test_gate.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/root_resolver.py src/metagit/core/mcp/gate.py tests/core/mcp/test_root_resolver.py tests/core/mcp/test_gate.py
git commit -m "feat: add metagit mcp root resolution and gating"
```

### Task 3: Tool Registry with Inactive/Active Surface

**Files:**
- Create: `src/metagit/core/mcp/tool_registry.py`
- Create: `src/metagit/core/mcp/tools/workspace_status.py`
- Create: `src/metagit/core/mcp/tools/bootstrap_plan_only.py`
- Test: `tests/core/mcp/test_tool_registry.py`

- [ ] **Step 1: Write failing registry tests for state-dependent tool exposure**

```python
def test_inactive_registry_exposes_only_safe_tools() -> None:
  # assert only status and bootstrap_plan_only are visible
  ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/core/mcp/test_tool_registry.py -v`
Expected: FAIL due to missing registry implementation

- [ ] **Step 3: Implement minimal registry and baseline tools**

```python
class ToolRegistry:
  def list_tools(self, status: WorkspaceStatus) -> list[str]:
    if status.state == McpActivationState.ACTIVE:
      return ["metagit_workspace_status", "metagit_workspace_index", "metagit_workspace_search", "metagit_upstream_hints", "metagit_repo_inspect", "metagit_repo_sync", "metagit_bootstrap_config"]
    return ["metagit_workspace_status", "metagit_bootstrap_config_plan_only"]
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/core/mcp/test_tool_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/tool_registry.py src/metagit/core/mcp/tools/workspace_status.py src/metagit/core/mcp/tools/bootstrap_plan_only.py tests/core/mcp/test_tool_registry.py
git commit -m "feat: add stateful mcp tool registry"
```

### Task 4: Workspace Repo Inventory and Search Service

**Files:**
- Create: `src/metagit/core/mcp/services/workspace_index.py`
- Create: `src/metagit/core/mcp/services/workspace_search.py`
- Test: `tests/core/mcp/services/test_workspace_index.py`
- Test: `tests/core/mcp/services/test_workspace_search.py`

- [ ] **Step 1: Write failing tests for repo index and scoped search behavior**

```python
def test_workspace_index_resolves_repo_paths(tmp_path) -> None:
  # assert configured repos produce normalized status rows
  ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/core/mcp/services/test_workspace_index.py tests/core/mcp/services/test_workspace_search.py -v`
Expected: FAIL due to missing services

- [ ] **Step 3: Implement repo inventory and safe cross-repo search**

```python
class WorkspaceSearchService:
  def search(self, query: str, repo_paths: list[str], preset: str | None = None) -> list[dict[str, str]]:
    # restrict search scope to configured roots and cap output
    ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/core/mcp/services/test_workspace_index.py tests/core/mcp/services/test_workspace_search.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/services/workspace_index.py src/metagit/core/mcp/services/workspace_search.py tests/core/mcp/services/test_workspace_index.py tests/core/mcp/services/test_workspace_search.py
git commit -m "feat: add workspace repo indexing and search services"
```

### Task 5: Upstream Hint Ranking Service

**Files:**
- Create: `src/metagit/core/mcp/services/upstream_hints.py`
- Test: `tests/core/mcp/services/test_upstream_hints.py`

- [ ] **Step 1: Write failing tests for candidate ranking from blocker text**

```python
def test_terraform_blocker_ranks_infra_repos_higher() -> None:
  # assert infra/terraform tagged repositories rank at top
  ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/core/mcp/services/test_upstream_hints.py -v`
Expected: FAIL due to missing ranking service

- [ ] **Step 3: Implement heuristic ranking by keyword, metadata, and search signal**

```python
class UpstreamHintService:
  def rank(self, blocker: str, repo_context: list[dict[str, str]]) -> list[dict[str, str | float]]:
    # deterministic weighted scoring and sorted candidates
    ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/core/mcp/services/test_upstream_hints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/services/upstream_hints.py tests/core/mcp/services/test_upstream_hints.py
git commit -m "feat: add upstream blocker hint ranking service"
```

### Task 6: Sampling Bootstrap Orchestrator

**Files:**
- Create: `src/metagit/core/mcp/services/bootstrap_sampling.py`
- Create: `src/metagit/core/mcp/services/discovery_context.py`
- Test: `tests/core/mcp/services/test_bootstrap_sampling.py`

- [ ] **Step 1: Write failing tests for sampling and fallback behavior**

```python
def test_sampling_disabled_returns_plan_only_payload() -> None:
  # assert no sampling call and prompt bundle returned
  ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/core/mcp/services/test_bootstrap_sampling.py -v`
Expected: FAIL due to missing orchestrator

- [ ] **Step 3: Implement discovery packaging, sampling loop, and validation retries**

```python
class BootstrapSamplingService:
  def generate(self, context: dict[str, str], confirm_write: bool = False) -> dict[str, str]:
    # if sampling supported -> createMessage loop + validation
    # else -> plan-only payload
    ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/core/mcp/services/test_bootstrap_sampling.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/services/bootstrap_sampling.py src/metagit/core/mcp/services/discovery_context.py tests/core/mcp/services/test_bootstrap_sampling.py
git commit -m "feat: add mcp sampling bootstrap for metagit config"
```

### Task 7: Repo Inspect and Guarded Sync Service

**Files:**
- Create: `src/metagit/core/mcp/services/repo_ops.py`
- Test: `tests/core/mcp/services/test_repo_ops.py`

- [ ] **Step 1: Write failing tests for inspect and safe sync mode restrictions**

```python
def test_pull_requires_explicit_mutation_enable() -> None:
  # assert guarded failure when mutation toggles are absent
  ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/core/mcp/services/test_repo_ops.py -v`
Expected: FAIL due to missing repo ops implementation

- [ ] **Step 3: Implement inspect and sync with guardrails (`fetch` default)**

```python
class RepoOperationsService:
  def sync(self, repo_path: str, mode: str = "fetch", allow_mutation: bool = False) -> dict[str, str]:
    # enforce fetch default and mutation gate for pull/clone
    ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/core/mcp/services/test_repo_ops.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/services/repo_ops.py tests/core/mcp/services/test_repo_ops.py
git commit -m "feat: add guarded repo inspect and sync operations"
```

### Task 8: CLI Command and MCP Server Runtime Wiring

**Files:**
- Create: `src/metagit/cli/commands/mcp.py`
- Modify: `src/metagit/cli/main.py`
- Create: `tests/cli/commands/test_mcp.py`

- [ ] **Step 1: Write failing CLI tests for `metagit mcp serve` and root option behavior**

```python
def test_mcp_serve_accepts_root_option(runner) -> None:
  result = runner.invoke(cli, ["mcp", "serve", "--root", "/tmp/project"])
  assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/cli/commands/test_mcp.py -v`
Expected: FAIL due to missing command wiring

- [ ] **Step 3: Implement command registration and runtime startup path**

```python
@click.group()
def mcp() -> None:
  pass


@mcp.command("serve")
@click.option("--root", default=None)
def serve(root: str | None) -> None:
  # initialize resolver, gate, tool registry, and start MCP runtime
  ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/cli/commands/test_mcp.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/commands/mcp.py src/metagit/cli/main.py tests/cli/commands/test_mcp.py
git commit -m "feat: add metagit mcp serve cli command"
```

### Task 9: MCP Resources and Operational Log Exposure

**Files:**
- Create: `src/metagit/core/mcp/resources.py`
- Create: `src/metagit/core/mcp/services/ops_log.py`
- Test: `tests/core/mcp/test_resources.py`

- [ ] **Step 1: Write failing tests for workspace config/status/ops resources**

```python
def test_workspace_resources_available_when_active() -> None:
  # assert resource map includes config and repos status
  ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/core/mcp/test_resources.py -v`
Expected: FAIL due to missing resource publisher

- [ ] **Step 3: Implement resource handlers and bounded operations log**

```python
class ResourcePublisher:
  def get_resource(self, uri: str) -> dict[str, str | list[dict[str, str]]]:
    ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/core/mcp/test_resources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/resources.py src/metagit/core/mcp/services/ops_log.py tests/core/mcp/test_resources.py
git commit -m "feat: add mcp workspace resources and ops log"
```

### Task 10: End-to-End Integration and Documentation Updates

**Files:**
- Create: `tests/integration/test_mcp_workspace_flow.py`
- Modify: `README.md`
- Modify: `docs/development.md`
- Modify: `docs/cli_reference.md`

- [ ] **Step 1: Write failing integration tests for inactive->active->search->sync flow**

```python
def test_end_to_end_workspace_activation_and_discovery(tmp_path) -> None:
  # assert server behavior changes after valid .metagit.yml is present
  ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/integration/test_mcp_workspace_flow.py -v`
Expected: FAIL due to incomplete end-to-end wiring

- [ ] **Step 3: Complete integration wiring and user documentation**

```markdown
# docs updates
- New command: metagit mcp serve
- Gating states and troubleshooting
- Sampling bootstrap usage
- Upstream discovery examples
```

- [ ] **Step 4: Run full MCP-related test suite**

Run: `uv run pytest tests/core/mcp tests/cli/commands/test_mcp.py tests/integration/test_mcp_workspace_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_mcp_workspace_flow.py README.md docs/development.md docs/cli_reference.md
git commit -m "docs: add metagit mcp usage and integration coverage"
```

## Final Verification Checklist

- [ ] `uv run pytest tests/core/mcp -v`
- [ ] `uv run pytest tests/cli/commands/test_mcp.py -v`
- [ ] `uv run pytest tests/integration/test_mcp_workspace_flow.py -v`
- [ ] `uv run ruff check src tests`
- [ ] `uv run ruff format --check src tests`

## Implementation Notes

- Keep all path handling safe and normalized.
- Ensure every mutating action is opt-in and logged.
- Prefer deterministic heuristics first; keep ranking explainable.
- Preserve backward compatibility for existing CLI commands.
