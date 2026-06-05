---
name: release-auditor
description: |
  Runs release-audit workflows, objectives tracking, and prepush gate checks. Load this skill for scoped sessions.
model: inherit
tools: Read, Bash, Grep, Glob, Skill
skills:
  - metagit-release-audit
  - metagit-control-center
---

{{ include "body" }}
