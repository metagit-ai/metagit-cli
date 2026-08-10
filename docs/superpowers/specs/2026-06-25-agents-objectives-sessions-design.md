# Agents Objectives and Sessions Design

## Summary

Extend the existing `web/src/pages/AgentsPage.tsx` route so the current agent template catalog remains available under a `Templates` sub-tab, and add two new sub-tabs: `Objectives` and `Sessions`. The new tabs will consume the recently added web ops endpoints for collaborative objective editing and current session visibility. Both new tabs will support optional live updates with a default interval of 90 seconds.

## Goals

- Preserve all current `/agents` template catalog behavior without moving it to a new route.
- Add an `Objectives` tab that supports create, read, update, and status changes through the existing `/v3/ops/objectives` API.
- Add a `Sessions` tab that shows the current session digest from `/v3/ops/session` and supports an explicit `Begin session` action via `/v3/ops/session/begin`.
- Add shared live-refresh controls for the `Objectives` and `Sessions` experience with:
  - `Live update` checkbox
  - configurable refresh cadence
  - default interval of 90 seconds
- Match current React, TanStack Query, and CSS-module patterns already used in the SPA.

## Non-Goals

- No new top-level routes beyond `/agents`.
- No new frontend framework, state library, or form library.
- No raw JSON inspector for the full `session/begin` response.
- No server-side push channel for objectives or sessions in this change; polling only.

## User Experience

### Agents page structure

The `/agents` page becomes a three-sub-tab console:

- `Templates`
- `Objectives`
- `Sessions`

`Templates` keeps the current catalog/detail/preview/overlay-init functionality intact. Existing interactions should stay recognizable and no behavior should regress.

### Objectives tab

The `Objectives` tab provides a workspace-facing collaboration surface.

Layout:

- top controls row with live refresh settings and a manual refresh button
- create-objective form near the top
- grouped objective sections by status:
  - `pending`
  - `in_progress`
  - `done`
  - `cancelled`

Per-objective card behavior:

- editable fields:
  - `title`
  - `acceptance`
  - `human_notes`
  - `status`
- display-only prominent field:
  - `agent_notes`
- optional repo list editing through a simple comma-separated input mapped to `repos: string[]`
- save action updates the objective through `PATCH /v3/ops/objectives/{id}`

Create form behavior:

- requires `id` and `title`
- optional initial `status`, `acceptance`, `human_notes`, and `repos`
- sends `POST /v3/ops/objectives`
- refreshes the objective list after success

### Sessions tab

The `Sessions` tab is a read-only dashboard plus one explicit action.

Layout:

- top controls row with live refresh settings and a manual refresh button
- session summary card
- repo changes list
- `Begin session` action block
- compact result summary after a begin action succeeds

Displayed digest fields:

- `active_objective_id`
- `first_session`
- `manifest_changed`
- `since`
- `repo_changes[]`

Repo changes presentation:

- project/repo identity
- commit count
- recent subjects list
- inline error text when a row includes `error`

`Begin session` action behavior:

- invokes `POST /v3/ops/session/begin`
- does not render the full raw envelope
- instead shows a compact confirmation summary such as:
  - workspace name
  - active project
  - objective count
  - pending approval count
  - warning count
- refreshes both session digest and objectives on success because session begin can affect workflow context visible across both tabs

## Refresh Model

Live refresh is scoped to the `Agents` page and reused by both new tabs.

Defaults:

- live update: enabled
- interval: 90 seconds

Allowed intervals:

- 30 seconds
- 60 seconds
- 90 seconds
- 300 seconds

Behavior:

- when live update is enabled, the `Objectives` and `Sessions` data queries refetch on the selected cadence
- when disabled, polling stops and only manual refresh or successful mutations trigger refresh
- `Templates` does not need live polling; its current query behavior remains unchanged

## Frontend Architecture

Recommended implementation stays inside the existing `/agents` route with focused child panels rather than introducing nested routing.

### Component structure

Keep `web/src/pages/AgentsPage.tsx` as the owning route component and split rendering into local child sections or nearby helper components as needed:

- `TemplatesPanel`
- `ObjectivesPanel`
- `SessionsPanel`
- shared live refresh controls component or local helper block

This keeps route churn low and preserves current navigation structure while allowing the page file to delegate dense UI sections.

### Data layer

Extend `web/src/api/client.ts` with typed request/response helpers for:

- `GET /v3/ops/objectives`
- `POST /v3/ops/objectives`
- `PATCH /v3/ops/objectives/{id}`
- `GET /v3/ops/session`
- `POST /v3/ops/session/begin`

Extend `web/src/pages/agentQueries.ts` with query keys and fetch wrappers for:

- objectives list
- session digest

Use TanStack Query for:

- cached fetches
- mutation invalidation
- optional `refetchInterval` driven by page state

### State model

Local `AgentsPage` state should own:

- selected sub-tab
- live update enabled flag
- selected refresh interval
- template-specific selection state already present
- transient success/error message state for objectives and session begin

Editable objective draft state can remain local to each rendered objective card.

## API Usage

### Objectives

- `GET /v3/ops/objectives`
  - source of truth for all objective groupings
- `POST /v3/ops/objectives`
  - create a new objective
- `PATCH /v3/ops/objectives/{id}`
  - update editable fields and status

The UI should rely on server responses after mutation rather than attempting optimistic local reconciliation across all grouped lists.

### Sessions

- `GET /v3/ops/session`
  - current digest for dashboard state
- `POST /v3/ops/session/begin`
  - explicit begin action and compact success summary

## Error Handling

- Reuse the existing `ApiError` pattern from `web/src/api/client.ts`.
- Show inline section-scoped errors rather than global page failure whenever possible.
- Keep template catalog errors isolated from objectives/session errors.
- On mutation success, show concise confirmation text and invalidate/refetch the affected queries.
- On mutation failure, preserve local draft values so the user can retry without retyping.

## Testing Strategy

### Frontend tests

Add focused tests for the new `/agents` page behavior, covering:

- current templates functionality still renders under the `Templates` sub-tab
- switching to `Objectives` loads and groups objectives by status
- objective edit mutation sends the expected patch payload and refreshes state
- switching to `Sessions` loads digest data and renders summary + repo changes
- `Begin session` triggers the action and displays compact summary output
- live update toggle and interval selection control `refetchInterval` behavior at the query layer or component behavior level

If the repo currently has limited frontend test harness coverage for page components, use the smallest test surface consistent with existing web test patterns.

### Existing backend coverage reuse

No new backend behavior is required for this UI-only step beyond the already-added API endpoints. The frontend should consume those existing contracts directly.

## Risks and Mitigations

### Risk: Agents page becomes too large

Mitigation:

- split the page into small local child panels during implementation
- keep template logic isolated from new objective/session logic

### Risk: polling causes unnecessary network churn

Mitigation:

- keep intervals coarse and user-controlled
- default to 90 seconds rather than a high-frequency poll
- only apply live polling to objectives and sessions

### Risk: grouped objective lists drift after edits

Mitigation:

- invalidate and refetch objective list after mutations
- avoid complex client-side regrouping logic during writes

## Implementation Notes

- Prefer the smallest possible route/layout diff.
- Preserve existing `AgentsPage` CSS language where possible; extend `AgentsPage.module.css` rather than introducing a separate styling system.
- Keep `Templates` functionally unchanged aside from being nested under a sub-tab.
- Refresh both objectives and sessions after `Begin session` to preserve a coherent collaborative workflow view.

## Acceptance Criteria

- `/agents` shows sub-tabs for `Templates`, `Objectives`, and `Sessions`
- current templates behavior remains available under `Templates`
- `Objectives` can create and edit objectives using the current ops API
- `Sessions` shows the current digest and supports `Begin session`
- a live update checkbox and frequency control are available and default to 90 seconds
- manual refresh remains available when live update is disabled
- all changes follow existing SPA patterns and pass repo QA