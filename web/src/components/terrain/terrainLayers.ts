export interface TerrainLayerState {
  terrain: boolean
  gitState: boolean
  workingTree: boolean
  cicd: boolean
  dependencies: boolean
  ownership: boolean
  agent: boolean
}

export const DEFAULT_LAYERS: TerrainLayerState = {
  terrain: true,
  gitState: true,
  workingTree: true,
  cicd: true,
  dependencies: true,
  ownership: false,
  agent: false,
}
