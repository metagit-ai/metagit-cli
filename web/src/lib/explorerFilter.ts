import type { WorkspaceProjectEntry, WorkspaceRepoIndexRow } from '../api/client'

export interface ExplorerProjectGroup {
  project: WorkspaceProjectEntry
  repos: WorkspaceRepoIndexRow[]
}

interface ParsedQuery {
  textTokens: string[]
  tagFilters: Array<{ key: string; value?: string }>
  projectFilter: string | null
  statusFilter: 'synced' | 'missing' | null
}

function parseExplorerQuery(raw: string): ParsedQuery {
  const textTokens: string[] = []
  const tagFilters: Array<{ key: string; value?: string }> = []
  let projectFilter: string | null = null
  let statusFilter: 'synced' | 'missing' | null = null

  for (const token of raw.trim().split(/\s+/)) {
    if (!token) {
      continue
    }
    const lower = token.toLowerCase()
    if (lower.startsWith('project:')) {
      projectFilter = token.slice('project:'.length).toLowerCase()
      continue
    }
    if (lower.startsWith('status:')) {
      const status = lower.slice('status:'.length)
      if (status === 'synced' || status === 'missing') {
        statusFilter = status
      }
      continue
    }
    if (lower.startsWith('tag:')) {
      const tagSpec = token.slice('tag:'.length)
      const eqIndex = tagSpec.indexOf('=')
      if (eqIndex >= 0) {
        tagFilters.push({
          key: tagSpec.slice(0, eqIndex).toLowerCase(),
          value: tagSpec.slice(eqIndex + 1).toLowerCase(),
        })
      } else {
        tagFilters.push({ key: tagSpec.toLowerCase() })
      }
      continue
    }
    if (token.startsWith('#')) {
      const tagSpec = token.slice(1)
      const eqIndex = tagSpec.indexOf('=')
      if (eqIndex >= 0) {
        tagFilters.push({
          key: tagSpec.slice(0, eqIndex).toLowerCase(),
          value: tagSpec.slice(eqIndex + 1).toLowerCase(),
        })
      } else {
        tagFilters.push({ key: tagSpec.toLowerCase() })
      }
      continue
    }
    textTokens.push(lower)
  }

  return { textTokens, tagFilters, projectFilter, statusFilter }
}

function tagEntries(tags: Record<string, string> | undefined): Array<[string, string]> {
  if (!tags) {
    return []
  }
  return Object.entries(tags)
}

function matchesTagFilters(
  projectTags: Record<string, string> | undefined,
  repoTags: Record<string, string> | undefined,
  filters: Array<{ key: string; value?: string }>,
): boolean {
  if (filters.length === 0) {
    return true
  }
  const combined = new Map<string, string>()
  for (const [key, value] of tagEntries(projectTags)) {
    combined.set(key.toLowerCase(), value.toLowerCase())
  }
  for (const [key, value] of tagEntries(repoTags)) {
    combined.set(key.toLowerCase(), value.toLowerCase())
  }
  return filters.every((filter) => {
    if (filter.value !== undefined) {
      return combined.get(filter.key) === filter.value
    }
    if (combined.has(filter.key)) {
      return true
    }
    for (const [key, value] of combined.entries()) {
      if (key.includes(filter.key) || value.includes(filter.key)) {
        return true
      }
    }
    return false
  })
}

function matchesTextTokens(
  row: WorkspaceRepoIndexRow,
  project: WorkspaceProjectEntry,
  tokens: string[],
): boolean {
  if (tokens.length === 0) {
    return true
  }
  const haystack = [
    row.repo_name,
    row.project_name,
    row.repo_path ?? '',
    row.configured_path ?? '',
    row.url ?? '',
    project.description ?? '',
    ...Object.entries(project.tags ?? {}).flatMap(([key, value]) => [key, value]),
    ...Object.entries(row.tags ?? {}).flatMap(([key, value]) => [key, value]),
  ]
    .join(' ')
    .toLowerCase()
  return tokens.every((token) => haystack.includes(token))
}

function matchesStatus(
  row: WorkspaceRepoIndexRow,
  statusFilter: 'synced' | 'missing' | null,
): boolean {
  if (!statusFilter) {
    return true
  }
  if (statusFilter === 'synced') {
    return row.status === 'synced'
  }
  return row.status === 'configured_missing'
}

export function filterExplorerGroups(
  projects: WorkspaceProjectEntry[],
  reposIndex: WorkspaceRepoIndexRow[],
  query: string,
): ExplorerProjectGroup[] {
  const parsed = parseExplorerQuery(query)
  const byProject = new Map<string, WorkspaceRepoIndexRow[]>()

  for (const row of reposIndex) {
    if (
      parsed.projectFilter &&
      row.project_name.toLowerCase() !== parsed.projectFilter
    ) {
      continue
    }
    const project =
      projects.find((entry) => entry.name === row.project_name) ??
      ({
        name: row.project_name,
        repo_count: 0,
      } satisfies WorkspaceProjectEntry)
    if (
      !matchesStatus(row, parsed.statusFilter) ||
      !matchesTagFilters(project.tags, row.tags, parsed.tagFilters) ||
      !matchesTextTokens(row, project, parsed.textTokens)
    ) {
      continue
    }
    const list = byProject.get(row.project_name) ?? []
    list.push(row)
    byProject.set(row.project_name, list)
  }

  const ordered: ExplorerProjectGroup[] = []
  for (const project of projects) {
    const repos = byProject.get(project.name)
    if (!repos?.length) {
      continue
    }
    repos.sort((a, b) => a.repo_name.localeCompare(b.repo_name))
    ordered.push({ project, repos })
  }
  return ordered
}

export function explorerQueryHint(): string {
  return 'Search names, paths, tag:key, #tag, project:name, status:synced|missing'
}
