import { useMemo, useState } from 'react'
import type { WorkspaceProjectEntry, WorkspaceRepoIndexRow } from '../api/client'
import { postOpenPath } from '../api/client'
import {
  EDITOR_ACTIONS,
  editorProtocolUrl,
  type EditorProtocol,
} from '../lib/editorLinks'
import {
  explorerQueryHint,
  filterExplorerGroups,
} from '../lib/explorerFilter'
import styles from './WorkspaceExplorer.module.css'

export interface WorkspaceExplorerProps {
  workspaceName: string | null
  definitionPath: string | null
  projects: WorkspaceProjectEntry[]
  reposIndex: WorkspaceRepoIndexRow[]
  search: string
  onSearchChange: (value: string) => void
}

function formatTag(key: string, value: string): string {
  return value ? `${key}=${value}` : key
}

export default function WorkspaceExplorer({
  workspaceName,
  definitionPath,
  projects,
  reposIndex,
  search,
  onSearchChange,
}: WorkspaceExplorerProps) {
  const [collapsedProjects, setCollapsedProjects] = useState<Record<string, boolean>>(
    {},
  )
  const [openError, setOpenError] = useState<string | null>(null)
  const [openingPath, setOpeningPath] = useState<string | null>(null)

  const groups = useMemo(
    () => filterExplorerGroups(projects, reposIndex, search),
    [projects, reposIndex, search],
  )

  const toggleProject = (name: string) => {
    setCollapsedProjects((current) => ({ ...current, [name]: !current[name] }))
  }

  const handleServerOpen = async (path: string) => {
    setOpenError(null)
    setOpeningPath(path)
    try {
      const result = await postOpenPath({ path })
      if (!result.ok) {
        throw new Error('Failed to open path')
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to open in default editor'
      setOpenError(message)
    } finally {
      setOpeningPath(null)
    }
  }

  return (
    <section className={styles.panel} aria-label="Workspace explorer">
      <div className={styles.searchRow}>
        <input
          type="search"
          className={styles.searchInput}
          placeholder="Filter workspace tree…"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          aria-label="Filter workspace explorer"
        />
        <p className={styles.searchHint}>{explorerQueryHint()}</p>
      </div>

      {openError ? <p className={styles.openError}>{openError}</p> : null}

      {groups.length === 0 ? (
        <p className={styles.empty}>No projects or repositories match the current filters.</p>
      ) : (
        <ul className={styles.tree}>
          <li className={styles.workspaceNode}>
            <span className={styles.workspaceLabel}>
              <span aria-hidden>🗂</span>
              {workspaceName ?? 'Workspace'}
            </span>
            {definitionPath ? (
              <span className={styles.workspacePath}>{definitionPath}</span>
            ) : null}
            <ul className={styles.projectList}>
              {groups.map(({ project, repos }) => (
                <ProjectBranch
                  key={project.name}
                  project={project}
                  repos={repos}
                  collapsed={collapsedProjects[project.name] ?? false}
                  openingPath={openingPath}
                  onToggle={() => toggleProject(project.name)}
                  onServerOpen={handleServerOpen}
                />
              ))}
            </ul>
          </li>
        </ul>
      )}
    </section>
  )
}

interface ProjectBranchProps {
  project: WorkspaceProjectEntry
  repos: WorkspaceRepoIndexRow[]
  collapsed: boolean
  openingPath: string | null
  onToggle: () => void
  onServerOpen: (path: string) => Promise<void>
}

function ProjectBranch({
  project,
  repos,
  collapsed,
  openingPath,
  onToggle,
  onServerOpen,
}: ProjectBranchProps) {
  const projectTags = Object.entries(project.tags ?? {})

  return (
    <li className={styles.projectNode}>
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
        {projectTags.length > 0 ? (
          <span className={styles.tagList}>
            {projectTags.map(([key, value]) => (
              <span key={`${key}=${value}`} className={styles.tag}>
                {formatTag(key, value)}
              </span>
            ))}
          </span>
        ) : null}
      </div>
      {!collapsed ? (
        <ul className={styles.repoList}>
          {repos.map((row) => (
            <RepoLeaf
              key={`${row.project_name}/${row.repo_name}`}
              row={row}
              openingPath={openingPath}
              onServerOpen={onServerOpen}
            />
          ))}
        </ul>
      ) : null}
    </li>
  )
}

interface RepoLeafProps {
  row: WorkspaceRepoIndexRow
  openingPath: string | null
  onServerOpen: (path: string) => Promise<void>
}

function RepoLeaf({ row, openingPath, onServerOpen }: RepoLeafProps) {
  const canOpen = row.exists && row.status === 'synced'
  const repoTags = Object.entries(row.tags ?? {})
  const isOpening = openingPath === row.repo_path

  return (
    <li className={styles.repoNode}>
      <div className={styles.repoHeader}>
        <span className={styles.repoName}>{row.repo_name}</span>
        <span
          className={
            row.status === 'synced'
              ? `${styles.badge} ${styles.badgeSynced}`
              : `${styles.badge} ${styles.badgeMissing}`
          }
        >
          {row.status === 'synced' ? 'synced' : 'missing'}
        </span>
        {repoTags.length > 0 ? (
          <span className={styles.tagList}>
            {repoTags.map(([key, value]) => (
              <span key={`${key}=${value}`} className={styles.tag}>
                {formatTag(key, value)}
              </span>
            ))}
          </span>
        ) : null}
      </div>
      {row.repo_path ? (
        canOpen ? (
          <a
            className={`${styles.repoPath} ${styles.repoPathLink}`}
            href={editorProtocolUrl('vscode', row.repo_path)}
            title="Open path in VS Code"
          >
            {row.repo_path}
          </a>
        ) : (
          <span className={styles.repoPath}>{row.repo_path}</span>
        )
      ) : null}
      <div className={styles.actions}>
        {EDITOR_ACTIONS.map((action) => {
          if (action.id === 'server') {
            return (
              <button
                key={action.id}
                type="button"
                className={`${styles.actionButton} ${styles.actionPrimary}`}
                title={action.title}
                disabled={!canOpen || isOpening}
                onClick={() => void onServerOpen(row.repo_path)}
              >
                {isOpening ? 'Opening…' : action.label}
              </button>
            )
          }
          if (!canOpen) {
            return (
              <button
                key={action.id}
                type="button"
                className={styles.actionButton}
                title={`${action.title} (clone required)`}
                disabled
              >
                {action.label}
              </button>
            )
          }
          return (
            <a
              key={action.id}
              className={styles.actionButton}
              href={editorProtocolUrl(action.id as EditorProtocol, row.repo_path)}
              title={action.title}
            >
              {action.label}
            </a>
          )
        })}
      </div>
    </li>
  )
}
