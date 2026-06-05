---
name: release-auditor
description: |
  Runs release-audit workflows, objectives tracking, and prepush gate checks.
model: inherit
tools: Read, Bash, Grep, Glob, Skill
skills:
  - metagit-release-audit
  - metagit-control-center
---

{{ include "body" }}
