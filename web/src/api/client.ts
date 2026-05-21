export type ConfigOpKind = 'enable' | 'disable' | 'set' | 'append' | 'remove'

export interface ConfigOperation {
  op: ConfigOpKind
  path: string
  value?: unknown
}

export interface SchemaFieldNode {
  path: string
  key: string
  type: string
  type_label?: string | null
  description?: string | null
  required?: boolean
  enabled?: boolean
  editable?: boolean
  sensitive?: boolean
  default_value?: unknown
  value?: unknown
  enum_options?: string[]
  item_count?: number | null
  can_append?: boolean
  children?: SchemaFieldNode[]
}

export interface ConfigTreeResponse {
  ok: boolean
  target: 'metagit' | 'appconfig'
  config_path: string
  tree: SchemaFieldNode
  validation_errors: Array<Record<string, string>>
  saved?: boolean
}

export type ConfigPreviewStyle = 'normalized' | 'minimal' | 'disk'

export interface ConfigPreviewResponse {
  ok: boolean
  target: 'metagit' | 'appconfig'
  config_path: string
  style: ConfigPreviewStyle
  yaml: string
  draft?: boolean
  validation_errors: Array<{ path?: string; message?: string }>
}

export interface SyncJobRequest {
  repos?: string[] | null
  mode?: 'fetch' | 'pull' | 'clone'
  dry_run?: boolean
  allow_mutation?: boolean
  max_parallel?: number
}

export interface SyncJobStatus {
  job_id: string
  state: 'pending' | 'running' | 'completed' | 'failed'
  summary: Record<string, unknown>
  results: Array<Record<string, unknown>>
  error?: string | null
}

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  const text = await response.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text) as unknown
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    const message =
      typeof data === 'object' &&
      data !== null &&
      'message' in data &&
      typeof (data as { message: unknown }).message === 'string'
        ? (data as { message: string }).message
        : response.statusText
    throw new ApiError(response.status, message, data)
  }

  return data as T
}

export function getMetagitConfigTree(): Promise<ConfigTreeResponse> {
  return requestJson<ConfigTreeResponse>('/v3/config/metagit/tree')
}

export function getAppconfigTree(): Promise<ConfigTreeResponse> {
  return requestJson<ConfigTreeResponse>('/v3/config/appconfig/tree')
}

export function patchMetagitConfig(
  ops: ConfigOperation[],
  save: boolean,
): Promise<ConfigTreeResponse> {
  return requestJson<ConfigTreeResponse>('/v3/config/metagit', {
    method: 'PATCH',
    body: JSON.stringify({ operations: ops, save }),
  })
}

export function patchAppconfig(
  ops: ConfigOperation[],
  save: boolean,
): Promise<ConfigTreeResponse> {
  return requestJson<ConfigTreeResponse>('/v3/config/appconfig', {
    method: 'PATCH',
    body: JSON.stringify({ operations: ops, save }),
  })
}

export function postConfigPreview(
  target: 'metagit' | 'appconfig',
  style: ConfigPreviewStyle,
  operations: ConfigOperation[],
): Promise<ConfigPreviewResponse> {
  return requestJson<ConfigPreviewResponse>(`/v3/config/${target}/preview`, {
    method: 'POST',
    body: JSON.stringify({ style, operations }),
  })
}

export interface CatalogEnvelope<T> {
  ok: boolean
  error?: { kind: string; message: string } | null
  data?: T
}

export interface WorkspaceProjectEntry {
  name: string
  description?: string | null
  agent_instructions?: string | null
  dedupe_enabled?: boolean | null
  repo_count: number
}

export interface WorkspaceRepoIndexRow {
  project_name: string
  repo_name: string
  configured_path: string | null
  repo_path: string
  exists: boolean
  is_git_repo: boolean
  status: 'synced' | 'configured_missing' | string
  url?: string | null
  sync?: boolean
  tags?: Record<string, string>
}

export interface WorkspaceData {
  summary: Record<string, unknown>
  projects: WorkspaceProjectEntry[]
  repos_index: WorkspaceRepoIndexRow[]
}

export interface HealthRecommendation {
  severity: 'info' | 'warning' | 'critical'
  action: string
  message: string
  project_name?: string | null
  repo_name?: string | null
  repo_path?: string | null
}

export interface RepoHealthRow {
  project_name: string
  repo_name: string
  repo_path: string
  status: string
  exists: boolean
  is_git_repo: boolean
  branch?: string | null
  dirty?: boolean | null
}

export interface WorkspaceHealthResult {
  ok: boolean
  workspace_root: string
  summary: Record<string, number>
  repos: RepoHealthRow[]
  recommendations: HealthRecommendation[]
}

export interface PruneCandidate {
  path: string
  name: string
}

export function getWorkspace(): Promise<CatalogEnvelope<WorkspaceData>> {
  return requestJson<CatalogEnvelope<WorkspaceData>>('/v2/workspace')
}

export interface GraphViewNode {
  id: string
  label: string
  kind: 'project' | 'repo'
  project_name?: string | null
  repo_name?: string | null
}

export interface GraphViewEdge {
  id: string
  from_id: string
  to_id: string
  type: string
  label?: string | null
  source: 'manual' | 'inferred' | 'structure'
}

export interface WorkspaceGraphView {
  ok: boolean
  nodes: GraphViewNode[]
  edges: GraphViewEdge[]
  manual_edge_count: number
  inferred_edge_count: number
  structure_edge_count: number
}

export function getWorkspaceGraph(options?: {
  includeInferred?: boolean
  includeStructure?: boolean
}): Promise<WorkspaceGraphView> {
  const params = new URLSearchParams()
  if (options?.includeInferred === false) {
    params.set('include_inferred', 'false')
  }
  if (options?.includeStructure === false) {
    params.set('include_structure', 'false')
  }
  const query = params.toString()
  const path = query ? `/v3/ops/graph?${query}` : '/v3/ops/graph'
  return requestJson<WorkspaceGraphView>(path)
}

export function postHealth(
  body: Record<string, unknown> = {},
): Promise<WorkspaceHealthResult> {
  return requestJson<WorkspaceHealthResult>('/v3/ops/health', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function postSync(body: SyncJobRequest): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>('/v3/ops/sync', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getSyncJob(id: string): Promise<SyncJobStatus> {
  return requestJson<SyncJobStatus>(`/v3/ops/sync/${id}`)
}

export interface PrunePreviewResponse {
  ok: boolean
  candidates: PruneCandidate[]
}

export interface PruneExecuteResponse {
  ok: boolean
  dry_run: boolean
  force: boolean
  removed: string[]
  paths?: string[]
  errors?: Array<{ path: string; message: string }>
}

export function postPrunePreview(body: {
  project: string
  include_hidden?: boolean
}): Promise<PrunePreviewResponse> {
  return requestJson<PrunePreviewResponse>('/v3/ops/prune/preview', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function postPrune(body: {
  project: string
  paths: string[]
  dry_run?: boolean
  force?: boolean
}): Promise<PruneExecuteResponse> {
  return requestJson<PruneExecuteResponse>('/v3/ops/prune', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
