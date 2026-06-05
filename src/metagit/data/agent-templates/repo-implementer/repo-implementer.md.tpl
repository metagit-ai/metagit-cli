---
name: repo-implementer
description: |
  Single-repo implementation specialist dispatched by the orchestration overseer. Focuses on scoped code changes, guarded sync, and handoff prompts.
model: inherit
tools: Read, Write, Edit, Bash, Grep, Glob, Skill
skills:
  - metagit-cli
  - metagit-workspace-sync
  - metagit-repo-impact
---

{{ include "body" }}
