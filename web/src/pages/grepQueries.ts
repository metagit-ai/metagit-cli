import {
  getWorkspaceGrep,
  getWorkspaceGrepInfo,
  type WorkspaceGrepHit,
  type WorkspaceGrepInfo,
  type WorkspaceGrepOptions,
} from '../api/client'

export function grepQueryKey(options: WorkspaceGrepOptions): readonly unknown[] {
  return [
    'workspace-grep',
    options.q,
    options.project ?? '',
    ...(options.repos ?? []),
    options.preset ?? '',
    options.intent ?? '',
    options.maxResults ?? 25,
    options.contextLines ?? 0,
    options.includePaths ?? false,
  ] as const
}

export async function fetchWorkspaceGrep(
  options: WorkspaceGrepOptions,
): Promise<WorkspaceGrepHit[]> {
  const result = await getWorkspaceGrep(options)
  if (!result.ok) {
    const message = result.error?.message ?? 'Grep search failed'
    throw new Error(message)
  }
  return result.data?.hits ?? []
}

export const grepInfoQueryKey = ['workspace-grep-info'] as const

export async function fetchWorkspaceGrepInfo(): Promise<WorkspaceGrepInfo> {
  const result = await getWorkspaceGrepInfo()
  if (!result.ok || !result.data) {
    throw new Error(result.error?.message ?? 'Failed to load grep backend status')
  }
  return result.data
}

export type { WorkspaceGrepHit, WorkspaceGrepInfo, WorkspaceGrepOptions }
