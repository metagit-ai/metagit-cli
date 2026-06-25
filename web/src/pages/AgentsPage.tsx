import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  type AgentCatalogEntry,
  type ObjectiveEditRequest,
  type ObjectiveRow,
  type ObjectiveStatus,
} from '../api/client'
import {
  agentCatalogQueryKey,
  agentPreviewQueryKey,
  beginSession,
  fetchAgentCatalog,
  fetchAgentPreview,
  fetchObjectives,
  fetchSessionDigest,
  groupAgentsByCategory,
  initAgentOverlay,
  objectivesQueryKey,
  sessionDigestQueryKey,
  saveObjective,
} from './agentQueries'
import styles from './AgentsPage.module.css'

const VENDORS = [
  'claude_code',
  'cursor',
  'github_copilot',
  'hermes',
  'openclaw',
  'opencode',
  'windsurf',
  'codex',
] as const

const REFRESH_OPTIONS = [30, 60, 90, 300] as const

type AgentsTab = 'templates' | 'objectives' | 'sessions'
type DetailTab = 'metadata' | 'preview'

type RefreshPanelProps = {
  liveUpdate: boolean
  refreshSeconds: number
  onLiveUpdateChange: (value: boolean) => void
  onRefreshSecondsChange: (value: number) => void
}

type ObjectiveDraft = {
  title: string
  status: ObjectiveStatus
  acceptance: string
  human_notes: string
  repos: string[]
}

const OBJECTIVE_GROUPS: Array<{ status: ObjectiveStatus; label: string }> = [
  { status: 'pending', label: 'Pending' },
  { status: 'in_progress', label: 'In Progress' },
  { status: 'done', label: 'Done' },
  { status: 'cancelled', label: 'Cancelled' },
]

export default function AgentsPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<AgentsTab>('templates')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<DetailTab>('metadata')
  const [previewVendor, setPreviewVendor] = useState<string>('claude_code')
  const [overlayMessage, setOverlayMessage] = useState<string | null>(null)
  const [liveUpdate, setLiveUpdate] = useState(true)
  const [refreshSeconds, setRefreshSeconds] = useState<number>(90)

  const overlayInit = useMutation({
    mutationFn: (templateId: string) =>
      initAgentOverlay(templateId, {
        mode: 'full',
        force: false,
      }),
    onSuccess: (response) => {
      if (!response.ok || !response.overlay) {
        setOverlayMessage(response.error?.message ?? 'Overlay init failed.')
        return
      }
      setOverlayMessage(
        `Overlay ready at ${response.overlay.overlay_path} (${response.overlay.scope}) — commit .metagit-agents/ to git.`,
      )
      void queryClient.invalidateQueries({ queryKey: agentCatalogQueryKey })
    },
    onError: (mutationError: Error) => {
      setOverlayMessage(mutationError.message)
    },
  })

  const { data, isLoading, isError, error } = useQuery({
    queryKey: agentCatalogQueryKey,
    queryFn: fetchAgentCatalog,
  })

  const templates = data?.catalog.templates ?? []
  const grouped = useMemo(() => groupAgentsByCategory(templates), [templates])
  const selected = templates.find((entry) => entry.id === selectedId) ?? null

  const {
    data: previewData,
    isLoading: previewLoading,
    isError: previewError,
  } = useQuery({
    queryKey: agentPreviewQueryKey(selectedId ?? '', previewVendor),
    queryFn: () => fetchAgentPreview(selectedId as string, previewVendor),
    enabled: detailTab === 'preview' && selectedId !== null,
  })

  const installCommand = selected
    ? `metagit agent create ${selected.id} --vendor ${previewVendor}`
    : ''

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Agents</h2>
          <p className={styles.subtitle}>
            Templates, objectives, and session context for collaborative agent work.
          </p>
        </div>
      </header>

      <div className={styles.pageTabs} role="tablist" aria-label="Agents sections">
        <button
          type="button"
          aria-pressed={activeTab === 'templates'}
          className={activeTab === 'templates' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('templates')}
        >
          Templates
        </button>
        <button
          type="button"
          aria-pressed={activeTab === 'objectives'}
          className={activeTab === 'objectives' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('objectives')}
        >
          Objectives
        </button>
        <button
          type="button"
          aria-pressed={activeTab === 'sessions'}
          className={activeTab === 'sessions' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('sessions')}
        >
          Sessions
        </button>
      </div>

      {activeTab === 'templates' ? (
        <>
          {isLoading ? <p className={styles.status}>Loading catalog…</p> : null}
          {isError ? (
            <p className={styles.error}>
              Failed to load catalog: {error instanceof Error ? error.message : 'unknown error'}
            </p>
          ) : null}

          {!isLoading && !isError ? (
            <>
              <section className={styles.panel} aria-label="Templates panel">
                <h3 className={styles.detailTitle}>Agent templates</h3>
                <p className={styles.subtitle}>
                  Bundled archetypes for Metagit-managed workspaces. Team overlays live in
                  `.metagit-agents/` (commit to git); personal overrides use `.metagit/.agent-templates/`.
                </p>
              </section>

              {[...grouped.entries()].map(([category, entries]) => (
                <section key={category} className={styles.section}>
                  <h3 className={styles.sectionTitle}>{category}</h3>
                  <div className={styles.grid}>
                    {entries.map((entry) => (
                      <AgentCard
                        key={entry.id}
                        entry={entry}
                        active={entry.id === selectedId}
                        onSelect={() => {
                          setSelectedId(entry.id)
                          setDetailTab('metadata')
                        }}
                      />
                    ))}
                  </div>
                </section>
              ))}

              {selected ? (
                <section className={styles.detail} aria-label="Template detail">
                  <h3 className={styles.detailTitle}>{selected.label}</h3>
                  <p>{selected.description}</p>
                  <div className={styles.previewControls}>
                    {selected.source === 'bundled' ? (
                      <button
                        type="button"
                        className={styles.copyButton}
                        disabled={overlayInit.isPending}
                        onClick={() => {
                          setOverlayMessage(null)
                          overlayInit.mutate(selected.id)
                        }}
                      >
                        {overlayInit.isPending
                          ? 'Creating overlay…'
                          : 'Create team overlay (.metagit-agents)'}
                      </button>
                    ) : (
                      <p className={styles.subtitle}>
                        Overlay path:{' '}
                        <code>{selected.overlay_path ?? `.metagit/.agent-templates/${selected.id}`}</code>
                      </p>
                    )}
                    {overlayMessage ? <p className={styles.status}>{overlayMessage}</p> : null}
                  </div>
                  <div className={styles.tabs}>
                    <button
                      type="button"
                      className={detailTab === 'metadata' ? styles.tabActive : styles.tab}
                      onClick={() => setDetailTab('metadata')}
                    >
                      Metadata
                    </button>
                    <button
                      type="button"
                      className={detailTab === 'preview' ? styles.tabActive : styles.tab}
                      onClick={() => setDetailTab('preview')}
                    >
                      Preview
                    </button>
                  </div>

                  {detailTab === 'metadata' ? (
                    <MetadataPanel entry={selected} />
                  ) : (
                    <div>
                      <div className={styles.previewControls}>
                        <label htmlFor="agent-vendor">Vendor</label>
                        <select
                          id="agent-vendor"
                          className={styles.select}
                          value={previewVendor}
                          onChange={(event) => setPreviewVendor(event.target.value)}
                        >
                          {VENDORS.map((vendor) => (
                            <option key={vendor} value={vendor}>
                              {vendor}
                            </option>
                          ))}
                        </select>
                      </div>
                      {previewLoading ? <p className={styles.status}>Rendering preview…</p> : null}
                      {previewError ? <p className={styles.error}>Failed to load preview.</p> : null}
                      {previewData?.preview.content ? (
                        <pre className={styles.previewBox}>{previewData.preview.content}</pre>
                      ) : null}
                    </div>
                  )}

                  <div>
                    <p className={styles.subtitle}>Install command</p>
                    <div className={styles.installBox}>
                      <input
                        className={styles.installInput}
                        readOnly
                        value={installCommand}
                        aria-label="Install command"
                      />
                      <button
                        type="button"
                        className={styles.copyButton}
                        onClick={() => navigator.clipboard.writeText(installCommand)}
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                </section>
              ) : null}
            </>
          ) : null}
        </>
      ) : null}

      {activeTab === 'objectives' ? (
        <ObjectivesPanel
          liveUpdate={liveUpdate}
          refreshSeconds={refreshSeconds}
          onLiveUpdateChange={setLiveUpdate}
          onRefreshSecondsChange={setRefreshSeconds}
        />
      ) : null}

      {activeTab === 'sessions' ? (
        <SessionsPanel
          liveUpdate={liveUpdate}
          refreshSeconds={refreshSeconds}
          onLiveUpdateChange={setLiveUpdate}
          onRefreshSecondsChange={setRefreshSeconds}
        />
      ) : null}
    </div>
  )
}

function ObjectivesPanel({
  liveUpdate,
  refreshSeconds,
  onLiveUpdateChange,
  onRefreshSecondsChange,
}: RefreshPanelProps) {
  const queryClient = useQueryClient()
  const [savingId, setSavingId] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: objectivesQueryKey,
    queryFn: fetchObjectives,
    refetchInterval: liveUpdate ? refreshSeconds * 1000 : false,
  })

  const saveMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: ObjectiveEditRequest }) => saveObjective(id, body),
    onMutate: ({ id }) => {
      setSavingId(id)
      setSaveMessage(null)
      setSaveError(null)
    },
    onSuccess: async (row) => {
      setSaveMessage(`Saved ${row.title}.`)
      await queryClient.invalidateQueries({ queryKey: objectivesQueryKey })
    },
    onError: (mutationError: Error) => {
      setSaveError(mutationError.message)
    },
    onSettled: () => {
      setSavingId(null)
    },
  })

  const objectives = data?.objectives ?? []

  return (
    <section className={styles.panel} aria-label="Objectives panel">
      <div className={styles.objectivesHeader}>
        <div>
          <h3 className={styles.detailTitle}>Objectives</h3>
          <p className={styles.subtitle}>
            Review agent-authored notes, update human notes, and keep objective status grouped by workflow state.
          </p>
        </div>
        <RefreshControls
          liveUpdate={liveUpdate}
          refreshSeconds={refreshSeconds}
          onLiveUpdateChange={onLiveUpdateChange}
          onRefreshSecondsChange={onRefreshSecondsChange}
          frequencyId="Objectives-refresh-frequency"
          onRefresh={() => void refetch()}
        />
      </div>

      {isLoading ? <p className={styles.status}>Loading objectives…</p> : null}
      {isError ? (
        <p className={styles.error}>
          Failed to load objectives: {error instanceof Error ? error.message : 'unknown error'}
        </p>
      ) : null}
      {saveMessage ? <p className={styles.status}>{saveMessage}</p> : null}
      {saveError ? <p className={styles.error}>{saveError}</p> : null}

      {!isLoading && !isError ? (
        <div className={styles.objectiveGroups}>
          {OBJECTIVE_GROUPS.map((group) => {
            const groupObjectives = objectives.filter((item) => item.status === group.status)
            return (
              <section key={group.status} className={styles.objectiveSection}>
                <div className={styles.objectiveSectionHeader}>
                  <h4 className={styles.sectionTitle}>{group.label}</h4>
                  <span className={styles.objectiveCount}>{groupObjectives.length}</span>
                </div>

                {groupObjectives.length ? (
                  <div className={styles.objectiveList}>
                    {groupObjectives.map((objective) => (
                      <ObjectiveCard
                        key={objective.id}
                        objective={objective}
                        isSaving={savingId === objective.id && saveMutation.isPending}
                        onSave={(body) => saveMutation.mutate({ id: objective.id, body })}
                      />
                    ))}
                  </div>
                ) : (
                  <p className={styles.emptyState}>No objectives in this group.</p>
                )}
              </section>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}

function SessionsPanel({
  liveUpdate,
  refreshSeconds,
  onLiveUpdateChange,
  onRefreshSecondsChange,
}: RefreshPanelProps) {
  const queryClient = useQueryClient()
  const [beginSummary, setBeginSummary] = useState<{
    workspaceName: string
    activeProject: string | null
    objectivesCount: number
    pendingApprovalsCount: number
    warningsCount: number
  } | null>(null)
  const [beginError, setBeginError] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: sessionDigestQueryKey,
    queryFn: fetchSessionDigest,
    refetchInterval: liveUpdate ? refreshSeconds * 1000 : false,
  })

  const beginMutation = useMutation({
    mutationFn: () => beginSession(),
    onMutate: () => {
      setBeginError(null)
    },
    onSuccess: async (result) => {
      setBeginSummary({
        workspaceName: result.workspace_name,
        activeProject: result.active_project ?? null,
        objectivesCount: result.objectives.length,
        pendingApprovalsCount: result.approvals.filter((approval) => approval.status === 'pending')
          .length,
        warningsCount: result.warnings.length,
      })
      await Promise.all([
        queryClient.fetchQuery({ queryKey: sessionDigestQueryKey, queryFn: fetchSessionDigest }),
        queryClient.fetchQuery({ queryKey: objectivesQueryKey, queryFn: fetchObjectives }),
      ])
    },
    onError: (mutationError: Error) => {
      setBeginError(mutationError.message)
    },
  })

  return (
    <section className={styles.panel} aria-label="Sessions panel">
      <div className={styles.objectivesHeader}>
        <div>
          <h3 className={styles.detailTitle}>Sessions</h3>
          <p className={styles.subtitle}>
            Review the current session digest, inspect recent repo activity, and begin a fresh
            session pack.
          </p>
        </div>
        <RefreshControls
          liveUpdate={liveUpdate}
          refreshSeconds={refreshSeconds}
          onLiveUpdateChange={onLiveUpdateChange}
          onRefreshSecondsChange={onRefreshSecondsChange}
          frequencyId="Sessions-refresh-frequency"
          onRefresh={() => void refetch()}
        />
      </div>

      {isLoading ? <p className={styles.status}>Loading session digest…</p> : null}
      {isError ? (
        <p className={styles.error}>
          Failed to load session digest: {error instanceof Error ? error.message : 'unknown error'}
        </p>
      ) : null}
      {beginError ? <p className={styles.error}>{beginError}</p> : null}

      {!isLoading && !isError ? (
        <>
          <section className={styles.summaryCard} aria-label="Session digest summary">
            <div className={styles.summaryItem}>
              <span className={styles.objectiveLabel}>Active objective</span>
              <strong>{data?.active_objective_id ?? 'None'}</strong>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.objectiveLabel}>First session</span>
              <strong>{data?.first_session ? 'Yes' : 'No'}</strong>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.objectiveLabel}>Manifest changed</span>
              <strong>{data?.manifest_changed ? 'Yes' : 'No'}</strong>
            </div>
          </section>

          <div className={styles.sessionsHeader}>
            <h4 className={styles.sectionTitle}>Recent repo changes</h4>
            <button
              type="button"
              className={styles.copyButton}
              disabled={beginMutation.isPending}
              onClick={() => beginMutation.mutate()}
            >
              {beginMutation.isPending ? 'Beginning…' : 'Begin session'}
            </button>
          </div>

          {data?.repo_changes.length ? (
            <div className={styles.sessionRepoList}>
              {data.repo_changes.map((change) => (
                <article
                  key={`${change.project_name}-${change.repo_name}-${change.repo_path}`}
                  className={styles.sessionRepoCard}
                >
                  <div className={styles.objectiveCardHeader}>
                    <div>
                      <h5 className={styles.cardTitle}>
                        {change.project_name} / {change.repo_name}
                      </h5>
                      <p className={styles.cardDescription}>{change.repo_path}</p>
                    </div>
                    <span className={styles.badge}>
                      {change.commit_count} {change.commit_count === 1 ? 'commit' : 'commits'}
                    </span>
                  </div>

                  {change.error ? <p className={styles.error}>{change.error}</p> : null}

                  {change.recent_subjects.length ? (
                    <ul className={styles.list}>
                      {change.recent_subjects.map((subject) => (
                        <li key={subject}>{subject}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className={styles.emptyState}>No recent subjects recorded.</p>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p className={styles.emptyState}>No repo changes in the current session digest.</p>
          )}

          {beginSummary ? (
            <section className={styles.summaryCard} aria-label="Begin session summary">
              <div className={styles.summaryItem}>
                <span className={styles.objectiveLabel}>Workspace name</span>
                <strong>{beginSummary.workspaceName}</strong>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.objectiveLabel}>Active project</span>
                <strong>{beginSummary.activeProject ?? 'None'}</strong>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.objectiveLabel}>Objectives count</span>
                <strong>{beginSummary.objectivesCount}</strong>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.objectiveLabel}>Pending approvals count</span>
                <strong>{beginSummary.pendingApprovalsCount}</strong>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.objectiveLabel}>Warnings count</span>
                <strong>{beginSummary.warningsCount}</strong>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  )
}

function RefreshControls({
  liveUpdate,
  refreshSeconds,
  onLiveUpdateChange,
  onRefreshSecondsChange,
  frequencyId,
  onRefresh,
}: RefreshPanelProps & {
  frequencyId: string
  onRefresh?: () => void
}) {
  return (
    <div className={styles.refreshControls}>
      <label className={styles.checkboxLabel}>
        <input
          type="checkbox"
          checked={liveUpdate}
          onChange={(event) => onLiveUpdateChange(event.target.checked)}
        />
        Live update
      </label>
      <label className={styles.selectLabel} htmlFor={frequencyId}>
        Update frequency
      </label>
      <select
        id={frequencyId}
        className={styles.select}
        value={String(refreshSeconds)}
        onChange={(event) => onRefreshSecondsChange(Number(event.target.value))}
      >
        {REFRESH_OPTIONS.map((seconds) => (
          <option key={seconds} value={seconds}>
            {seconds} seconds
          </option>
        ))}
      </select>
      {onRefresh ? (
        <button type="button" className={styles.copyButton} onClick={onRefresh}>
          Refresh now
        </button>
      ) : null}
    </div>
  )
}

function ObjectiveCard({
  objective,
  isSaving,
  onSave,
}: {
  objective: ObjectiveRow
  isSaving: boolean
  onSave: (body: ObjectiveEditRequest) => void
}) {
  const [draft, setDraft] = useState<ObjectiveDraft>(() => toObjectiveDraft(objective))

  useEffect(() => {
    setDraft(toObjectiveDraft(objective))
  }, [objective])

  return (
    <article className={styles.objectiveCard}>
      <div className={styles.objectiveCardHeader}>
        <div>
          <h5 className={styles.cardTitle}>{objective.title}</h5>
          <p className={styles.cardDescription}>{objective.acceptance ?? 'No acceptance notes.'}</p>
        </div>
        <span className={styles.badge}>{formatObjectiveStatus(objective.status)}</span>
      </div>

      <div className={styles.meta}>
        {(objective.repos ?? []).map((repo) => (
          <span key={repo} className={styles.metaTag}>
            {repo}
          </span>
        ))}
      </div>

      <div className={styles.agentNotesBlock}>
        <p className={styles.objectiveLabel}>Agent notes</p>
        <p className={styles.agentNotesText}>{objective.agent_notes ?? 'No agent notes yet.'}</p>
      </div>

      <div className={styles.objectiveField}>
        <label className={styles.objectiveLabel} htmlFor={`objective-human-notes-${objective.id}`}>
          Human notes
        </label>
        <textarea
          id={`objective-human-notes-${objective.id}`}
          className={styles.textarea}
          rows={4}
          value={draft.human_notes}
          onChange={(event) => {
            setDraft((current) => ({
              ...current,
              human_notes: event.target.value,
            }))
          }}
        />
      </div>

      <div className={styles.objectiveActions}>
        <button
          type="button"
          className={styles.copyButton}
          disabled={isSaving}
          onClick={() => {
            onSave({
              title: draft.title,
              status: draft.status,
              repos: draft.repos,
              acceptance: draft.acceptance || null,
              human_notes: draft.human_notes,
            })
          }}
        >
          {isSaving ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </article>
  )
}

function toObjectiveDraft(objective: ObjectiveRow): ObjectiveDraft {
  return {
    title: objective.title,
    status: objective.status,
    acceptance: objective.acceptance ?? '',
    human_notes: objective.human_notes ?? '',
    repos: objective.repos ?? [],
  }
}

function formatObjectiveStatus(status: ObjectiveStatus): string {
  switch (status) {
    case 'in_progress':
      return 'In Progress'
    case 'done':
      return 'Done'
    case 'cancelled':
      return 'Cancelled'
    case 'pending':
    default:
      return 'Pending'
  }
}

function AgentCard({
  entry,
  active,
  onSelect,
}: {
  entry: AgentCatalogEntry
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      className={active ? `${styles.card} ${styles.cardActive}` : styles.card}
      onClick={onSelect}
    >
      <div className={styles.cardHeader}>
        <h4 className={styles.cardTitle}>{entry.label}</h4>
        <span className={styles.badge}>{entry.source}</span>
      </div>
      <p className={styles.cardDescription}>{entry.description}</p>
      <div className={styles.meta}>
        <span className={styles.metaTag}>{entry.archetype}</span>
        <span className={styles.metaTag}>{entry.scope}</span>
      </div>
    </button>
  )
}

function MetadataPanel({ entry }: { entry: AgentCatalogEntry }) {
  return (
    <div>
      <ul className={styles.list}>
        <li>
          <strong>ID:</strong> {entry.id}
        </li>
        <li>
          <strong>Status:</strong> {entry.status} ({entry.version})
        </li>
        <li>
          <strong>Prompt kinds:</strong> {entry.prompt_kinds.join(', ') || '—'}
        </li>
        <li>
          <strong>Skills:</strong> {entry.recommended_skills.join(', ') || '—'}
        </li>
        <li>
          <strong>Delegates to:</strong> {entry.delegates_to.join(', ') || '—'}
        </li>
        <li>
          <strong>Delegated by:</strong> {entry.delegated_by.join(', ') || '—'}
        </li>
        <li>
          <strong>Vendors:</strong> {entry.vendors.join(', ')}
        </li>
      </ul>
    </div>
  )
}
