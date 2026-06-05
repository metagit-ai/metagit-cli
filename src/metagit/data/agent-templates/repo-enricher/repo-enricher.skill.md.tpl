---
name: repo-enricher
description: |
  Enriches a single repo catalog entry via detect/source sync and repo-enrich prompt workflows. Load this skill for scoped sessions.
model: inherit
tools: Read, Write, Bash, Grep, Glob, Skill
skills:
  - metagit-config-refresh
  - metagit-cli
---

{{ include "body" }}
