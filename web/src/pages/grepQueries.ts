import {
  getWorkspaceGrep,
  type WorkspaceGrepHit,
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

export type { WorkspaceGrepHit, WorkspaceGrepOptions }
