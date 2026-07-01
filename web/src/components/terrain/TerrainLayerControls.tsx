import type { TerrainLayerState } from './terrainLayers'
import styles from './TerrainLayerControls.module.css'

export interface TerrainLayerControlsProps {
  layers: TerrainLayerState
  onChange: (layers: TerrainLayerState) => void
}

const LAYER_ITEMS: Array<{ key: keyof TerrainLayerState; label: string }> = [
  { key: 'terrain', label: 'Terrain' },
  { key: 'gitState', label: 'Git state' },
  { key: 'workingTree', label: 'Working tree' },
  { key: 'cicd', label: 'CI/CD' },
  { key: 'dependencies', label: 'Dependencies' },
  { key: 'ownership', label: 'Ownership' },
  { key: 'agent', label: 'Agent layer' },
]

export default function TerrainLayerControls({
  layers,
  onChange,
}: TerrainLayerControlsProps) {
  return (
    <div className={styles.panel} aria-label="Visualization layers">
      <p className={styles.heading}>Layers</p>
      <ul className={styles.list}>
        {LAYER_ITEMS.map(({ key, label }) => (
          <li key={key}>
            <label className={styles.item}>
              <input
                type="checkbox"
                checked={layers[key]}
                onChange={(event) =>
                  onChange({ ...layers, [key]: event.target.checked })
                }
              />
              <span>{label}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )
}
