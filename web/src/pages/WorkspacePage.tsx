import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import GraphDiagram from '../components/GraphDiagram'
import OpsPanel from '../components/OpsPanel'
import RepoTable from '../components/RepoTable'
import SyncDialog from '../components/SyncDialog'
import { fetchWorkspaceGraph, graphQueryKey } from './graphQueries'
import {
  fetchWorkspaceGrep,
  fetchWorkspaceGrepInfo,
  grepInfoQueryKey,
  grepQueryKey,
} from './grepQueries'
import {
  fetchWorkspace,
  workspaceQueryKey,
  type StatusFilter,
} from './workspaceQueries'
import styles from './WorkspacePage.module.css'

type WorkspaceView = 'repos' | 'graph' | 'search'

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
  const [grepInput, setGrepInput] = useState('')
  const [grepSubmitted, setGrepSubmitted] = useState('')
  const [grepProject, setGrepProject] = useState('')
  const [grepFilesOnly, setGrepFilesOnly] = useState(false)

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

  const {
    data: grepHits,
    isLoading: grepLoading,
    isError: grepIsError,
    error: grepError,
    refetch: refetchGrep,
  } = useQuery({
    queryKey: grepQueryKey({
      q: grepSubmitted,
      project: grepProject || undefined,
      includePaths: grepFilesOnly,
    }),
    queryFn: () =>
      fetchWorkspaceGrep({
        q: grepSubmitted,
        project: grepProject || undefined,
        includePaths: grepFilesOnly,
      }),
    enabled: view === 'search' && grepSubmitted.length > 0,
  })

  const { data: grepInfo } = useQuery({
    queryKey: grepInfoQueryKey,
    queryFn: fetchWorkspaceGrepInfo,
    enabled: view === 'search',
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
              ['search', 'Search'],
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
        ) : view === 'search' ? (
          <form
            className={styles.grepForm}
            onSubmit={(event) => {
              event.preventDefault()
              const trimmed = grepInput.trim()
              if (!trimmed) {
                return
              }
              setGrepSubmitted(trimmed)
              if (trimmed === grepSubmitted) {
                void refetchGrep()
              }
            }}
          >
            <input
              type="search"
              className={styles.search}
              placeholder="Search file contents across repos…"
              value={grepInput}
              onChange={(event) => setGrepInput(event.target.value)}
              aria-label="Grep query"
            />
            <select
              className={styles.grepSelect}
              value={grepProject}
              onChange={(event) => setGrepProject(event.target.value)}
              aria-label="Limit to project"
            >
              <option value="">All projects</option>
              {projects.map((project) => (
                <option key={project.name} value={project.name}>
                  {project.name}
                </option>
              ))}
            </select>
            <label className={styles.checkLabel}>
              <input
                type="checkbox"
                checked={grepFilesOnly}
                onChange={(event) => setGrepFilesOnly(event.target.checked)}
              />
              Files only
            </label>
            <button type="submit" className={styles.grepSubmit}>
              Search
            </button>
          </form>
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
          ) : view === 'search' ? (
            <section className={styles.grepPanel} aria-label="Content search results">
              {grepInfo ? (
                <p className={styles.grepBackend}>
                  Search backend:{' '}
                  {grepInfo.ripgrep_available
                    ? `ripgrep (${grepInfo.ripgrep_version ?? grepInfo.ripgrep_path ?? 'available'})`
                    : 'Python walk (install ripgrep for faster search)'}
                </p>
              ) : null}
              {!grepSubmitted ? (
                <p className={styles.loading}>
                  Enter a query and press Search to grep workspace repositories.
                </p>
              ) : null}
              {grepLoading ? (
                <p className={styles.loading}>Searching…</p>
              ) : null}
              {grepIsError ? (
                <p className={styles.error}>
                  {grepError instanceof Error
                    ? grepError.message
                    : 'Search failed.'}
                </p>
              ) : null}
              {grepSubmitted && !grepLoading && !grepIsError ? (
                grepHits && grepHits.length > 0 ? (
                  <ul className={styles.grepHits}>
                    {grepHits.map((hit, index) => (
                      <li
                        key={`${hit.repo_path}-${hit.file_path}-${hit.line_number}-${index}`}
                        className={styles.grepHit}
                      >
                        <span className={styles.grepLocation}>
                          {hit.project_name}/{hit.repo_name}:{hit.file_path}
                          {hit.match_kind !== 'path' ? `:${hit.line_number}` : ''}
                        </span>
                        {hit.line ? (
                          <code className={styles.grepLine}>{hit.line}</code>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className={styles.loading}>No matches.</p>
                )
              ) : null}
            </section>
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
