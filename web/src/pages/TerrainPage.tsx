import { useQuery } from '@tanstack/react-query'
import { Suspense, lazy, useMemo, useState } from 'react'
import type { RepositoryTerrainNode } from '../api/client'
import { DEFAULT_LAYERS, type TerrainLayerState } from '../components/terrain/terrainLayers'
import TerrainDetailPanel from '../components/terrain/TerrainDetailPanel'
import TerrainLayerControls from '../components/terrain/TerrainLayerControls'
import TerrainViewControls, {
  DEFAULT_VIEW_OPTIONS,
} from '../components/terrain/TerrainViewControls'
import type { TerrainViewOptions } from '../components/terrain/terrainViewOptions'
import {
  fetchTerrainEnriched,
  fetchTerrainManifest,
  terrainEnrichedQueryKey,
  terrainManifestQueryKey,
  type TerrainProjectFilter,
} from './terrainQueries'
import styles from './TerrainPage.module.css'

const RepositoryTerrainCanvas = lazy(
  () => import('../components/terrain/RepositoryTerrainCanvas'),
)

export default function TerrainPage() {
  const [layers, setLayers] = useState<TerrainLayerState>({ ...DEFAULT_LAYERS })
  const [selected, setSelected] = useState<RepositoryTerrainNode | null>(null)
  const [hovered, setHovered] = useState<RepositoryTerrainNode | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })
  const [projectFilter, setProjectFilter] = useState<TerrainProjectFilter>('all')
  const [includePipelines, setIncludePipelines] = useState(false)
  const [viewOptions, setViewOptions] = useState<TerrainViewOptions>({
    layout: { ...DEFAULT_VIEW_OPTIONS.layout },
    visual: { ...DEFAULT_VIEW_OPTIONS.visual },
  })

  const manifestQuery = useQuery({
    queryKey: terrainManifestQueryKey(projectFilter),
    queryFn: () => fetchTerrainManifest(projectFilter),
    staleTime: 15_000,
  })

  const enrichedQuery = useQuery({
    queryKey: terrainEnrichedQueryKey(projectFilter, includePipelines, true),
    queryFn: () =>
      fetchTerrainEnriched({
        project: projectFilter,
        includePipelines,
        includeInferred: true,
      }),
    enabled: manifestQuery.isSuccess,
    staleTime: 30_000,
  })

  const displayData = enrichedQuery.data ?? manifestQuery.data
  const projectOptions = manifestQuery.data?.projects ?? enrichedQuery.data?.projects ?? []
  const showManifestOnly =
    displayData?.detail_level === 'manifest' ||
    (enrichedQuery.isFetching && !enrichedQuery.data)
  const isInitialLoad = manifestQuery.isLoading && !displayData
  const loadError = manifestQuery.error ?? enrichedQuery.error

  const summary = useMemo(() => {
    if (!displayData) {
      return null
    }
    const dirty = displayData.nodes.filter((node) => node.git.dirty).length
    const behind = displayData.nodes.filter((node) => node.git.behind > 0).length
    const failed = displayData.nodes.filter(
      (node) => node.pipeline?.status === 'failed',
    ).length
    return {
      total: displayData.node_count,
      dirty,
      behind,
      failed,
      deps: displayData.dependencies.length,
    }
  }, [displayData])

  const refreshAll = (): void => {
    void manifestQuery.refetch()
    if (manifestQuery.isSuccess) {
      void enrichedQuery.refetch()
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.toolbar}>
        <div>
          <h1 className={styles.title}>Repository Terrain</h1>
          <p className={styles.subtitle}>
            Manifest layout loads first; git, activity, and CI enrich in the background.
          </p>
        </div>
        <div className={styles.actions}>
          <label className={styles.fieldLabel}>
            Project
            <select
              className={styles.select}
              value={projectFilter}
              onChange={(event) => {
                setSelected(null)
                setProjectFilter(
                  event.target.value === 'all' ? 'all' : event.target.value,
                )
              }}
            >
              <option value="all">All projects</option>
              {projectOptions.map((project) => (
                <option key={project.name} value={project.name}>
                  {project.name} ({project.repo_count})
                </option>
              ))}
            </select>
          </label>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={includePipelines}
              onChange={(event) => setIncludePipelines(event.target.checked)}
            />
            Live CI lookup
          </label>
          <button type="button" className={styles.refresh} onClick={refreshAll}>
            {manifestQuery.isFetching || enrichedQuery.isFetching
              ? 'Refreshing…'
              : 'Refresh'}
          </button>
        </div>
      </header>

      {summary ? (
        <div className={styles.stats} aria-label="Terrain summary">
          <span>{summary.total} repos</span>
          <span>{summary.dirty} dirty</span>
          <span>{summary.behind} behind</span>
          <span>{summary.failed} CI failed</span>
          <span>{summary.deps} dependency arcs</span>
          {showManifestOnly ? (
            <span className={styles.enriching}>Enriching git &amp; activity…</span>
          ) : null}
        </div>
      ) : null}

      <div className={styles.viewport}>
        {isInitialLoad ? (
          <p className={styles.message}>Loading manifest layout…</p>
        ) : null}
        {loadError ? (
          <p className={styles.error}>
            {loadError instanceof Error ? loadError.message : 'Failed to load terrain.'}
          </p>
        ) : null}
        {displayData && !manifestQuery.isError ? (
          <>
            <Suspense fallback={<p className={styles.message}>Loading 3D view…</p>}>
              <RepositoryTerrainCanvas
                data={displayData}
                layers={layers}
                viewOptions={viewOptions}
                onSelect={setSelected}
                onHover={(node, x, y) => {
                  setHovered(node)
                  setTooltipPos({ x, y })
                }}
              />
            </Suspense>
            <TerrainLayerControls layers={layers} onChange={setLayers} />
            <TerrainViewControls options={viewOptions} onChange={setViewOptions} />
            <TerrainDetailPanel node={selected} onClose={() => setSelected(null)} />
            {hovered && !selected ? (
              <div
                className={styles.tooltip}
                style={{ left: tooltipPos.x + 12, top: tooltipPos.y + 12 }}
              >
                <strong>{hovered.repo_name}</strong>
                <span>{hovered.project_name}</span>
                <span>{hovered.git.branch ?? hovered.local_status}</span>
                {hovered.git.dirty ? (
                  <span>
                    Modified {hovered.git.modified_count} · Untracked{' '}
                    {hovered.git.untracked_count}
                  </span>
                ) : null}
                {hovered.pipeline ? <span>CI: {hovered.pipeline.status}</span> : null}
              </div>
            ) : null}
          </>
        ) : null}
      </div>

      <footer className={styles.legend} aria-label="Terrain legend">
        <span>Flat green: synced on default branch, clean</span>
        <span>Bulge up: unpushed commits + uncommitted files</span>
        <span>Depressed: behind remote · colors: branch kind</span>
        <span>Layouts: hierarchy · grid · sphere · solid/rich styles</span>
        <span>Beacons: CI status</span>
      </footer>
    </div>
  )
}
