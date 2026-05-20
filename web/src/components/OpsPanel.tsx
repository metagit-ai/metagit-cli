import { useMemo, useState } from 'react'
import {
  ApiError,
  postHealth,
  postPrune,
  postPrunePreview,
  type PruneCandidate,
  type WorkspaceHealthResult,
  type WorkspaceProjectEntry,
} from '../api/client'
import styles from './OpsPanel.module.css'

export interface OpsPanelProps {
  projects: WorkspaceProjectEntry[]
  onWorkspaceRefresh?: () => void
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

  const projectOptions = useMemo(
    () => projects.filter((entry) => entry.name !== 'local'),
    [projects],
  )

  const selectedProject = project || projectOptions[0]?.name || ''

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
