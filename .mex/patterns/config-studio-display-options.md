---
name: config-studio-display-options
description: Session-only Config Studio display prefs and list-remove UX.
last_updated: 2026-08-06
---

# Config Studio display options

## Where
- Prefs live in React state on `web/src/pages/ConfigPage.tsx` (not persisted).
- Tree filtering / numbering / type labels: `web/src/components/SchemaTree.tsx` via `visibleChildNodes`.
- Array remove affordance (`×`) is on list-item header rows; when **Show list item headers** is off (default), those rows are hidden and children render inline.

## Gotchas
- FieldEditor array hint must tell users to enable **Show list item headers** to remove items; do not claim `×` is always visible.
- After SPA edits, run `task web:build` so `src/metagit/data/web/` stays in sync with `web/`.
