import {
  DEFAULT_VIEW_OPTIONS,
  GRID_COLUMN_OPTIONS,
  type TerrainGridColumns,
  type TerrainLayoutMode,
  type TerrainViewOptions,
  type TerrainVisualStyle,
} from './terrainViewOptions'
import styles from './TerrainViewControls.module.css'

export interface TerrainViewControlsProps {
  options: TerrainViewOptions
  onChange: (options: TerrainViewOptions) => void
}

const LAYOUT_LABELS: Record<TerrainLayoutMode, string> = {
  hierarchy: 'Filesystem hierarchy',
  grid: 'Grid matrix',
  sphere: 'Sphere wrap',
}

export default function TerrainViewControls({
  options,
  onChange,
}: TerrainViewControlsProps) {
  const showGridColumns = options.layout.mode === 'grid'
  const isSolid = options.visual.style === 'solid'

  return (
    <div className={styles.panel} aria-label="Layout and visual preferences">
      <p className={styles.heading}>View</p>
      <div className={styles.fields}>
        <label className={styles.field}>
          Layout
          <select
            className={styles.select}
            value={options.layout.mode}
            onChange={(event) => {
              const mode = event.target.value as TerrainLayoutMode
              onChange({
                ...options,
                layout: { ...options.layout, mode },
              })
            }}
          >
            {(Object.keys(LAYOUT_LABELS) as TerrainLayoutMode[]).map((mode) => (
              <option key={mode} value={mode}>
                {LAYOUT_LABELS[mode]}
              </option>
            ))}
          </select>
        </label>

        {showGridColumns ? (
          <label className={styles.field}>
            Grid columns
            <select
              className={styles.select}
              value={String(options.layout.gridColumns)}
              onChange={(event) => {
                const raw = event.target.value
                const gridColumns: TerrainGridColumns =
                  raw === 'auto' ? 'auto' : (Number(raw) as TerrainGridColumns)
                onChange({
                  ...options,
                  layout: { ...options.layout, gridColumns },
                })
              }}
            >
              <option value="auto">Auto (√n)</option>
              {GRID_COLUMN_OPTIONS.map((columns) => (
                <option key={columns} value={columns}>
                  {columns} columns
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <label className={styles.field}>
          Repo style
          <select
            className={styles.select}
            value={options.visual.style}
            onChange={(event) => {
              const style = event.target.value as TerrainVisualStyle
              onChange({
                ...options,
                visual: {
                  style,
                  animations: style === 'solid' ? false : options.visual.animations,
                },
              })
            }}
          >
            <option value="rich">Rich (elevation + effects)</option>
            <option value="solid">Solid (flat colors)</option>
          </select>
        </label>

        <label className={styles.check}>
          <input
            type="checkbox"
            checked={options.visual.animations}
            disabled={isSolid}
            onChange={(event) =>
              onChange({
                ...options,
                visual: { ...options.visual, animations: event.target.checked },
              })
            }
          />
          <span>Animations</span>
        </label>
      </div>
    </div>
  )
}

export { DEFAULT_VIEW_OPTIONS }
