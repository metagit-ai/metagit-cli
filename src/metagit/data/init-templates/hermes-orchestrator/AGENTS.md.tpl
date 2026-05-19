# Hermes orchestrator coordinator

This repository was initialized with the `hermes-orchestrator` metagit template.

## Controller role

You are the DevOps and project-management entrypoint for workspace **{{ name }}**.
Read root and layered `agent_instructions` in `.metagit.yml` before changing workspace layout.

## Session checklist

1. `metagit_workspace_status` and `metagit_workspace_health_check`
2. Search before create (`metagit search` / `metagit_repo_search`)
3. `metagit config validate` after manifest edits
4. `metagit_project_context_switch` when focusing a project
5. Delegate single-repo work to subagents with `effective_agent_instructions`
6. `metagit_session_update` on handoff

## Docs

- [Hermes orchestrator workspace](https://metagit-ai.github.io/metagit-cli/hermes-orchestrator-workspace/)
- [Hermes & org IaC guide](https://metagit-ai.github.io/metagit-cli/hermes-iac-workspace-guide/)
