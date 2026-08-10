# Agents Objectives and Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `/agents` so the current templates UI remains available under a `Templates` sub-tab, and add `Objectives` and `Sessions` sub-tabs backed by the new ops API endpoints with optional live refresh defaulting to 90 seconds.

**Architecture:** Keep `web/src/pages/AgentsPage.tsx` as the owning route component and split the page into focused local panels instead of adding nested routes. Add typed agent-page query helpers and a minimal Vitest + Testing Library harness so the new behavior is implemented test-first and verified at component level.

**Tech Stack:** React 19, TypeScript, Vite, TanStack Query, CSS Modules, Vitest, Testing Library.

## Global Constraints

- No new top-level routes beyond `/agents`.
- No new frontend framework, state library, or form library.
- No raw JSON inspector for the full `session/begin` response.
- No server-side push channel for objectives or sessions in this change; polling only.
- Keep `Templates` functionally unchanged aside from being nested under a sub-tab.
- Live refresh defaults to enabled with a 90 second interval.
- Allowed intervals are 30 seconds, 60 seconds, 90 seconds, and 300 seconds.
- Refresh both objectives and sessions after `Begin session` succeeds.

---

### Task 1: Add Web Test Harness For Agents Page Work

**Files:**
- Modify: `web/package.json`
- Create: `web/vitest.config.ts`
- Create: `web/src/test/setup.ts`
- Create: `web/src/pages/AgentsPage.test.tsx`

**Interfaces:**
- Consumes: `web/src/pages/AgentsPage.tsx` default export
- Produces: component test harness runnable with `npm test`-style Vitest commands and a failing Agents page test suite

- [ ] **Step 1: Write the failing test**

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AgentsPage from './AgentsPage'

vi.mock('./agentQueries', () => ({
  agentCatalogQueryKey: ['agents', 'catalog'],
  agentPreviewQueryKey: () => ['agents', 'preview'],
  fetchAgentCatalog: async () => ({
    ok: true,
    catalog: {
      templates: [
        {
          id: 'planner',
          label: 'Planner',
          description: 'Plans work',
          archetype: 'specialist',
          scope: 'workspace',
          status: 'stable',
          version: '1',
          source: 'bundled',
          ui: { category: 'General', sort_order: 1 },
          prompt_kinds: [],
          mcp_tools: [],
          recommended_skills: [],
          external_skills: [],
          vendors: ['claude_code'],
          delegates_to: [],
          delegated_by: [],
        },
      ],
    },
  }),
  fetchAgentPreview: async () => ({ ok: true, preview: { content: 'preview' } }),
  groupAgentsByCategory: (rows: Array<any>) => new Map([['General', rows]]),
  initAgentOverlay: async () => ({ ok: true }),
  objectivesQueryKey: ['agents', 'objectives'],
  fetchObjectives: async () => ({ ok: true, objectives: [] }),
  sessionDigestQueryKey: ['agents', 'session'],
  fetchSessionDigest: async () => ({ tier: 2, first_session: true, manifest_changed: false, repo_changes: [] }),
  beginSession: async () => ({ ok: true, workspace_name: 'demo', active_project: 'alpha', objectives: [], approvals: [], warnings: [], pack: { tier: 2 }, prompt: '', session: {}, schema_version: '1.0' }),
}))

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <AgentsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('AgentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Templates, Objectives, and Sessions tabs', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: 'Templates' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Objectives' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sessions' })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx`
Expected: FAIL because Vitest is not configured and/or the page does not render the new sub-tabs yet.

- [ ] **Step 3: Write minimal implementation**

`web/package.json`

```json
{
  "scripts": {
    "test": "vitest run"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.8.0",
    "@testing-library/react": "^16.3.0",
    "jsdom": "^26.1.0",
    "vitest": "^3.2.4"
  }
}
```

`web/vitest.config.ts`

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
})
```

`web/src/test/setup.ts`

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 4: Run test to verify it passes or fails for the right reason**

Run: `cd web && npm install && npx vitest run src/pages/AgentsPage.test.tsx`
Expected: The harness loads; the test now fails specifically because `AgentsPage` does not yet render `Templates`, `Objectives`, and `Sessions`.

- [ ] **Step 5: Commit**

```bash
git add web/package.json web/package-lock.json web/vitest.config.ts web/src/test/setup.ts web/src/pages/AgentsPage.test.tsx
git commit -m "test(web): add agents page test harness"
```

### Task 2: Add Agent Queries And Typed API Helpers For Objectives And Sessions

**Files:**
- Modify: `web/src/api/client.ts`
- Modify: `web/src/pages/agentQueries.ts`
- Test: `web/src/pages/AgentsPage.test.tsx`

**Interfaces:**
- Consumes: existing `requestJson`, current agent query helpers, existing ops endpoints
- Produces:
  - `getObjectives(): Promise<ObjectiveListResponse>`
  - `postObjective(body: ObjectiveUpsertRequest): Promise<ObjectiveRow>`
  - `patchObjective(id: string, body: ObjectiveEditRequest): Promise<ObjectiveRow>`
  - `getSessionDigest(): Promise<SessionDigestResponse>`
  - `postSessionBegin(body?: { project_name?: string; repo_name?: string; max_tokens?: number }): Promise<SessionBeginResponse>`
  - `objectivesQueryKey`
  - `fetchObjectives()`
  - `sessionDigestQueryKey`
  - `fetchSessionDigest()`
  - `beginSession()`

- [ ] **Step 1: Write the failing test**

Add this case to `web/src/pages/AgentsPage.test.tsx`:

```tsx
it('shows live update controls when Objectives is selected', async () => {
  renderPage()
  const objectivesTab = await screen.findByRole('button', { name: 'Objectives' })
  objectivesTab.click()
  expect(await screen.findByLabelText('Live update')).toBeInTheDocument()
  expect(screen.getByLabelText('Update frequency')).toHaveValue('90')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "shows live update controls when Objectives is selected"`
Expected: FAIL because the page has no live refresh controls and no objective/session data plumbing yet.

- [ ] **Step 3: Write minimal implementation**

`web/src/pages/agentQueries.ts`

```ts
import {
  getAgentCatalog,
  getAgentPreview,
  getObjectives,
  getSessionDigest,
  postAgentOverlayInit,
  postSessionBegin,
  type AgentCatalogEntry,
  type AgentCatalogResponse,
  type AgentOverlayInitOptions,
  type AgentOverlayInitResponse,
  type AgentPreviewResponse,
  type ObjectiveListResponse,
  type SessionBeginResponse,
  type SessionDigestResponse,
} from '../api/client'

export const objectivesQueryKey = ['agents', 'objectives'] as const
export const sessionDigestQueryKey = ['agents', 'session'] as const

export function fetchObjectives(): Promise<ObjectiveListResponse> {
  return getObjectives()
}

export function fetchSessionDigest(): Promise<SessionDigestResponse> {
  return getSessionDigest()
}

export function beginSession(body?: {
  project_name?: string
  repo_name?: string
  max_tokens?: number
}): Promise<SessionBeginResponse> {
  return postSessionBegin(body)
}
```

`web/src/api/client.ts`

```ts
export interface ObjectiveRow {
  id: string
  status: 'pending' | 'in_progress' | 'done' | 'cancelled'
  title: string
  repos: string[]
  acceptance?: string | null
  human_notes?: string | null
  agent_notes?: string | null
  created_at: string
  updated_at: string
}

export interface ObjectiveListResponse {
  ok: boolean
  objectives: ObjectiveRow[]
}

export interface SessionDigestResponse {
  tier: 2
  since?: string | null
  first_session: boolean
  manifest_changed: boolean
  active_objective_id?: string | null
  repo_changes: Array<{
    project_name: string
    repo_name: string
    repo_path: string
    commit_count: number
    recent_subjects: string[]
    error?: string | null
  }>
}

export interface SessionBeginResponse {
  ok: boolean
  schema_version: string
  workspace_name: string
  active_project?: string | null
  session: Record<string, unknown>
  objectives: ObjectiveRow[]
  approvals: ApprovalRequestRow[]
  pack: Record<string, unknown>
  prompt: string
  warnings: string[]
}
```

- [ ] **Step 4: Run test to verify it still fails for the UI gap only**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "shows live update controls when Objectives is selected"`
Expected: FAIL because the page still does not render the controls, but type/query imports resolve cleanly.

- [ ] **Step 5: Commit**

```bash
git add web/src/api/client.ts web/src/pages/agentQueries.ts web/src/pages/AgentsPage.test.tsx
git commit -m "test(web): add agents objectives and session query contracts"
```

### Task 3: Implement Agents Sub-Tabs And Templates Preservation

**Files:**
- Modify: `web/src/pages/AgentsPage.tsx`
- Modify: `web/src/pages/AgentsPage.module.css`
- Test: `web/src/pages/AgentsPage.test.tsx`

**Interfaces:**
- Consumes: `fetchAgentCatalog`, `fetchAgentPreview`, `groupAgentsByCategory`, `initAgentOverlay`
- Produces: page-level sub-tabs `Templates`, `Objectives`, `Sessions` while preserving the existing template catalog interactions inside the `Templates` panel

- [ ] **Step 1: Write the failing test**

Add this case to `web/src/pages/AgentsPage.test.tsx`:

```tsx
it('keeps template catalog functionality under the Templates tab', async () => {
  renderPage()
  expect(await screen.findByText('Planner')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Agent templates' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Templates' })).toHaveAttribute('aria-pressed', 'true')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "keeps template catalog functionality under the Templates tab"`
Expected: FAIL because the page does not yet expose the new sub-tab shell.

- [ ] **Step 3: Write minimal implementation**

`web/src/pages/AgentsPage.tsx`

```tsx
type AgentsTab = 'templates' | 'objectives' | 'sessions'

const REFRESH_OPTIONS = [30, 60, 90, 300] as const

export default function AgentsPage() {
  const [activeTab, setActiveTab] = useState<AgentsTab>('templates')
  const [liveUpdate, setLiveUpdate] = useState(true)
  const [refreshSeconds, setRefreshSeconds] = useState(90)

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Agents</h2>
          <p className={styles.subtitle}>Templates, objectives, and session context for collaborative agent work.</p>
        </div>
      </header>

      <div className={styles.pageTabs} role="tablist" aria-label="Agents sections">
        <button type="button" aria-pressed={activeTab === 'templates'} className={activeTab === 'templates' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('templates')}>Templates</button>
        <button type="button" aria-pressed={activeTab === 'objectives'} className={activeTab === 'objectives' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('objectives')}>Objectives</button>
        <button type="button" aria-pressed={activeTab === 'sessions'} className={activeTab === 'sessions' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('sessions')}>Sessions</button>
      </div>

      {activeTab === 'templates' ? <TemplatesPanel /> : null}
      {activeTab === 'objectives' ? <ObjectivesPanel liveUpdate={liveUpdate} refreshSeconds={refreshSeconds} onLiveUpdateChange={setLiveUpdate} onRefreshSecondsChange={setRefreshSeconds} /> : null}
      {activeTab === 'sessions' ? <SessionsPanel liveUpdate={liveUpdate} refreshSeconds={refreshSeconds} onLiveUpdateChange={setLiveUpdate} onRefreshSecondsChange={setRefreshSeconds} /> : null}
    </div>
  )
}
```

`web/src/pages/AgentsPage.module.css`

```css
.pageTabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  padding: 1rem;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "keeps template catalog functionality under the Templates tab"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/AgentsPage.tsx web/src/pages/AgentsPage.module.css web/src/pages/AgentsPage.test.tsx
git commit -m "feat(web): add agents page sub-tabs shell"
```

### Task 4: Implement Objectives Panel With Grouped Editable Cards

**Files:**
- Modify: `web/src/pages/AgentsPage.tsx`
- Modify: `web/src/pages/AgentsPage.module.css`
- Test: `web/src/pages/AgentsPage.test.tsx`

**Interfaces:**
- Consumes:
  - `fetchObjectives(): Promise<ObjectiveListResponse>`
  - `postObjective(body: ObjectiveUpsertRequest): Promise<ObjectiveRow>`
  - `patchObjective(id: string, body: ObjectiveEditRequest): Promise<ObjectiveRow>`
- Produces:
  - grouped objectives render by status
  - create form
  - save mutation with query invalidation

- [ ] **Step 1: Write the failing test**

Add these cases to `web/src/pages/AgentsPage.test.tsx`:

```tsx
it('groups objectives by status', async () => {
  renderPage()
  screen.getByRole('button', { name: 'Objectives' }).click()
  expect(await screen.findByRole('heading', { name: 'Pending' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'In Progress' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Done' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Cancelled' })).toBeInTheDocument()
})

it('shows agent notes as read-only and human notes as editable', async () => {
  renderPage()
  screen.getByRole('button', { name: 'Objectives' }).click()
  expect(await screen.findByText('Agent notes')).toBeInTheDocument()
  expect(screen.getByLabelText('Human notes')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "groups objectives by status|shows agent notes as read-only and human notes as editable"`
Expected: FAIL because the objectives panel does not exist yet.

- [ ] **Step 3: Write minimal implementation**

`web/src/pages/AgentsPage.tsx`

```tsx
const OBJECTIVE_GROUPS = [
  ['pending', 'Pending'],
  ['in_progress', 'In Progress'],
  ['done', 'Done'],
  ['cancelled', 'Cancelled'],
] as const

function ObjectivesPanel(props: RefreshProps) {
  const queryClient = useQueryClient()
  const { data, refetch, isLoading, isError, error } = useQuery({
    queryKey: objectivesQueryKey,
    queryFn: fetchObjectives,
    refetchInterval: props.liveUpdate ? props.refreshSeconds * 1000 : false,
  })

  const createMutation = useMutation({
    mutationFn: postObjective,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: objectivesQueryKey })
    },
  })

  const saveMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: ObjectiveEditRequest }) => patchObjective(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: objectivesQueryKey })
    },
  })

  const objectives = data?.objectives ?? []
  return (
    <section className={styles.panel}>
      <RefreshControls {...props} onRefresh={() => void refetch()} />
      {OBJECTIVE_GROUPS.map(([status, label]) => (
        <div key={status}>
          <h3>{label}</h3>
          {objectives.filter((item) => item.status === status).map((item) => (
            <ObjectiveCard key={item.id} objective={item} onSave={(body) => saveMutation.mutate({ id: item.id, body })} />
          ))}
        </div>
      ))}
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "groups objectives by status|shows agent notes as read-only and human notes as editable"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/AgentsPage.tsx web/src/pages/AgentsPage.module.css web/src/pages/AgentsPage.test.tsx
git commit -m "feat(web): add agents objectives panel"
```

### Task 5: Implement Sessions Panel With Digest View And Begin Action

**Files:**
- Modify: `web/src/pages/AgentsPage.tsx`
- Modify: `web/src/pages/AgentsPage.module.css`
- Test: `web/src/pages/AgentsPage.test.tsx`

**Interfaces:**
- Consumes:
  - `fetchSessionDigest(): Promise<SessionDigestResponse>`
  - `beginSession(): Promise<SessionBeginResponse>`
  - `objectivesQueryKey`
  - `sessionDigestQueryKey`
- Produces:
  - session summary card
  - repo change list
  - begin-session action with compact result summary and cross-panel refresh

- [ ] **Step 1: Write the failing test**

Add these cases to `web/src/pages/AgentsPage.test.tsx`:

```tsx
it('renders session digest summary and repo changes', async () => {
  renderPage()
  screen.getByRole('button', { name: 'Sessions' }).click()
  expect(await screen.findByText('Active objective')).toBeInTheDocument()
  expect(screen.getByText('Recent repo changes')).toBeInTheDocument()
})

it('runs begin session and shows compact result summary', async () => {
  renderPage()
  screen.getByRole('button', { name: 'Sessions' }).click()
  const beginButton = await screen.findByRole('button', { name: 'Begin session' })
  beginButton.click()
  expect(await screen.findByText(/workspace name/i)).toBeInTheDocument()
  expect(screen.getByText(/pending approvals/i)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "renders session digest summary and repo changes|runs begin session and shows compact result summary"`
Expected: FAIL because the sessions panel does not exist yet.

- [ ] **Step 3: Write minimal implementation**

`web/src/pages/AgentsPage.tsx`

```tsx
function SessionsPanel(props: RefreshProps) {
  const queryClient = useQueryClient()
  const [summary, setSummary] = useState<SessionBeginResponse | null>(null)
  const { data, refetch } = useQuery({
    queryKey: sessionDigestQueryKey,
    queryFn: fetchSessionDigest,
    refetchInterval: props.liveUpdate ? props.refreshSeconds * 1000 : false,
  })

  const beginMutation = useMutation({
    mutationFn: () => beginSession(),
    onSuccess: async (result) => {
      setSummary(result)
      await queryClient.invalidateQueries({ queryKey: sessionDigestQueryKey })
      await queryClient.invalidateQueries({ queryKey: objectivesQueryKey })
    },
  })

  return (
    <section className={styles.panel}>
      <RefreshControls {...props} onRefresh={() => void refetch()} />
      <div className={styles.summaryCard}>
        <p><strong>Active objective</strong> {data?.active_objective_id ?? '—'}</p>
        <p><strong>First session</strong> {data?.first_session ? 'Yes' : 'No'}</p>
        <p><strong>Manifest changed</strong> {data?.manifest_changed ? 'Yes' : 'No'}</p>
      </div>
      <h3>Recent repo changes</h3>
      <button type="button" onClick={() => beginMutation.mutate()}>Begin session</button>
      {summary ? (
        <div className={styles.summaryCard}>
          <p><strong>Workspace name</strong> {summary.workspace_name}</p>
          <p><strong>Active project</strong> {summary.active_project ?? '—'}</p>
          <p><strong>Objectives</strong> {summary.objectives.length}</p>
          <p><strong>Pending approvals</strong> {summary.approvals.length}</p>
          <p><strong>Warnings</strong> {summary.warnings.length}</p>
        </div>
      ) : null}
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "renders session digest summary and repo changes|runs begin session and shows compact result summary"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/AgentsPage.tsx web/src/pages/AgentsPage.module.css web/src/pages/AgentsPage.test.tsx
git commit -m "feat(web): add agents sessions panel"
```

### Task 6: Final Styling, Docs, And Verification

**Files:**
- Modify: `web/src/pages/AgentsPage.module.css`
- Modify: `docs/reference/metagit-web.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: completed sub-tab panels and existing docs/changelog structure
- Produces: polished styling, updated docs, and verified delivery commands

- [ ] **Step 1: Write the failing test**

Add this case to `web/src/pages/AgentsPage.test.tsx`:

```tsx
it('defaults live update frequency to 90 seconds', async () => {
  renderPage()
  screen.getByRole('button', { name: 'Sessions' }).click()
  expect(await screen.findByLabelText('Update frequency')).toHaveValue('90')
})
```

- [ ] **Step 2: Run test to verify it fails or exposes final UI gaps**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx -t "defaults live update frequency to 90 seconds"`
Expected: FAIL if the control value or labeling is still inconsistent.

- [ ] **Step 3: Write minimal implementation**

`web/src/pages/AgentsPage.module.css`

```css
.refreshBar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.summaryCard {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  padding: 0.75rem;
}

.objectiveGrid {
  display: grid;
  gap: 0.75rem;
}
```

`docs/reference/metagit-web.md`

```md
- `/agents` now includes `Templates`, `Objectives`, and `Sessions` sub-tabs.
- `Objectives` supports collaborative editing against `/v3/ops/objectives`.
- `Sessions` shows the current digest from `/v3/ops/session` and supports `POST /v3/ops/session/begin`.
- Live refresh controls default to 90 seconds and can be disabled for manual refresh.
```

`CHANGELOG.md`

```md
### Changed
- The web `/agents` route now includes `Templates`, `Objectives`, and `Sessions` sub-tabs with collaborative objective editing and session digest controls.
```

- [ ] **Step 4: Run tests and project verification**

Run: `cd web && npx vitest run src/pages/AgentsPage.test.tsx`
Expected: PASS

Run: `cd web && npm run build`
Expected: PASS

Run: `cd /Users/zacharyloeber/Zach-Projects/Personal/active/metagit-cli && task qa:prepush`
Expected: PASS

Run: `cd /Users/zacharyloeber/Zach-Projects/Personal/active/metagit-cli && task gitnexus:analyze`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/AgentsPage.module.css web/src/pages/AgentsPage.tsx web/src/pages/AgentsPage.test.tsx docs/reference/metagit-web.md CHANGELOG.md
git commit -m "feat(web): add agents objectives and sessions console"
```

## Self-Review

- Spec coverage: the plan covers the approved `/agents` sub-tab split, objectives CRUD surface, session digest + begin action, live refresh controls, templates preservation, and repo QA/docs updates.
- Placeholder scan: no `TBD`, `TODO`, or deferred implementation markers remain.
- Type consistency: the same response and helper names are used across the tasks (`ObjectiveRow`, `SessionDigestResponse`, `SessionBeginResponse`, `fetchObjectives`, `fetchSessionDigest`, `beginSession`).