import { getWorkspaceGraph, type WorkspaceGraphView } from '../api/client'

export const graphQueryKey = (includeInferred: boolean, includeStructure: boolean) =>
  ['workspace-graph', includeInferred, includeStructure] as const

export async function fetchWorkspaceGraph(
  includeInferred: boolean,
  includeStructure: boolean,
): Promise<WorkspaceGraphView> {
  const view = await getWorkspaceGraph({
    includeInferred,
    includeStructure,
  })
  if (!view.ok) {
    throw new Error('Failed to load workspace graph')
  }
  return view
}
