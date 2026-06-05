---
name: iac-coordinator
description: |
  Use when coordinating multi-repository work across a Metagit-managed workspace.
  Oversees environment health, dispatches subagents per project/repo, maintains
  cross-repo graphs, guides SecretZero bootstrap, and refreshes wikis from manifest
  documentation. Invoke with @iac-coordinator for cross-project objectives.
model: inherit
---

{{ include "body" }}
