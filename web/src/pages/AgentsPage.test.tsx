import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AgentsPage from './AgentsPage'

const patchObjectiveMock = vi.fn()
const fetchSessionDigestMock = vi.fn(async () => ({
  tier: 2,
  since: '2026-06-24T09:00:00Z',
  first_session: false,
  manifest_changed: true,
  active_objective_id: 'obj-progress',
  repo_changes: [
    {
      project_name: 'workspace-console',
      repo_name: 'metagit-cli',
      repo_path: '/tmp/metagit-cli',
      commit_count: 3,
      recent_subjects: ['feat: add sessions tab', 'test: add panel coverage'],
      error: null,
    },
  ],
}))
const beginSessionMock = vi.fn(async () => ({
  ok: true,
  workspace_name: 'demo',
  active_project: 'alpha',
  objectives: [
    {
      id: 'obj-progress',
      status: 'in_progress',
      title: 'Refine workspace prompts',
      repos: ['src', 'docs'],
      acceptance: 'Prompt pack matches session-start flow',
      human_notes: 'Check wording with router docs',
      agent_notes: 'Prompt variants already narrowed to two options.',
      created_at: '2026-06-24T10:10:00Z',
      updated_at: '2026-06-24T11:10:00Z',
    },
  ],
  approvals: [
    {
      id: 'approval-1',
      kind: 'confirm',
      status: 'pending',
      title: 'Approve session scope',
      detail: 'Need approval before broader refresh',
      created_at: '2026-06-24T12:00:00Z',
      updated_at: '2026-06-24T12:00:00Z',
    },
  ],
  warnings: ['Workspace has unstaged docs changes'],
  pack: { tier: 2 },
  prompt: '',
  session: {},
  schema_version: '1.0',
}))
const fetchObjectivesMock = vi.fn(async () => ({
  ok: true,
  objectives: [
    {
      id: 'obj-pending',
      status: 'pending',
      title: 'Draft agent onboarding guide',
      repos: ['docs'],
      acceptance: 'Guide covers install and usage',
      human_notes: 'Need final walkthrough notes',
      agent_notes: 'Suggested outline generated from existing docs.',
      created_at: '2026-06-24T10:00:00Z',
      updated_at: '2026-06-24T11:00:00Z',
    },
    {
      id: 'obj-progress',
      status: 'in_progress',
      title: 'Refine workspace prompts',
      repos: ['src', 'docs'],
      acceptance: 'Prompt pack matches session-start flow',
      human_notes: 'Check wording with router docs',
      agent_notes: 'Prompt variants already narrowed to two options.',
      created_at: '2026-06-24T10:10:00Z',
      updated_at: '2026-06-24T11:10:00Z',
    },
    {
      id: 'obj-done',
      status: 'done',
      title: 'Ship template shell',
      repos: ['web'],
      acceptance: 'Templates tab remains intact',
      human_notes: 'Completed in prior task',
      agent_notes: 'Preview + overlay actions verified.',
      created_at: '2026-06-24T10:20:00Z',
      updated_at: '2026-06-24T11:20:00Z',
    },
    {
      id: 'obj-cancelled',
      status: 'cancelled',
      title: 'Prototype websocket updates',
      repos: ['web'],
      acceptance: 'Not needed for polling milestone',
      human_notes: 'Deferred from current scope',
      agent_notes: 'Polling path is sufficient for this phase.',
      created_at: '2026-06-24T10:30:00Z',
      updated_at: '2026-06-24T11:30:00Z',
    },
  ],
}))

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
  fetchObjectives: () => fetchObjectivesMock(),
  saveObjective: (...args: Array<any>) => patchObjectiveMock(...args),
  sessionDigestQueryKey: ['agents', 'session'],
  fetchSessionDigest: () => fetchSessionDigestMock(),
  beginSession: () => beginSessionMock(),
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
    patchObjectiveMock.mockResolvedValue({
      id: 'obj-pending',
      status: 'pending',
      title: 'Draft agent onboarding guide',
      repos: ['docs'],
      acceptance: 'Guide covers install and usage',
      human_notes: 'Updated by test',
      agent_notes: 'Suggested outline generated from existing docs.',
      created_at: '2026-06-24T10:00:00Z',
      updated_at: '2026-06-24T11:15:00Z',
    })
    fetchSessionDigestMock.mockClear()
    beginSessionMock.mockClear()
  })

  it('renders Templates, Objectives, and Sessions tabs', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: 'Templates' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Objectives' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sessions' })).toBeInTheDocument()
  })

  it('shows live update controls when Objectives is selected', async () => {
    renderPage()
    const objectivesTab = await screen.findByRole('button', { name: 'Objectives' })
    fireEvent.click(objectivesTab)
    expect(await screen.findByLabelText('Live update')).toBeInTheDocument()
    expect(screen.getByLabelText('Update frequency')).toHaveValue('90')
  })

  it('keeps template catalog functionality under the Templates tab', async () => {
    renderPage()
    expect(await screen.findByText('Planner')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Agent templates' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Templates' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('groups objectives by status', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Objectives' }))

    expect(await screen.findByRole('heading', { name: 'Pending' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'In Progress' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Done' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Cancelled' })).toBeInTheDocument()
    expect(screen.getByText('Draft agent onboarding guide')).toBeInTheDocument()
    expect(screen.getByText('Refine workspace prompts')).toBeInTheDocument()
    expect(screen.getByText('Ship template shell')).toBeInTheDocument()
    expect(screen.getByText('Prototype websocket updates')).toBeInTheDocument()
  })

  it('shows agent notes as read-only and human notes as editable', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Objectives' }))

    expect(await screen.findAllByText('Agent notes')).toHaveLength(4)
    expect(screen.getByText('Suggested outline generated from existing docs.')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Human notes')).toHaveLength(4)
  })

  it('saves edited human notes through the objective patch helper', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Objectives' }))

    const notesFields = await screen.findAllByLabelText('Human notes')
    fireEvent.change(notesFields[0], { target: { value: 'Updated by test' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save changes' })[0])

    await waitFor(() => {
      expect(patchObjectiveMock).toHaveBeenCalledWith('obj-pending', {
        title: 'Draft agent onboarding guide',
        status: 'pending',
        repos: ['docs'],
        acceptance: 'Guide covers install and usage',
        human_notes: 'Updated by test',
      })
    })
  })

  it('allows updating objective status before saving', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Objectives' }))

    const statusFields = await screen.findAllByLabelText('Status')
    fireEvent.change(statusFields[0], { target: { value: 'done' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save changes' })[0])

    await waitFor(() => {
      expect(patchObjectiveMock).toHaveBeenCalledWith('obj-pending', {
        title: 'Draft agent onboarding guide',
        status: 'done',
        repos: ['docs'],
        acceptance: 'Guide covers install and usage',
        human_notes: 'Need final walkthrough notes',
      })
    })
  })

  it('supports alternate list view with inline editing', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Objectives' }))

    fireEvent.click(await screen.findByRole('tab', { name: 'List view' }))
    expect(screen.getByRole('tab', { name: 'Grouped view' })).toBeInTheDocument()

    const row = await screen.findByRole('article', { name: /Draft agent onboarding guide/i })
    fireEvent.change(within(row).getByLabelText('Human notes'), {
      target: { value: 'List edit note' },
    })
    fireEvent.change(within(row).getByLabelText('Status'), {
      target: { value: 'in_progress' },
    })
    fireEvent.click(within(row).getByRole('button', { name: 'Save changes' }))

    await waitFor(() => {
      expect(patchObjectiveMock).toHaveBeenCalledWith('obj-pending', {
        title: 'Draft agent onboarding guide',
        status: 'in_progress',
        repos: ['docs'],
        acceptance: 'Guide covers install and usage',
        human_notes: 'List edit note',
      })
    })
  })

  it('renders session digest summary and repo changes', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Sessions' }))

    expect(await screen.findByText('Active objective')).toBeInTheDocument()
    expect(screen.getByText('obj-progress')).toBeInTheDocument()
    expect(screen.getByText('First session')).toBeInTheDocument()
    expect(screen.getByText('No')).toBeInTheDocument()
    expect(screen.getByText('Manifest changed')).toBeInTheDocument()
    expect(screen.getByText('Yes')).toBeInTheDocument()
    expect(screen.getByText('Recent repo changes')).toBeInTheDocument()
    expect(screen.getByText('workspace-console / metagit-cli')).toBeInTheDocument()
    expect(screen.getByText('3 commits')).toBeInTheDocument()
    expect(screen.getByText('feat: add sessions tab')).toBeInTheDocument()
    expect(screen.getByText('test: add panel coverage')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Begin session' })).toBeInTheDocument()
    expect(screen.getByLabelText('Live update')).toBeInTheDocument()
    expect(screen.getByLabelText('Update frequency')).toHaveValue('90')
  })

  it('runs begin session, shows compact result summary, and refreshes digest plus objectives', async () => {
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Objectives' }))
    await screen.findByText('Draft agent onboarding guide')
    expect(fetchObjectivesMock).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Sessions' }))
    const beginButton = await screen.findByRole('button', { name: 'Begin session' })
    expect(fetchSessionDigestMock).toHaveBeenCalledTimes(1)

    fireEvent.click(beginButton)

    expect(await screen.findByText('Workspace name')).toBeInTheDocument()
    expect(screen.getByText('demo')).toBeInTheDocument()
    expect(screen.getByText('Active project')).toBeInTheDocument()
    expect(screen.getByText('alpha')).toBeInTheDocument()
    const beginSummary = screen.getByLabelText('Begin session summary')
    expect(within(beginSummary).getByText('Objectives count')).toBeInTheDocument()
    expect(within(beginSummary).getAllByText('1')).toHaveLength(3)
    expect(within(beginSummary).getByText('Pending approvals count')).toBeInTheDocument()
    expect(within(beginSummary).getByText('Warnings count')).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchSessionDigestMock.mock.calls.length).toBeGreaterThanOrEqual(2)
      expect(fetchObjectivesMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })
  })
})