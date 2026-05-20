import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import OpsPanel from '../components/OpsPanel'
import RepoTable from '../components/RepoTable'
import SyncDialog from '../components/SyncDialog'
import {
  fetchWorkspace,
  workspaceQueryKey,
  type StatusFilter,
} from './workspaceQueries'
import styles from './WorkspacePage.module.css'

interface SyncTarget {
  repos: string[]
  title: string
}

export default function WorkspacePage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')
  const [syncTarget, setSyncTarget] = useState<SyncTarget | null>(null)

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: workspaceQueryKey,
    queryFn: fetchWorkspace,
  })

  const reposIndex = data?.repos_index ?? []
  const projects = data?.projects ?? []

  const stats = useMemo(() => {
    const synced = reposIndex.filter((row) => row.status === 'synced').length
    const missing = reposIndex.filter(
      (row) => row.status === 'configured_missing',
    ).length
    return {
      projects: projects.length,
      repos: reposIndex.length,
      synced,
      missing,
    }
  }, [projects.length, reposIndex])

  const definitionPath =
    typeof data?.summary?.definition_path === 'string'
      ? data.summary.definition_path
      : null

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Workspace</h2>
          {definitionPath ? (
            <p className={styles.subtitle}>{definitionPath}</p>
          ) : null}
        </div>
      </header>

      <div className={styles.chips} aria-label="Workspace summary">
        <span className={styles.chip}>
          <strong>{stats.projects}</strong> projects
        </span>
        <span className={styles.chip}>
          <strong>{stats.repos}</strong> repos
        </span>
        <span className={styles.chip}>
          <strong>{stats.synced}</strong> synced
        </span>
        <span className={styles.chip}>
          <strong>{stats.missing}</strong> missing
        </span>
      </div>

      <div className={styles.toolbar}>
        <div className={styles.tabs} role="tablist" aria-label="Repository status filter">
          {(
            [
              ['all', 'All'],
              ['synced', 'Synced'],
              ['missing', 'Missing'],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={statusFilter === value}
              className={
                statusFilter === value ? `${styles.tab} ${styles.tabActive}` : styles.tab
              }
              onClick={() => setStatusFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <input
          type="search"
          className={styles.search}
          placeholder="Search repositories…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Search repositories"
        />
      </div>

      {isLoading ? <p className={styles.loading}>Loading workspace…</p> : null}
      {isError ? (
        <p className={styles.error}>
          {error instanceof Error ? error.message : 'Failed to load workspace.'}
        </p>
      ) : null}

      {!isLoading && !isError && data ? (
        <div className={styles.layout}>
          <RepoTable
            projects={projects}
            reposIndex={reposIndex}
            statusFilter={statusFilter}
            search={search}
            onSync={(repos, title) => setSyncTarget({ repos, title })}
          />
          <OpsPanel projects={projects} onWorkspaceRefresh={() => void refetch()} />
        </div>
      ) : null}

      <SyncDialog
        open={syncTarget !== null}
        title={syncTarget?.title ?? ''}
        repos={syncTarget?.repos ?? []}
        onClose={() => setSyncTarget(null)}
      />
    </section>
  )
}
