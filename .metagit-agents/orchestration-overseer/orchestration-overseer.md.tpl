---
name: orchestration-overseer
description: |
  Use when coordinating multi-repository work across a Metagit-managed workspace.
  Oversees environment health, dispatches subagents per project/repo, maintains
  cross-repo graphs, guides SecretZero bootstrap, and refreshes wikis from manifest
  documentation. Examples:

  <example>
  Context: Operator starts a session in an umbrella workspace with stale clones.
  user: "Get the workspace ready and tell me what's blocked."
  assistant: "I'll invoke the orchestration-overseer to run health checks, context pack,
  and graph maintenance before summarizing blockers."
  <commentary>
  Session bootstrap and cross-repo awareness belong to the overseer, not a repo agent.
  </commentary>
  </example>

  <example>
  Context: A feature spans API and frontend repos in different projects.
  user: "Implement auth refresh across api-service and web-app."
  assistant: "Delegating to orchestration-overseer to scope projects, sync safely,
  and dispatch focused subagents with effective_agent_instructions."
  <commentary>
  Cross-project objectives need manifest-scoped dispatch and guarded sync.
  </commentary>
  </example>

model: inherit
tools: Read, Write, Edit, Bash, Grep, Glob, Agent, Skill
skills:
  - metagit-control-center
  - metagit-context-pack
  - metagit-graph-maintain
  - metagit-gitnexus
  - metagit-cli
---

{{ include "body" }}
