export type ConfigOpKind = 'enable' | 'disable' | 'set'

export interface ConfigOperation {
  op: ConfigOpKind
  path: string
  value?: unknown
}

export interface SchemaFieldNode {
  path: string
  key: string
  type: string
  description?: string | null
  required?: boolean
  enabled?: boolean
  editable?: boolean
  sensitive?: boolean
  default_value?: unknown
  value?: unknown
  enum_options?: string[]
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

export function getWorkspace(): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>('/v2/workspace')
}

export function postHealth(
  body: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>('/v3/ops/health', {
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

export function postPrunePreview(
  body: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>('/v3/ops/prune/preview', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function postPrune(
  body: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>('/v3/ops/prune', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
