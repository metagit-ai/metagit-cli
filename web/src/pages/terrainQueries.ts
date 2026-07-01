import { getRepositoryTerrain, type RepositoryTerrainResponse } from '../api/client'

export type TerrainProjectFilter = 'all' | string

export interface TerrainFetchOptions {
  project?: TerrainProjectFilter
  includePipelines?: boolean
  includeInferred?: boolean
}

function projectParam(project: TerrainProjectFilter | undefined): string | undefined {
  if (!project || project === 'all') {
    return undefined
  }
  return project
}

export const terrainManifestQueryKey = (
  project: TerrainProjectFilter,
) => ['repository-terrain', 'manifest', project] as const

export const terrainEnrichedQueryKey = (
  project: TerrainProjectFilter,
  includePipelines: boolean,
  includeInferred: boolean,
) =>
  [
    'repository-terrain',
    'enriched',
    project,
    includePipelines,
    includeInferred,
  ] as const

export async function fetchTerrainManifest(
  project: TerrainProjectFilter = 'all',
): Promise<RepositoryTerrainResponse> {
  const view = await getRepositoryTerrain({
    detail: 'manifest',
    project: projectParam(project),
    includeInferred: false,
  })
  if (!view.ok) {
    throw new Error('Failed to load repository terrain manifest')
  }
  return view
}

export async function fetchTerrainEnriched(
  options: TerrainFetchOptions = {},
): Promise<RepositoryTerrainResponse> {
  const view = await getRepositoryTerrain({
    detail: 'enriched',
    project: projectParam(options.project),
    includePipelines: options.includePipelines === true,
    includeInferred: options.includeInferred !== false,
  })
  if (!view.ok) {
    throw new Error('Failed to enrich repository terrain')
  }
  return view
}
