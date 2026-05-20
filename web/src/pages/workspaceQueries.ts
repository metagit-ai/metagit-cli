import { getWorkspace, type WorkspaceData } from '../api/client'

export const workspaceQueryKey = ['workspace'] as const

export async function fetchWorkspace(): Promise<WorkspaceData> {
  const envelope = await getWorkspace()
  if (!envelope.ok || !envelope.data) {
    const message = envelope.error?.message ?? 'Failed to load workspace'
    throw new Error(message)
  }
  return envelope.data
}

export type StatusFilter = 'all' | 'synced' | 'missing'

export function repoSelector(projectName: string, repoName: string): string {
  return `${projectName}/${repoName}`
}
