import { useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  getApprovals,
  getObjectives,
  getSessionDigest,
  patchObjective,
  postHealth,
  postObjective,
  postSessionBegin,
  postPrune,
  postPrunePreview,
  postSourceSync,
  resolveApproval,
  type ApprovalRequestRow,
  type ObjectiveRow,
  type ObjectiveStatus,
  type PruneCandidate,
  type SessionDigestResponse,
  type WorkspaceHealthResult,
  type WorkspaceProjectEntry,
} from '../api/client'
import styles from './OpsPanel.module.css'

export interface OpsPanelProps {
  projects: WorkspaceProjectEntry[]
  onWorkspaceRefresh?: () => void
}

type ObjectiveDraft = {
  title: string
  status: ObjectiveStatus
  acceptance: string
  human_notes: string
  repos: string
}

const OBJECTIVE_STATUS_ORDER: ObjectiveStatus[] = [
  'pending',
  'in_progress',
  'done',
  'cancelled',
]

function toObjectiveDraft(row: ObjectiveRow): ObjectiveDraft {
  return {
    title: row.title,
    status: row.status,
    acceptance: row.acceptance ?? '',
    human_notes: row.human_notes ?? '',
    repos: (row.repos ?? []).join(', '),
  }
}

export default function OpsPanel({ projects, onWorkspaceRefresh }: OpsPanelProps) {
  const [healthOpen, setHealthOpen] = useState(false)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthResult, setHealthResult] = useState<WorkspaceHealthResult | null>(null)
  const [healthError, setHealthError] = useState('')

  const [project, setProject] = useState('')
  const [candidates, setCandidates] = useState<PruneCandidate[]>([])
  const [pruneLoading, setPruneLoading] = useState(false)
  const [pruneMessage, setPruneMessage] = useState('')
  const [pruneError, setPruneError] = useState('')
  const [confirmPrune, setConfirmPrune] = useState(false)

  const [approvals, setApprovals] = useState<ApprovalRequestRow[]>([])
  const [approvalsLoading, setApprovalsLoading] = useState(false)
  const [approvalsError, setApprovalsError] = useState('')
  const [approvalsMessage, setApprovalsMessage] = useState('')

  const [sourceApply, setSourceApply] = useState(false)
  const [sourceForce, setSourceForce] = useState(false)
  const [sourceSyncClones, setSourceSyncClones] = useState(false)
  const [sourceLoading, setSourceLoading] = useState(false)
  const [sourceMessage, setSourceMessage] = useState('')
  const [sourceError, setSourceError] = useState('')

  const projectOptions = useMemo(
    () => projects.filter((entry) => entry.name !== 'local'),
    [projects],
  )

  const selectedProject = project || projectOptions[0]?.name || ''

  const loadApprovals = async () => {
    setApprovalsLoading(true)
    setApprovalsError('')
    try {
      const result = await getApprovals('pending')
      setApprovals(result.requests ?? [])
    } catch (err) {
      setApprovalsError(err instanceof ApiError ? err.message : 'Failed to load approvals.')
    } finally {
      setApprovalsLoading(false)
    }
  }

  useEffect(() => {
    void loadApprovals()
  }, [])

  const runHealth = async () => {
    setHealthLoading(true)
    setHealthError('')
    setHealthResult(null)
    try {
      const result = await postHealth({})
      setHealthResult(result)
      setHealthOpen(true)
    } catch (err) {
      setHealthError(err instanceof ApiError ? err.message : 'Health check failed.')
      setHealthOpen(true)
    } finally {
      setHealthLoading(false)
    }
  }

  const runPrunePreview = async () => {
    if (!selectedProject) {
      setPruneError('Select a project first.')
      return
    }
    setPruneLoading(true)
    setPruneError('')
    setPruneMessage('')
    setCandidates([])
    setConfirmPrune(false)
    try {
      const result = await postPrunePreview({ project: selectedProject })
      setCandidates(result.candidates ?? [])
      setPruneMessage(
        result.candidates?.length
          ? `${result.candidates.length} candidate(s) found.`
          : 'No unmanaged directories to prune.',
      )
    } catch (err) {
      setPruneError(err instanceof ApiError ? err.message : 'Prune preview failed.')
    } finally {
      setPruneLoading(false)
    }
  }

  const runPruneExecute = async () => {
    if (!selectedProject || candidates.length === 0 || !confirmPrune) {
      return
    }
    setPruneLoading(true)
    setPruneError('')
    setPruneMessage('')
    try {
      const result = await postPrune({
        project: selectedProject,
        paths: candidates.map((item) => item.path),
        force: true,
      })
      setPruneMessage(
        result.removed?.length
          ? `Removed ${result.removed.length} path(s).`
          : 'Prune completed with no removals.',
      )
      setCandidates([])
      setConfirmPrune(false)
      onWorkspaceRefresh?.()
    } catch (err) {
      setPruneError(err instanceof ApiError ? err.message : 'Prune failed.')
    } finally {
      setPruneLoading(false)
    }
  }

  const runSourceSync = async () => {
    if (!selectedProject) {
      setSourceError('Select a project first.')
      return
    }
    setSourceLoading(true)
    setSourceError('')
    setSourceMessage('')
    try {
      const result = await postSourceSync({
        project_name: selectedProject,
        from_manifest: true,
        apply: sourceApply,
        force: sourceForce,
        sync: sourceSyncClones,
      })
      if (result.pending_approval_id) {
        setSourceMessage(
          `Plan applied; removals pending approval (${result.pending_approval_id}).`,
        )
        await loadApprovals()
      } else if (result.applied) {
        setSourceMessage('Manifest source sync applied.')
      } else {
        setSourceMessage('Manifest source sync plan ready (dry run).')
      }
      onWorkspaceRefresh?.()
    } catch (err) {
      setSourceError(err instanceof ApiError ? err.message : 'Source sync failed.')
    } finally {
      setSourceLoading(false)
    }
  }

  const resolvePendingApproval = async (
    row: ApprovalRequestRow,
    decision: 'approved' | 'denied',
  ) => {
    setApprovalsLoading(true)
    setApprovalsError('')
    setApprovalsMessage('')
    try {
      await resolveApproval(row.id, {
        decision,
        note: decision === 'denied' ? 'Denied from web UI' : undefined,
      })
      setApprovalsMessage(
        decision === 'approved'
          ? `Approved ${row.action}.`
          : `Denied ${row.action}.`,
      )
      await loadApprovals()
      onWorkspaceRefresh?.()
    } catch (err) {
      setApprovalsError(
        err instanceof ApiError ? err.message : 'Failed to resolve approval.',
      )
    } finally {
      setApprovalsLoading(false)
    }
  }

  return (
    <aside className={styles.panel} aria-label="Workspace operations">
      <h3 className={styles.heading}>Operations</h3>

      <div className={styles.section}>
        <h4 className={styles.sectionTitle}>Health</h4>
        <p className={styles.hint}>
          Run a workspace integrity check and review recommendations.
        </p>
        <button
          type="button"
          className={`${styles.button} ${styles.buttonPrimary}`}
          onClick={() => void runHealth()}
          disabled={healthLoading}
        >
          {healthLoading ? 'Checking…' : 'Health check'}
        </button>
      </div>

      <div className={styles.divider} />

      <div className={styles.section}>
        <h4 className={styles.sectionTitle}>Provider source sync</h4>
        <p className={styles.hint}>
          Sync repos from manifest <code>sources[]</code> for the selected project.
        </p>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="source-project">
            Project
          </label>
          <select
            id="source-project"
            className={styles.select}
            value={selectedProject}
            onChange={(event) => {
              setProject(event.target.value)
              setSourceMessage('')
              setSourceError('')
            }}
            disabled={sourceLoading || projectOptions.length === 0}
          >
            {projectOptions.length === 0 ? (
              <option value="">No projects</option>
            ) : (
              projectOptions.map((entry) => (
                <option key={entry.name} value={entry.name}>
                  {entry.name}
                </option>
              ))
            )}
          </select>
        </div>
        <label className={styles.checkboxRow}>
          <input
            type="checkbox"
            checked={sourceApply}
            onChange={(event) => setSourceApply(event.target.checked)}
            disabled={sourceLoading}
          />
          Apply changes to manifest
        </label>
        <label className={styles.checkboxRow}>
          <input
            type="checkbox"
            checked={sourceForce}
            onChange={(event) => setSourceForce(event.target.checked)}
            disabled={sourceLoading || !sourceApply}
          />
          Force reconcile removals (skip approval queue)
        </label>
        <label className={styles.checkboxRow}>
          <input
            type="checkbox"
            checked={sourceSyncClones}
            onChange={(event) => setSourceSyncClones(event.target.checked)}
            disabled={sourceLoading || !sourceApply}
          />
          Clone/sync repos after apply
        </label>
        <button
          type="button"
          className={`${styles.button} ${styles.buttonPrimary}`}
          onClick={() => void runSourceSync()}
          disabled={sourceLoading || !selectedProject}
        >
          {sourceLoading ? 'Running…' : sourceApply ? 'Run manifest sync' : 'Preview manifest sync'}
        </button>
        {sourceMessage ? <p className={styles.status}>{sourceMessage}</p> : null}
        {sourceError ? (
          <p className={`${styles.status} ${styles.statusError}`}>{sourceError}</p>
        ) : null}
      </div>

      <div className={styles.divider} />

      <div className={styles.section}>
        <h4 className={styles.sectionTitle}>Pending approvals</h4>
        <p className={styles.hint}>
          Reconcile removals and other gated operations awaiting a decision.
        </p>
        <button
          type="button"
          className={styles.button}
          onClick={() => void loadApprovals()}
          disabled={approvalsLoading}
        >
          {approvalsLoading ? 'Loading…' : 'Refresh'}
        </button>
        {approvalsMessage ? <p className={styles.status}>{approvalsMessage}</p> : null}
        {approvalsError ? (
          <p className={`${styles.status} ${styles.statusError}`}>{approvalsError}</p>
        ) : null}
        {approvals.length === 0 ? (
          <p className={styles.status}>No pending approvals.</p>
        ) : (
          <ul className={styles.candidateList}>
            {approvals.map((row) => (
              <li key={row.id}>
                <strong>{row.action}</strong>
                <br />
                <span>{row.id}</span>
                <div className={styles.approvalActions}>
                  <button
                    type="button"
                    className={`${styles.button} ${styles.buttonPrimary}`}
                    onClick={() => void resolvePendingApproval(row, 'approved')}
                    disabled={approvalsLoading}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className={styles.button}
                    onClick={() => void resolvePendingApproval(row, 'denied')}
                    disabled={approvalsLoading}
                  >
                    Deny
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.divider} />

      <div className={styles.section}>
        <h4 className={styles.sectionTitle}>Prune sync folders</h4>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="prune-project">
            Project
          </label>
          <select
            id="prune-project"
            className={styles.select}
            value={selectedProject}
            onChange={(event) => {
              setProject(event.target.value)
              setCandidates([])
              setConfirmPrune(false)
              setPruneMessage('')
              setPruneError('')
            }}
            disabled={pruneLoading || projectOptions.length === 0}
          >
            {projectOptions.length === 0 ? (
              <option value="">No projects</option>
            ) : (
              projectOptions.map((entry) => (
                <option key={entry.name} value={entry.name}>
                  {entry.name}
                </option>
              ))
            )}
          </select>
        </div>
        <button
          type="button"
          className={styles.button}
          onClick={() => void runPrunePreview()}
          disabled={pruneLoading || !selectedProject}
        >
          Preview
        </button>
        {pruneMessage ? <p className={styles.status}>{pruneMessage}</p> : null}
        {pruneError ? <p className={`${styles.status} ${styles.statusError}`}>{pruneError}</p> : null}
        {candidates.length > 0 ? (
          <>
            <ul className={styles.candidateList}>
              {candidates.map((item) => (
                <li key={item.path}>{item.path}</li>
              ))}
            </ul>
            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={confirmPrune}
                onChange={(event) => setConfirmPrune(event.target.checked)}
                disabled={pruneLoading}
              />
              I confirm deletion of the listed paths
            </label>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonDanger}`}
              onClick={() => void runPruneExecute()}
              disabled={pruneLoading || !confirmPrune}
            >
              Execute prune
            </button>
          </>
        ) : null}
      </div>

      {healthOpen ? (
        <div
          className={styles.overlay}
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setHealthOpen(false)
            }
          }}
        >
          <div className={styles.modal} role="dialog" aria-modal="true">
            <h3 className={styles.modalTitle}>Health check results</h3>
            {healthError ? (
              <p className={`${styles.status} ${styles.statusError}`}>{healthError}</p>
            ) : null}
            {healthResult ? (
              <>
                {Object.keys(healthResult.summary).length > 0 ? (
                  <div className={styles.summaryGrid}>
                    {Object.entries(healthResult.summary).map(([key, value]) => (
                      <div key={key} className={styles.summaryChip}>
                        <strong>{value}</strong>
                        {key.replaceAll('_', ' ')}
                      </div>
                    ))}
                  </div>
                ) : null}
                {healthResult.recommendations.length > 0 ? (
                  <ul className={styles.recommendations}>
                    {healthResult.recommendations.map((item, index) => (
                      <li
                        key={`${item.action}-${index}`}
                        className={
                          item.severity === 'critical'
                            ? styles.severityCritical
                            : item.severity === 'warning'
                              ? styles.severityWarning
                              : styles.severityInfo
                        }
                      >
                        <strong>{item.severity}</strong> · {item.action}: {item.message}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={styles.status}>No recommendations.</p>
                )}
                {healthResult.repos.length > 0 ? (
                  <table className={styles.repoTable}>
                    <thead>
                      <tr>
                        <th>Project</th>
                        <th>Repo</th>
                        <th>Status</th>
                        <th>Branch</th>
                      </tr>
                    </thead>
                    <tbody>
                      {healthResult.repos.map((row) => (
                        <tr key={`${row.project_name}/${row.repo_name}`}>
                          <td>{row.project_name}</td>
                          <td>{row.repo_name}</td>
                          <td>{row.status}</td>
                          <td>{row.branch ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : null}
              </>
            ) : null}
            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.button}
                onClick={() => setHealthOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </aside>
  )
}
