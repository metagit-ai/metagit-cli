import type { RepositoryTerrainNode } from '../../api/client'
import styles from './TerrainDetailPanel.module.css'

export interface TerrainDetailPanelProps {
  node: RepositoryTerrainNode | null
  onClose: () => void
}

function driftLabel(ahead: number, behind: number): string {
  if (ahead > 0 && behind > 0) {
    return `${ahead} ahead, ${behind} behind`
  }
  if (ahead > 0) {
    return `${ahead} ahead`
  }
  if (behind > 0) {
    return `${behind} behind`
  }
  return 'Synchronized'
}

export default function TerrainDetailPanel({ node, onClose }: TerrainDetailPanelProps) {
  if (!node) {
    return null
  }

  const dirtyLabel = node.git.dirty
    ? `${node.git.uncommitted_count} uncommitted (${node.git.untracked_count} untracked)`
    : 'Clean'

  return (
    <aside className={styles.panel} aria-label="Repository details">
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>{node.repo_name}</h2>
          <p className={styles.subtitle}>
            {node.project_name} · {node.local_status}
          </p>
        </div>
        <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
          ×
        </button>
      </header>

      <dl className={styles.grid}>
        <div>
          <dt>Path</dt>
          <dd>{node.repo_path}</dd>
        </div>
        {node.configured_path ? (
          <div>
            <dt>Configured path</dt>
            <dd>{node.configured_path}</dd>
          </div>
        ) : null}
        <div>
          <dt>Tile state</dt>
          <dd>{node.visual.state_label}</dd>
        </div>
        <div>
          <dt>Local pressure</dt>
          <dd>
            {node.visual.local_pressure} (unpushed + uncommitted)
            {node.visual.elevation !== 0
              ? ` · elevation ${node.visual.elevation.toFixed(2)}`
              : ' · flat'}
          </dd>
        </div>
        <div>
          <dt>Default branch</dt>
          <dd>{node.git.default_branch ?? '—'}</dd>
        </div>
        <div>
          <dt>Current branch</dt>
          <dd>{node.git.branch ?? '—'}</dd>
        </div>
        <div>
          <dt>Drift</dt>
          <dd>{driftLabel(node.git.ahead, node.git.behind)}</dd>
        </div>
        <div>
          <dt>Working tree</dt>
          <dd>{dirtyLabel}</dd>
        </div>
        <div>
          <dt>Dependencies</dt>
          <dd>
            {node.dependencies_out} out · {node.dependencies_in} in
          </dd>
        </div>
        <div>
          <dt>Activity</dt>
          <dd>
            24h {node.activity.commits_24h} · 7d {node.activity.commits_7d} · 30d{' '}
            {node.activity.commits_30d}
          </dd>
        </div>
        {node.ownership ? (
          <div>
            <dt>Ownership</dt>
            <dd>{node.ownership}</dd>
          </div>
        ) : null}
        {node.pipeline ? (
          <div>
            <dt>CI/CD</dt>
            <dd>
              {node.pipeline.status}
              {node.pipeline.workflow ? ` · ${node.pipeline.workflow}` : ''}
              {node.pipeline.provider ? ` (${node.pipeline.provider})` : ''}
            </dd>
          </div>
        ) : null}
        {node.url ? (
          <div>
            <dt>Remote</dt>
            <dd>
              <a href={node.url} target="_blank" rel="noopener noreferrer">
                {node.url}
              </a>
            </dd>
          </div>
        ) : null}
        {node.tags.length > 0 ? (
          <div>
            <dt>Tags</dt>
            <dd>{node.tags.join(', ')}</dd>
          </div>
        ) : null}
        <div>
          <dt>Agent readiness</dt>
          <dd>
            {node.agent.has_agents_md ? 'AGENTS.md' : 'No AGENTS.md'}
            {node.agent.has_llms_txt ? ' · llms.txt' : ''}
            {' · '}
            score {(node.agent.documentation_score * 100).toFixed(0)}%
          </dd>
        </div>
      </dl>
    </aside>
  )
}
