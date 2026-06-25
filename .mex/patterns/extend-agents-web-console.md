---
name: extend-agents-web-console
description: Extend the `/agents` SPA route with additional sub-tabs or panels while preserving template catalog behavior and using existing ops API/query patterns.
triggers:
  - "agents page"
  - "agents tab"
  - "templates objectives sessions"
edges:
  - target: "context/architecture.md"
    condition: "when combining `/v3/agents/*` and `/v3/ops/*` data in one page"
  - target: "context/conventions.md"
    condition: "before adding tests, queries, or SPA state"
last_updated: 2026-06-25
---

# Extend Agents Web Console

## Context
- The `/agents` route is a single React page at `web/src/pages/AgentsPage.tsx`.
- Agent catalog data comes from `web/src/pages/agentQueries.ts` and `/v3/agents/*`.
- Objective/session workflow data comes from `web/src/api/client.ts` + `web/src/pages/agentQueries.ts` backed by `/v3/ops/objectives*` and `/v3/ops/session*`.
- Keep route churn minimal; prefer sub-tabs/panels inside the existing page over nested routes unless deep-linking is explicitly required.

## Steps
1. Add or update page-level tests in `web/src/pages/AgentsPage.test.tsx` first.
2. Wire any new query helpers through `web/src/pages/agentQueries.ts`; keep raw fetch helpers in `web/src/api/client.ts`.
3. Preserve the current `Templates` workflow before layering new tabs or panels.
4. Scope polling controls to the page or affected panels; use TanStack Query `refetchInterval` rather than ad hoc timers.
5. Keep editable draft state local to each card/panel and invalidate/refetch after mutations instead of doing complex optimistic regrouping.
6. Extend `web/src/pages/AgentsPage.module.css` rather than introducing a parallel styling system.

## Gotchas
- `web/src/components/OpsPanel.tsx` is separate from `/agents`; do not leave partial imports or dead helpers there when moving objective/session UX into `AgentsPage`.
- The page mixes three concerns: templates, objectives, and sessions. Split into focused local helpers/components before adding more state to the route body.
- Live refresh should not apply to the Templates catalog by default.
- `Begin session` should refresh both session digest and objective queries to keep workflow context aligned.

## Verify
- Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx`
- Run: `cd web && npm run build`
- Run: `task qa:prepush`
- Run: `task gitnexus:analyze`

## Debug
- If the page compiles but tests fail to find tabs or controls, confirm the active panel renders after tab click and that labels are unique across tabs.
- If objectives/sessions appear stale, confirm `refetchInterval` is disabled with `false` when live update is off and that post-mutation invalidation targets the correct query keys.
- If TypeScript fails in unrelated web files, look for abandoned imports or helpers from intermediate UI experiments.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`