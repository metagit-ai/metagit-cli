---
name: secret-bootstrapper
description: |
  Guides SecretZero bootstrap when Secretfile.yml is present. Never handles secret values. Load this skill for scoped sessions.
model: inherit
tools: Read, Bash, Grep, Glob, Skill
---

{{ include "body" }}
