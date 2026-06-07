---
name: secret-bootstrapper
description: |
  Guides SecretZero bootstrap when Secretfile.yml is present. Never handles secret values.
model: inherit
tools: Read, Bash, Grep, Glob, Skill
---

{{ include "body" }}
