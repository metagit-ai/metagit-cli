import type { RepositoryTerrainNode } from '../../api/client'

export type TerrainLayoutMode = 'hierarchy' | 'grid' | 'sphere'

export const GRID_COLUMN_OPTIONS = [4, 6, 8, 10, 12, 16] as const
export type TerrainGridColumns = (typeof GRID_COLUMN_OPTIONS)[number] | 'auto'

export interface TerrainLayoutOptions {
  mode: TerrainLayoutMode
  gridColumns: TerrainGridColumns
}

export type TerrainVisualStyle = 'rich' | 'solid'

export interface TerrainVisualPreferences {
  style: TerrainVisualStyle
  animations: boolean
}

export interface TerrainViewOptions {
  layout: TerrainLayoutOptions
  visual: TerrainVisualPreferences
}

export interface TerrainLayoutSlot {
  x: number
  y: number
  z: number
  normalX: number
  normalY: number
  normalZ: number
}

export const DEFAULT_LAYOUT: TerrainLayoutOptions = {
  mode: 'hierarchy',
  gridColumns: 'auto',
}

export const DEFAULT_VISUAL: TerrainVisualPreferences = {
  style: 'rich',
  animations: true,
}

export const DEFAULT_VIEW_OPTIONS: TerrainViewOptions = {
  layout: DEFAULT_LAYOUT,
  visual: DEFAULT_VISUAL,
}

const GRID_SPACING = 2.8

function sortNodes(nodes: RepositoryTerrainNode[]): RepositoryTerrainNode[] {
  return [...nodes].sort((left, right) => {
    const leftKey = `${left.project_name}/${left.repo_name}`
    const rightKey = `${right.project_name}/${right.repo_name}`
    return leftKey.localeCompare(rightKey)
  })
}

function gridColumnCount(count: number, gridColumns: TerrainGridColumns): number {
  if (gridColumns === 'auto') {
    return Math.max(1, Math.ceil(Math.sqrt(count)))
  }
  return gridColumns
}

function hierarchySlot(node: RepositoryTerrainNode): TerrainLayoutSlot {
  return {
    x: node.coordinates.x,
    y: 0,
    z: node.coordinates.y,
    normalX: 0,
    normalY: 1,
    normalZ: 0,
  }
}

function gridSlot(index: number, columns: number): TerrainLayoutSlot {
  const col = index % columns
  const row = Math.floor(index / columns)
  return {
    x: col * GRID_SPACING,
    y: 0,
    z: row * GRID_SPACING,
    normalX: 0,
    normalY: 1,
    normalZ: 0,
  }
}

function sphereSlot(index: number, count: number): TerrainLayoutSlot {
  const radius = Math.max(14, 2.4 * Math.sqrt(count))
  const golden = Math.PI * (3 - Math.sqrt(5))
  const yNorm = count <= 1 ? 0 : 1 - (index / (count - 1)) * 2
  const ring = Math.sqrt(Math.max(0, 1 - yNorm * yNorm))
  const theta = golden * index
  const x = Math.cos(theta) * ring * radius
  const z = Math.sin(theta) * ring * radius
  const y = yNorm * radius
  const normalLength = Math.hypot(x, y, z) || 1
  return {
    x,
    y,
    z,
    normalX: x / normalLength,
    normalY: y / normalLength,
    normalZ: z / normalLength,
  }
}

export function resolveTerrainLayout(
  nodes: RepositoryTerrainNode[],
  layout: TerrainLayoutOptions,
): TerrainLayoutSlot[] {
  const ordered = sortNodes(nodes)
  if (layout.mode === 'hierarchy') {
    return ordered.map(hierarchySlot)
  }
  if (layout.mode === 'grid') {
    const columns = gridColumnCount(ordered.length, layout.gridColumns)
    return ordered.map((_node, index) => gridSlot(index, columns))
  }
  return ordered.map((_node, index) => sphereSlot(index, ordered.length))
}

export function sortTerrainNodes(nodes: RepositoryTerrainNode[]): RepositoryTerrainNode[] {
  return sortNodes(nodes)
}

export function layoutUsesFlatGround(mode: TerrainLayoutMode): boolean {
  return mode === 'hierarchy' || mode === 'grid'
}
