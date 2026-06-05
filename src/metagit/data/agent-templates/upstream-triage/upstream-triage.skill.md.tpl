---
name: upstream-triage
description: |
  Triages cross-repo blockers by ranking likely upstream repositories and files. Load this skill for scoped sessions.
model: inherit
tools: Read, Bash, Grep, Glob, Skill
skills:
  - metagit-upstream-scan
  - metagit-upstream-triage
  - metagit-multi-repo
---

{{ include "body" }}
