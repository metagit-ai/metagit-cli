import { useMemo } from 'react'
import type {
  PipelineProvidersResponse,
  PipelineStatusResponse,
} from '../api/client'
import styles from './CicdDashboard.module.css'

export interface CicdDashboardProps {
  data: PipelineStatusResponse | undefined
  providers: PipelineProvidersResponse | undefined
  isLoading: boolean
  isError: boolean
  error: Error | null
  providerFilter: 'all' | 'github' | 'gitlab'
  statusFilter:
    | 'all'
    | 'passed'
    | 'failed'
    | 'running'
    | 'pending'
    | 'canceled'
    | 'skipped'
    | 'unknown'
  projectFilter: string
  includeUnsynced: boolean
  textFilter: string
  projects: Array<{ name: string }>
  onProviderFilter: (value: 'all' | 'github' | 'gitlab') => void
  onStatusFilter: (
    value:
      | 'all'
      | 'passed'
      | 'failed'
      | 'running'
      | 'pending'
      | 'canceled'
      | 'skipped'
      | 'unknown',
  ) => void
  onProjectFilter: (value: string) => void
  onIncludeUnsynced: (value: boolean) => void
  onTextFilter: (value: string) => void
  onRefresh: () => void
}

function ageLabel(updatedAt?: string | null): string {
  if (!updatedAt) {
    return 'unknown'
  }
  const then = new Date(updatedAt).getTime()
  if (Number.isNaN(then)) {
    return 'unknown'
  }
  const deltaMs = Date.now() - then
  if (deltaMs < 60_000) {
    return 'just now'
  }
  const mins = Math.floor(deltaMs / 60_000)
  if (mins < 60) {
    return `${mins}m ago`
  }
  const hours = Math.floor(mins / 60)
  if (hours < 24) {
    return `${hours}h ago`
  }
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function providerSummary(provider: PipelineProvidersResponse['providers'][number]): string {
  return provider.available ? 'auth ok' : 'no auth'
}

export default function CicdDashboard({
  data,
  providers,
  isLoading,
  isError,
  error,
  providerFilter,
  statusFilter,
  projectFilter,
  includeUnsynced,
  textFilter,
  projects,
  onProviderFilter,
  onStatusFilter,
  onProjectFilter,
  onIncludeUnsynced,
  onTextFilter,
  onRefresh,
}: CicdDashboardProps) {
  const rows = data?.rows ?? []
  const filteredRows = useMemo(() => {
    const needle = textFilter.trim().toLowerCase()
    if (!needle) {
      return rows
    }
    return rows.filter((row) => {
      const values = [
        row.project_name,
        row.repo_name,
        row.repo_path ?? '',
        row.repo_url ?? '',
        row.pipeline_name ?? '',
      ]
      return values.some((value) => value.toLowerCase().includes(needle))
    })
  }, [rows, textFilter])

  const grouped = useMemo(() => {
    const byProject = new Map<string, typeof filteredRows>()
    for (const row of filteredRows) {
      const list = byProject.get(row.project_name) ?? []
      list.push(row)
      byProject.set(row.project_name, list)
    }
    return [...byProject.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [filteredRows])

  return (
    <section className={styles.panel} aria-label="CI/CD dashboard">
      <div className={styles.summaryRow}>
        {(
          [
            ['failed', 'Failed'],
            ['running', 'Running'],
            ['pending', 'Pending'],
            ['passed', 'Passed'],
          ] as const
        ).map(([status, label]) => (
          <button
            key={status}
            type="button"
            className={
              statusFilter === status
                ? `${styles.summaryChip} ${styles.summaryChipActive}`
                : styles.summaryChip
            }
            onClick={() => onStatusFilter(status)}
          >
            <strong>{data?.summary?.[status] ?? 0}</strong> {label}
          </button>
        ))}
      </div>

      <div className={styles.filters}>
        <select
          value={providerFilter}
          onChange={(event) =>
            onProviderFilter(event.target.value as 'all' | 'github' | 'gitlab')
          }
          className={styles.select}
          aria-label="Provider filter"
        >
          <option value="all">All providers</option>
          <option value="github">GitHub</option>
          <option value="gitlab">GitLab</option>
        </select>

        <select
          value={statusFilter}
          onChange={(event) =>
            onStatusFilter(
              event.target.value as
                | 'all'
                | 'passed'
                | 'failed'
                | 'running'
                | 'pending'
                | 'canceled'
                | 'skipped'
                | 'unknown',
            )
          }
          className={styles.select}
          aria-label="Status filter"
        >
          <option value="all">All statuses</option>
          <option value="failed">Failed</option>
          <option value="running">Running</option>
          <option value="pending">Pending</option>
          <option value="passed">Passed</option>
          <option value="canceled">Canceled</option>
          <option value="skipped">Skipped</option>
          <option value="unknown">Unknown</option>
        </select>

        <select
          value={projectFilter}
          onChange={(event) => onProjectFilter(event.target.value)}
          className={styles.select}
          aria-label="Project filter"
        >
          <option value="">All projects</option>
          {projects.map((project) => (
            <option key={project.name} value={project.name}>
              {project.name}
            </option>
          ))}
        </select>

        <input
          type="search"
          className={styles.search}
          placeholder="Filter rows..."
          value={textFilter}
          onChange={(event) => onTextFilter(event.target.value)}
          aria-label="Text filter"
        />

        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={includeUnsynced}
            onChange={(event) => onIncludeUnsynced(event.target.checked)}
          />
          Include unsynced repos
        </label>

        <button type="button" className={styles.refresh} onClick={onRefresh}>
          Refresh now
        </button>
      </div>

      <div className={styles.providerInfo}>
        {providers?.providers?.map((provider) => (
          <article key={provider.provider} className={styles.providerCard}>
            <div className={styles.providerCardHeader}>
              <strong>{provider.provider}</strong>
              <span className={styles.providerChip}>{providerSummary(provider)}</span>
            </div>
            <div className={styles.providerMeta}>
              <span>source: {provider.auth_source}</span>
              {provider.account ? <span>account: {provider.account}</span> : null}
              {provider.account_type ? <span>account type: {provider.account_type}</span> : null}
              {provider.token_type ? <span>token type: {provider.token_type}</span> : null}
              {provider.scopes?.length ? <span>scopes: {provider.scopes.join(', ')}</span> : null}
              {provider.expires_at ? <span>expires: {provider.expires_at}</span> : null}
              {provider.base_url ? <span>api: {provider.base_url}</span> : null}
              {provider.note ? <span className={styles.reason}>{provider.note}</span> : null}
            </div>
          </article>
        ))}
      </div>

      {isLoading ? <p className={styles.loading}>Loading pipeline status...</p> : null}
      {isError ? (
        <p className={styles.error}>
          {error instanceof Error ? error.message : 'Failed to load pipeline status'}
        </p>
      ) : null}

      {!isLoading && !isError && grouped.length === 0 ? (
        <p className={styles.loading}>No pipelines match current filters.</p>
      ) : null}

      {!isLoading && !isError && grouped.length > 0 ? (
        <div className={styles.groups}>
          {grouped.map(([project, projectRows]) => (
            <article key={project} className={styles.group}>
              <h3 className={styles.groupTitle}>{project}</h3>
              <ul className={styles.rowList}>
                {projectRows.map((row) => (
                  <li
                    key={`${row.project_name}/${row.repo_name}/${row.provider}`}
                    className={styles.row}
                  >
                    <div className={styles.primary}>
                      <span className={styles.repoName}>{row.repo_name}</span>
                      <span className={`${styles.status} ${styles[`status_${row.pipeline_status}`] ?? ''}`}>
                        {row.pipeline_status}
                      </span>
                      <span className={styles.provider}>{row.provider}</span>
                    </div>
                    <div className={styles.meta}>
                      <span>branch: {row.branch_used ?? 'unknown'}</span>
                      <span>updated: {ageLabel(row.updated_at)}</span>
                      <span>{row.local_status === 'synced' ? 'synced' : 'unsynced'}</span>
                      {row.reason ? <span className={styles.reason}>{row.reason}</span> : null}
                    </div>
                    <div className={styles.links}>
                      {row.web_url ? (
                        <a href={row.web_url} target="_blank" rel="noreferrer">
                          Open pipeline
                        </a>
                      ) : (
                        <span className={styles.reason}>No pipeline URL</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}
