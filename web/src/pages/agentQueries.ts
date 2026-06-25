import {
  getAgentCatalog,
  getAgentPreview,
  getAgentTemplate,
  getObjectives,
  patchObjective,
  getSessionDigest,
  postAgentOverlayInit,
  postSessionBegin,
  type AgentCatalogEntry,
  type AgentCatalogResponse,
  type ObjectiveEditRequest,
  type AgentOverlayInitOptions,
  type AgentOverlayInitResponse,
  type AgentPreviewResponse,
  type AgentTemplateDetailResponse,
  type ObjectiveRow,
  type ObjectiveListResponse,
  type SessionBeginResponse,
  type SessionDigestResponse,
} from '../api/client'

export const agentCatalogQueryKey = ['agents', 'catalog'] as const
export const objectivesQueryKey = ['agents', 'objectives'] as const
export const sessionDigestQueryKey = ['agents', 'session'] as const

export function fetchAgentCatalog(): Promise<AgentCatalogResponse> {
  return getAgentCatalog()
}

export function fetchObjectives(): Promise<ObjectiveListResponse> {
  return getObjectives()
}

export function saveObjective(
  id: string,
  body: ObjectiveEditRequest,
): Promise<ObjectiveRow> {
  return patchObjective(id, body)
}

export function fetchSessionDigest(): Promise<SessionDigestResponse> {
  return getSessionDigest()
}

export function beginSession(body?: {
  project_name?: string
  repo_name?: string
  max_tokens?: number
}): Promise<SessionBeginResponse> {
  return postSessionBegin(body)
}

export function agentTemplateQueryKey(templateId: string) {
  return ['agents', 'template', templateId] as const
}

export function fetchAgentTemplate(templateId: string): Promise<AgentTemplateDetailResponse> {
  return getAgentTemplate(templateId)
}

export function agentPreviewQueryKey(templateId: string, vendor: string) {
  return ['agents', 'preview', templateId, vendor] as const
}

export function fetchAgentPreview(
  templateId: string,
  vendor: string,
): Promise<AgentPreviewResponse> {
  return getAgentPreview(templateId, vendor)
}

export function initAgentOverlay(
  templateId: string,
  options?: AgentOverlayInitOptions,
): Promise<AgentOverlayInitResponse> {
  return postAgentOverlayInit(templateId, {
    scope: 'committed',
    ...options,
  })
}

export function groupAgentsByCategory(
  templates: AgentCatalogEntry[],
): Map<string, AgentCatalogEntry[]> {
  const grouped = new Map<string, AgentCatalogEntry[]>()
  for (const entry of templates) {
    const category = entry.ui.category || 'General'
    const bucket = grouped.get(category) ?? []
    bucket.push(entry)
    grouped.set(category, bucket)
  }
  for (const [, bucket] of grouped) {
    bucket.sort((left, right) => left.ui.sort_order - right.ui.sort_order)
  }
  return grouped
}
