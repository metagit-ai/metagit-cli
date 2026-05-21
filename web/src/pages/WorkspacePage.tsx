import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import GraphDiagram from '../components/GraphDiagram'
import OpsPanel from '../components/OpsPanel'
import RepoTable from '../components/RepoTable'
import SyncDialog from '../components/SyncDialog'
import { fetchWorkspaceGraph, graphQueryKey } from './graphQueries'
import {
  fetchWorkspace,
  workspaceQueryKey,
  type StatusFilter,
} from './workspaceQueries'
import styles from './WorkspacePage.module.css'

type WorkspaceView = 'repos' | 'graph'

interface SyncTarget {
  repos: string[]
  title: string
}

export default function WorkspacePage() {
  const [view, setView] = useState<WorkspaceView>('repos')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [search, setSearch] = useState('')
  const [includeInferred, setIncludeInferred] = useState(true)
  const [includeStructure, setIncludeStructure] = useState(true)
  const [syncTarget, setSyncTarget] = useState<SyncTarget | null>(null)

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: workspaceQueryKey,
    queryFn: fetchWorkspace,
  })

  const {
    data: graphData,
    isLoading: graphLoading,
    isError: graphError,
    error: graphErr,
    refetch: refetchGraph,
  } = useQuery({
    queryKey: graphQueryKey(includeInferred, includeStructure),
    queryFn: () => fetchWorkspaceGraph(includeInferred, includeStructure),
    enabled: view === 'graph',
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
        <div className={styles.tabs} role="tablist" aria-label="Workspace view">
          {(
            [
              ['repos', 'Repositories'],
              ['graph', 'Graph'],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={view === value}
              className={view === value ? `${styles.tab} ${styles.tabActive}` : styles.tab}
              onClick={() => setView(value)}
            >
              {label}
            </button>
          ))}
        </div>
        {view === 'repos' ? (
          <>
            <div
              className={styles.tabs}
              role="tablist"
              aria-label="Repository status filter"
            >
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
                    statusFilter === value
                      ? `${styles.tab} ${styles.tabActive}`
                      : styles.tab
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
          </>
        ) : (
          <div className={styles.graphFilters}>
            <label className={styles.checkLabel}>
              <input
                type="checkbox"
                checked={includeInferred}
                onChange={(event) => setIncludeInferred(event.target.checked)}
              />
              Inferred dependencies
            </label>
            <label className={styles.checkLabel}>
              <input
                type="checkbox"
                checked={includeStructure}
                onChange={(event) => setIncludeStructure(event.target.checked)}
              />
              Project → repo structure
            </label>
          </div>
        )}
      </div>

      {isLoading ? <p className={styles.loading}>Loading workspace…</p> : null}
      {isError ? (
        <p className={styles.error}>
          {error instanceof Error ? error.message : 'Failed to load workspace.'}
        </p>
      ) : null}

      {!isLoading && !isError && data ? (
        <div className={styles.layout}>
          {view === 'repos' ? (
            <RepoTable
              projects={projects}
              reposIndex={reposIndex}
              statusFilter={statusFilter}
              search={search}
              onSync={(repos, title) => setSyncTarget({ repos, title })}
            />
          ) : (
            <section className={styles.graphPanel}>
              {graphLoading ? (
                <p className={styles.loading}>Loading relationship graph…</p>
              ) : null}
              {graphError ? (
                <p className={styles.error}>
                  {graphErr instanceof Error
                    ? graphErr.message
                    : 'Failed to load graph.'}
                </p>
              ) : null}
              {graphData ? (
                <GraphDiagram
                  nodes={graphData.nodes}
                  edges={graphData.edges}
                  manualEdgeCount={graphData.manual_edge_count}
                  inferredEdgeCount={graphData.inferred_edge_count}
                  structureEdgeCount={graphData.structure_edge_count}
                />
              ) : null}
            </section>
          )}
          <OpsPanel
            projects={projects}
            onWorkspaceRefresh={() => {
              void refetch()
              if (view === 'graph') {
                void refetchGraph()
              }
            }}
          />
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
