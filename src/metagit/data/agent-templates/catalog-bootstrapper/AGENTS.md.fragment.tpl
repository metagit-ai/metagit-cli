# Orchestration overseer (Metagit)

Coordinator workspace **{{ workspace_name }}** uses the `orchestration-overseer` agent
template. Install the vendor agent definition with:

```bash
metagit agent create orchestration-overseer --vendor claude_code --scope project
metagit skills install --scope project
metagit mcp install --scope project
```

Manifest: `{{ manifest_path }}`

## Overseer duties

- Metagit MCP control plane for multi-repo awareness and guarded sync
- Subagent dispatch per `workspace.projects[]` with `effective_agent_instructions`
- Graph discover → suggest → ingest → `gitnexus group sync`
- SecretZero skill/MCP when `Secretfile.yml` exists in managed repos
- GitNexus wiki refresh from manifest `documentation[]` links

Invoke `@orchestration-overseer` (Claude Code) or your vendor's equivalent for
cross-project objectives. Single-repo implementation stays with focused subagents.
