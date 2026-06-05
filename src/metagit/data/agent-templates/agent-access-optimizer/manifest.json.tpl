{
  "id": "orchestration-overseer",
  "label": "Orchestration overseer",
  "workspace_name": "{{ workspace_name }}",
  "manifest_path": "{{ manifest_path }}",
  "description": "{{ coordinator_description }}",
  "capabilities": [
    "metagit-mcp-control-plane",
    "subagent-dispatch",
    "graph-maintain",
    "gitnexus-group-sync",
    "secretzero-bootstrap",
    "documentation-wiki-refresh"
  ],
  "recommended_skills": [
    "metagit-control-center",
    "metagit-context-pack",
    "metagit-graph-maintain",
    "metagit-gitnexus",
    "metagit-cli"
  ],
  "external_skills": [
    "secretzero",
    "gitnexus-cli"
  ],
  "prompts": [
    "session-start",
    "graph-discover",
    "graph-maintain",
    "sync-safe",
    "health-preflight"
  ]
}
