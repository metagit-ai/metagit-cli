import { useEffect, useRef, useState } from 'react'
import type { RepositoryTerrainNode, RepositoryTerrainResponse } from '../../api/client'
import type { TerrainLayerState } from './terrainLayers'
import type { TerrainViewOptions } from './terrainViewOptions'

type TerrainSceneModule = typeof import('./terrainScene')

export interface RepositoryTerrainCanvasProps {
  data: RepositoryTerrainResponse | undefined
  layers: TerrainLayerState
  viewOptions: TerrainViewOptions
  onSelect: (node: RepositoryTerrainNode | null) => void
  onHover: (node: RepositoryTerrainNode | null, x: number, y: number) => void
}

export default function RepositoryTerrainCanvas({
  data,
  layers,
  viewOptions,
  onSelect,
  onHover,
}: RepositoryTerrainCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<InstanceType<TerrainSceneModule['RepositoryTerrainScene']> | null>(
    null,
  )
  const callbacksRef = useRef({ onSelect, onHover })
  const dataRef = useRef(data)
  const layersRef = useRef(layers)
  const viewOptionsRef = useRef(viewOptions)
  const [sceneReady, setSceneReady] = useState(false)
  callbacksRef.current = { onSelect, onHover }
  dataRef.current = data
  layersRef.current = layers
  viewOptionsRef.current = viewOptions

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return undefined
    }

    let cancelled = false
    let scene: InstanceType<TerrainSceneModule['RepositoryTerrainScene']> | null = null

    void import('./terrainScene').then((module) => {
      if (cancelled || !containerRef.current) {
        return
      }
      scene = new module.RepositoryTerrainScene(containerRef.current, {
        onSelect: (node) => callbacksRef.current.onSelect(node),
        onHover: (node, x, y) => callbacksRef.current.onHover(node, x, y),
      })
      sceneRef.current = scene
      scene.setViewOptions(viewOptionsRef.current)
      scene.setLayers(layersRef.current)
      if (dataRef.current) {
        scene.setData(dataRef.current)
      }
      setSceneReady(true)
    })

    return () => {
      cancelled = true
      scene?.dispose()
      sceneRef.current = null
      setSceneReady(false)
    }
  }, [])

  useEffect(() => {
    if (!sceneReady) {
      return
    }
    sceneRef.current?.setLayers(layers)
  }, [layers, sceneReady])

  useEffect(() => {
    if (!sceneReady) {
      return
    }
    sceneRef.current?.setViewOptions(viewOptions)
  }, [viewOptions, sceneReady])

  useEffect(() => {
    if (!sceneReady || !data) {
      return
    }
    sceneRef.current?.setData(data)
  }, [data, sceneReady])

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      {!sceneReady ? (
        <p
          style={{
            position: 'absolute',
            inset: 0,
            display: 'grid',
            placeItems: 'center',
            margin: 0,
            color: '#94a3b8',
            fontSize: '0.9rem',
            pointerEvents: 'none',
          }}
        >
          Loading 3D engine…
        </p>
      ) : null}
    </div>
  )
}

export { DEFAULT_LAYERS, type TerrainLayerState } from './terrainLayers'
export { DEFAULT_VIEW_OPTIONS, type TerrainViewOptions } from './terrainViewOptions'
