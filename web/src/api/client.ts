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
  refresh_sources?: boolean
  project_name?: string | null
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
  autoFormat = true,
): Promise<ConfigTreeResponse> {
  return requestJson<ConfigTreeResponse>('/v3/config/metagit', {
    method: 'PATCH',
    body: JSON.stringify({ operations: ops, save, auto_format: autoFormat }),
  })
}

export function patchAppconfig(
  ops: ConfigOperation[],
  save: boolean,
  autoFormat = true,
): Promise<ConfigTreeResponse> {
  return requestJson<ConfigTreeResponse>('/v3/config/appconfig', {
    method: 'PATCH',
    body: JSON.stringify({ operations: ops, save, auto_format: autoFormat }),
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
  protected?: boolean
  tags?: Record<string, string>
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

export type PipelineStatus =
  | 'passed'
  | 'failed'
  | 'running'
  | 'pending'
  | 'canceled'
  | 'skipped'
  | 'unknown'

export interface ProviderDiagnosticsRow {
  provider: 'github' | 'gitlab' | string
  enabled: boolean
  available: boolean
  auth_source: string
  base_url?: string | null
}

export interface PipelineProvidersResponse {
  ok: boolean
  fetched_at: string
  providers: ProviderDiagnosticsRow[]
}

export interface PipelineStatusRow {
  project_name: string
  repo_name: string
  provider: 'github' | 'gitlab' | 'unknown' | string
  repo_url?: string | null
  repo_path?: string | null
  local_status: 'synced' | 'configured_missing' | string
  branch_used?: string | null
  pipeline_status: PipelineStatus | string
  pipeline_name?: string | null
  updated_at?: string | null
  duration_sec?: number | null
  web_url?: string | null
  source: 'live' | 'cache' | 'fallback' | string
  reason?: string | null
}

export interface PipelineStatusResponse {
  ok: boolean
  fetched_at: string
  summary: Record<string, number>
  rows: PipelineStatusRow[]
  errors: Array<{ project_name: string; repo_name: string; message: string }>
}

export interface PipelineStatusOptions {
  project?: string
  provider?: 'github' | 'gitlab' | 'all'
  status?: PipelineStatus | 'all'
  repos?: string[]
  includeUnsynced?: boolean
  limit?: number
}

export interface PruneCandidate {
  path: string
  name: string
}

export function getWorkspace(): Promise<CatalogEnvelope<WorkspaceData>> {
  return requestJson<CatalogEnvelope<WorkspaceData>>('/v2/workspace')
}

export function getPipelineProviders(): Promise<PipelineProvidersResponse> {
  return requestJson<PipelineProvidersResponse>('/v3/ops/pipelines/providers')
}

export function getPipelineStatus(
  options: PipelineStatusOptions = {},
): Promise<PipelineStatusResponse> {
  const params = new URLSearchParams()
  if (options.project) {
    params.set('project', options.project)
  }
  if (options.provider && options.provider !== 'all') {
    params.set('provider', options.provider)
  }
  if (options.status && options.status !== 'all') {
    params.set('status', options.status)
  }
  for (const repo of options.repos ?? []) {
    if (repo.trim()) {
      params.append('repo', repo.trim())
    }
  }
  if (options.includeUnsynced === false) {
    params.set('include_unsynced', 'false')
  }
  if (typeof options.limit === 'number') {
    params.set('limit', String(options.limit))
  }
  const query = params.toString()
  const path = query
    ? `/v3/ops/pipelines/status?${query}`
    : '/v3/ops/pipelines/status'
  return requestJson<PipelineStatusResponse>(path)
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

export interface OpenPathRequest {
  path: string
  editor?: string
}

export interface OpenPathResponse {
  ok: boolean
  path?: string
  editor?: string
  error?: { kind: string; message: string }
}

export function postOpenPath(body: OpenPathRequest): Promise<OpenPathResponse> {
  return requestJson<OpenPathResponse>('/v3/ops/open', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export interface ApprovalRequestRow {
  id: string
  action: string
  status: 'pending' | 'approved' | 'denied'
  requested_by: string
  payload: Record<string, unknown>
  created_at: string
  resolved_at?: string | null
  resolver_note?: string | null
}

export interface ApprovalListResponse {
  ok: boolean
  requests: ApprovalRequestRow[]
}

export type ObjectiveStatus = 'pending' | 'in_progress' | 'done' | 'cancelled'

export interface ObjectiveRow {
  id: string
  status: ObjectiveStatus
  title: string
  repos: string[]
  acceptance?: string | null
  human_notes?: string | null
  agent_notes?: string | null
  created_at: string
  updated_at: string
}

export interface ObjectiveListResponse {
  ok: boolean
  objectives: ObjectiveRow[]
}

export interface ObjectiveUpsertRequest {
  id: string
  title: string
  status?: ObjectiveStatus
  repos?: string[]
  acceptance?: string | null
  human_notes?: string | null
  agent_notes?: string | null
}

export interface ObjectiveEditRequest {
  status?: ObjectiveStatus
  title?: string
  repos?: string[]
  acceptance?: string | null
  human_notes?: string | null
  agent_notes?: string | null
}

export interface SessionDigestRepoChange {
  project_name: string
  repo_name: string
  repo_path: string
  commit_count: number
  recent_subjects: string[]
  error?: string | null
}

export interface SessionDigestResponse {
  tier: 2
  since?: string | null
  first_session: boolean
  manifest_changed: boolean
  active_objective_id?: string | null
  repo_changes: SessionDigestRepoChange[]
}

export interface SessionBeginResponse {
  ok: boolean
  schema_version: string
  workspace_name: string
  active_project?: string | null
  session: Record<string, unknown>
  objectives: ObjectiveRow[]
  approvals: ApprovalRequestRow[]
  pack: Record<string, unknown>
  prompt: string
  warnings: string[]
}

export function getApprovals(status: 'pending' | 'approved' | 'denied' | 'all' = 'pending'): Promise<ApprovalListResponse> {
  const query = status === 'pending' ? '' : `?status=${encodeURIComponent(status)}`
  return requestJson<ApprovalListResponse>(`/v3/ops/approvals${query}`)
}

export function getObjectives(): Promise<ObjectiveListResponse> {
  return requestJson<ObjectiveListResponse>('/v3/ops/objectives')
}

export function postObjective(body: ObjectiveUpsertRequest): Promise<ObjectiveRow> {
  return requestJson<ObjectiveRow>('/v3/ops/objectives', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function patchObjective(id: string, body: ObjectiveEditRequest): Promise<ObjectiveRow> {
  return requestJson<ObjectiveRow>(`/v3/ops/objectives/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function getSessionDigest(): Promise<SessionDigestResponse> {
  return requestJson<SessionDigestResponse>('/v3/ops/session')
}

export function postSessionBegin(body?: {
  project_name?: string
  repo_name?: string
  max_tokens?: number
}): Promise<SessionBeginResponse> {
  return requestJson<SessionBeginResponse>('/v3/ops/session/begin', {
    method: 'POST',
    body: JSON.stringify(body ?? {}),
  })
}

export function resolveApproval(
  id: string,
  body: { decision: 'approved' | 'denied'; note?: string | null },
): Promise<ApprovalRequestRow> {
  return requestJson<ApprovalRequestRow>(`/v3/ops/approvals/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export interface SourceSyncRequest {
  project_name: string
  from_manifest?: boolean
  source_id?: string | null
  apply?: boolean
  force?: boolean
  sync?: boolean
  requested_by?: string
}

export interface SourceSyncResponse {
  ok: boolean
  applied?: boolean
  pending_approval_id?: string | null
  plan?: Record<string, unknown>
  errors?: Array<{ kind?: string; message?: string }>
}

export function postSourceSync(body: SourceSyncRequest): Promise<SourceSyncResponse> {
  return requestJson<SourceSyncResponse>('/v3/ops/source-sync', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export interface WorkspaceGrepHit {
  project_name?: string | null
  repo_name?: string | null
  repo_path: string
  file_path: string
  line_number: number
  line: string
  context_before?: string[]
  context_after?: string[]
  match_kind?: 'content' | 'path' | string
}

export interface WorkspaceGrepResult {
  ok: boolean
  data?: { hits: WorkspaceGrepHit[] }
  error?: { kind: string; message: string } | null
}

export interface WorkspaceGrepOptions {
  q: string
  project?: string
  repos?: string[]
  preset?: string
  intent?: string
  maxResults?: number
  contextLines?: number
  includePaths?: boolean
}

export function getWorkspaceGrep(
  options: WorkspaceGrepOptions,
): Promise<WorkspaceGrepResult> {
  const params = new URLSearchParams()
  params.set('q', options.q)
  if (options.project) {
    params.set('project', options.project)
  }
  for (const repo of options.repos ?? []) {
    if (repo.trim()) {
      params.append('repo', repo.trim())
    }
  }
  if (options.preset) {
    params.set('preset', options.preset)
  }
  if (options.intent) {
    params.set('intent', options.intent)
  }
  if (options.maxResults !== undefined) {
    params.set('max_results', String(options.maxResults))
  }
  if (options.contextLines !== undefined) {
    params.set('context_lines', String(options.contextLines))
  }
  if (options.includePaths) {
    params.set('include_paths', 'true')
  }
  return requestJson<WorkspaceGrepResult>(`/v2/workspace/grep?${params.toString()}`)
}

export interface WorkspaceGrepInfo {
  ripgrep_available: boolean
  ripgrep_path: string | null
  ripgrep_version: string | null
  search_backend: 'ripgrep' | 'python_walk' | string
}

export interface WorkspaceGrepInfoResult {
  ok: boolean
  data?: WorkspaceGrepInfo
  error?: { kind: string; message: string } | null
}

export function getWorkspaceGrepInfo(): Promise<WorkspaceGrepInfoResult> {
  return requestJson<WorkspaceGrepInfoResult>('/v2/workspace/grep/info')
}

export interface AgentUiSpec {
  category: string
  icon?: string
  color?: string
  sort_order: number
}

export interface AgentCatalogEntry {
  id: string
  label: string
  description: string
  archetype: 'control_plane' | 'specialist'
  scope: 'workspace' | 'project' | 'repo'
  status: 'stable' | 'beta'
  version: string
  source: 'bundled' | 'overlay' | 'merged'
  overlay_path?: string | null
  ui: AgentUiSpec
  prompt_kinds: string[]
  mcp_tools: string[]
  recommended_skills: string[]
  external_skills: Array<{ name: string; note: string }>
  vendors: string[]
  delegates_to: string[]
  delegated_by: string[]
}

export interface AgentCatalogEnvelope {
  schema_version: string
  templates: AgentCatalogEntry[]
  taxonomy: {
    archetypes: string[]
    scopes: string[]
    vendors: string[]
    categories: string[]
  }
}

export interface AgentCatalogResponse {
  ok: boolean
  catalog: AgentCatalogEnvelope
}

export interface AgentTemplateDetailResponse {
  ok: boolean
  template: {
    source: AgentCatalogEntry['source']
    overlay_path?: string | null
    manifest: Record<string, unknown>
    template_files: string[]
  }
}

export interface AgentPreviewResponse {
  ok: boolean
  preview: {
    template_id: string
    vendor: string
    filename: string
    content: string
    source: AgentCatalogEntry['source']
  }
}

export function getAgentCatalog(): Promise<AgentCatalogResponse> {
  return requestJson<AgentCatalogResponse>('/v3/agents/catalog')
}

export function getAgentTemplate(templateId: string): Promise<AgentTemplateDetailResponse> {
  return requestJson<AgentTemplateDetailResponse>(
    `/v3/agents/templates/${encodeURIComponent(templateId)}`,
  )
}

export function getAgentPreview(
  templateId: string,
  vendor: string,
): Promise<AgentPreviewResponse> {
  const params = new URLSearchParams({ vendor })
  return requestJson<AgentPreviewResponse>(
    `/v3/agents/templates/${encodeURIComponent(templateId)}/preview?${params.toString()}`,
  )
}

export interface AgentOverlayInitOptions {
  mode?: 'minimal' | 'full'
  scope?: 'committed' | 'local'
  force?: boolean
  dry_run?: boolean
}

export interface AgentOverlayInitResponse {
  ok: boolean
    overlay?: {
    template_id: string
    overlay_path: string
    scope: 'committed' | 'local'
    mode: 'minimal' | 'full'
    paths: string[]
    dry_run: boolean
  }
  error?: { kind: string; message: string }
}

export function postAgentOverlayInit(
  templateId: string,
  options: AgentOverlayInitOptions = {},
): Promise<AgentOverlayInitResponse> {
  return requestJson<AgentOverlayInitResponse>(
    `/v3/agents/templates/${encodeURIComponent(templateId)}/overlay/init`,
    {
      method: 'POST',
      body: JSON.stringify({
        mode: options.mode ?? 'full',
        scope: options.scope ?? 'committed',
        force: options.force ?? false,
        dry_run: options.dry_run ?? false,
      }),
    },
  )
}
