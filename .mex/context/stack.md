---
name: stack
description: Technology stack, library choices, and the reasoning behind them. Load when working with specific technologies or making decisions about libraries and tools.
triggers:
  - "library"
  - "package"
  - "dependency"
  - "which tool"
  - "technology"
edges:
  - target: context/decisions.md
    condition: when the reasoning behind a tech choice is needed
  - target: context/conventions.md
    condition: when understanding how to use a technology in this codebase
  - target: context/setup.md
    condition: when stack choices affect local tooling or command execution
  - target: context/mcp-runtime.md
    condition: when working with MCP JSON-RPC transport, tools, and resources
last_updated: 2026-05-05
---

# Stack

## Core Technologies
- **Python 3.12** — primary language runtime (`requires-python >=3.12` in `pyproject.toml`).
- **Click** — CLI framework used by `metagit.cli.main` and command modules.
- **Pydantic v2** — schema and model validation for config/app/workspace/records.
- **uv** — package/environment and command runner used across Taskfile and setup.
- **Taskfile (`task`)** — command orchestration layer for lint/test/build/docs workflows.

## Key Libraries
- **`pydantic`** — all structured config/workspace records are modeled and validated with explicit models.
- **`PyYAML` + custom loader (`metagit.core.utils.yaml_class`)** — YAML parsing with include/envvar and duplicate-key behavior.
- **`GitPython`** — repository metadata and sync operations instead of raw shell git calls in core logic.
- **`pytest`** — primary testing framework for unit/integration tests in `tests/`.
- **`ruff`** — primary lint + format tool for current local workflow (`task lint`, `task format`).
- **`litellm`** — agent-oriented integrations in core dependencies.
- **`crewai`** — optional dependency group (`uv sync --group crewai`) for detect-flow crews; not installed in default/prepush audit env (avoids transitive chromadb until upstream patch).

## What We Deliberately Do NOT Use
- No JavaScript/TypeScript runtime as the primary execution path; core implementation is Python CLI/service modules.
- No monolithic web framework dependency (e.g., Django/FastAPI app server) for core product behavior.
- No direct subprocess-heavy git orchestration as the primary pattern where GitPython is available.

## Version Constraints
- Python must be 3.12+ for supported runtime behavior.
- Pydantic is v2-style; legacy v1 patterns should not be introduced.
- MCP protocol version emitted by runtime initialize response is `2024-11-05`.
