import {
  getPipelineProviders,
  getPipelineStatus,
  getWorkspace,
  type PipelineProvidersResponse,
  type PipelineStatus,
  type PipelineStatusResponse,
  type WorkspaceData,
} from '../api/client'

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

export type PipelineProviderFilter = 'all' | 'github' | 'gitlab'

export type PipelineStatusFilter = 'all' | PipelineStatus

export const pipelineProvidersQueryKey = ['workspace', 'pipelines', 'providers'] as const

export function pipelineStatusQueryKey(options: {
  project?: string
  provider?: PipelineProviderFilter
  status?: PipelineStatusFilter
  includeUnsynced?: boolean
  limit?: number
}) {
  return ['workspace', 'pipelines', options] as const
}

export async function fetchPipelineProviders(): Promise<PipelineProvidersResponse> {
  return getPipelineProviders()
}

export async function fetchPipelineStatus(options: {
  project?: string
  provider?: PipelineProviderFilter
  status?: PipelineStatusFilter
  includeUnsynced?: boolean
  limit?: number
}): Promise<PipelineStatusResponse> {
  return getPipelineStatus({
    project: options.project,
    provider: options.provider,
    status: options.status,
    includeUnsynced: options.includeUnsynced,
    limit: options.limit,
  })
}

export function repoSelector(projectName: string, repoName: string): string {
  return `${projectName}/${repoName}`
}
