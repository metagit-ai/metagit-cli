import { useMemo, useState } from 'react'
import type { WorkspaceProjectEntry, WorkspaceRepoIndexRow } from '../api/client'
import { repoSelector, type StatusFilter } from '../pages/workspaceQueries'
import styles from './RepoTable.module.css'

export interface RepoTableProps {
  projects: WorkspaceProjectEntry[]
  reposIndex: WorkspaceRepoIndexRow[]
  statusFilter: StatusFilter
  search: string
  onSync: (repos: string[], title: string) => void
}

interface ProjectGroup {
  project: WorkspaceProjectEntry
  repos: WorkspaceRepoIndexRow[]
}

function matchesFilter(
  row: WorkspaceRepoIndexRow,
  statusFilter: StatusFilter,
): boolean {
  if (statusFilter === 'all') {
    return true
  }
  if (statusFilter === 'synced') {
    return row.status === 'synced'
  }
  return row.status === 'configured_missing'
}

function matchesSearch(row: WorkspaceRepoIndexRow, search: string): boolean {
  const needle = search.trim().toLowerCase()
  if (!needle) {
    return true
  }
  return (
    row.repo_name.toLowerCase().includes(needle) ||
    row.project_name.toLowerCase().includes(needle) ||
    (row.repo_path ?? '').toLowerCase().includes(needle)
  )
}

export default function RepoTable({
  projects,
  reposIndex,
  statusFilter,
  search,
  onSync,
}: RepoTableProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const groups = useMemo(() => {
    const byProject = new Map<string, WorkspaceRepoIndexRow[]>()
    for (const row of reposIndex) {
      if (!matchesFilter(row, statusFilter) || !matchesSearch(row, search)) {
        continue
      }
      const list = byProject.get(row.project_name) ?? []
      list.push(row)
      byProject.set(row.project_name, list)
    }

    const ordered: ProjectGroup[] = []
    for (const project of projects) {
      const repos = byProject.get(project.name)
      if (!repos?.length) {
        continue
      }
      repos.sort((a, b) => a.repo_name.localeCompare(b.repo_name))
      ordered.push({ project, repos })
    }
    return ordered
  }, [projects, reposIndex, statusFilter, search])

  const toggleProject = (name: string) => {
    setCollapsed((current) => ({ ...current, [name]: !current[name] }))
  }

  if (groups.length === 0) {
    return <p className={styles.empty}>No repositories match the current filters.</p>
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Repository</th>
            <th scope="col">Status</th>
            <th scope="col">Path</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {groups.map(({ project, repos }) => {
            const isCollapsed = collapsed[project.name] ?? false
            const selectors = repos.map((row) =>
              repoSelector(row.project_name, row.repo_name),
            )
            return (
              <ProjectSection
                key={project.name}
                project={project}
                repos={repos}
                collapsed={isCollapsed}
                onToggle={() => toggleProject(project.name)}
                onSync={onSync}
                onSyncAll={() =>
                  onSync(selectors, `Sync all in ${project.name} (${repos.length})`)
                }
              />
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

interface ProjectSectionProps {
  project: WorkspaceProjectEntry
  repos: WorkspaceRepoIndexRow[]
  collapsed: boolean
  onToggle: () => void
  onSync: (repos: string[], title: string) => void
  onSyncAll: () => void
}

function ProjectSection({
  project,
  repos,
  collapsed,
  onToggle,
  onSync,
  onSyncAll,
}: ProjectSectionProps) {
  return (
    <>
      <tr className={styles.projectRow}>
        <td colSpan={4}>
          <div className={styles.projectHeader}>
            <button
              type="button"
              className={styles.expandButton}
              onClick={onToggle}
              aria-expanded={!collapsed}
            >
              <span aria-hidden>{collapsed ? '▸' : '▾'}</span>
              {project.name}
            </button>
            <span className={styles.projectMeta}>
              {repos.length} repo{repos.length === 1 ? '' : 's'}
              {project.description ? ` · ${project.description}` : ''}
            </span>
            <button type="button" className={styles.buttonPrimary} onClick={onSyncAll}>
              Sync all
            </button>
          </div>
        </td>
      </tr>
      {!collapsed
        ? repos.map((row) => (
            <tr key={`${row.project_name}/${row.repo_name}`}>
              <td className={styles.repoName}>{row.repo_name}</td>
              <td>
                <span
                  className={
                    row.status === 'synced'
                      ? `${styles.badge} ${styles.badgeSynced}`
                      : `${styles.badge} ${styles.badgeMissing}`
                  }
                >
                  {row.status === 'synced' ? 'synced' : 'missing'}
                </span>
              </td>
              <td className={styles.path}>{row.repo_path}</td>
              <td>
                <div className={styles.actions}>
                  <button
                    type="button"
                    className={styles.buttonPrimary}
                    onClick={() =>
                      onSync(
                        [repoSelector(row.project_name, row.repo_name)],
                        `${row.project_name}/${row.repo_name}`,
                      )
                    }
                  >
                    Sync
                  </button>
                </div>
              </td>
            </tr>
          ))
        : null}
    </>
  )
}
