name: {{ name }}
description: |
  {{ description }}
kind: umbrella
url: {{ url }}
workspace:
  description: Workspace projects synced under the configured workspace.path.
  projects:
    - name: default
      description: Default project group for managed repositories.
      repos: []
