import { describe, expect, it } from 'vitest'
import type { RepositoryTerrainNode } from '../../api/client'
import { resolveTerrainLayout } from './terrainViewOptions'

function node(
  project: string,
  repo: string,
  x: number,
  y: number,
): RepositoryTerrainNode {
  return {
    id: `repo:${project}/${repo}`,
    project_name: project,
    repo_name: repo,
    label: repo,
    repo_path: `/tmp/${repo}`,
    exists: true,
    is_git_repo: true,
    local_status: 'synced',
    tags: [],
    coordinates: { x, y },
    git: {
      branch_kind: 'default',
      ahead: 0,
      behind: 0,
      dirty: false,
      uncommitted_count: 0,
      untracked_count: 0,
      modified_count: 0,
      merge_conflicts: false,
      detached_head: false,
    },
    activity: {
      commits_24h: 0,
      commits_7d: 0,
      commits_30d: 0,
      level: 'abandoned',
      pulse_intensity: 0,
    },
    agent: {
      has_agents_md: false,
      has_llms_txt: false,
      has_agent_instructions: false,
      documentation_score: 0,
    },
    visual: {
      elevation: 0,
      sync_color: 'neutral_blue',
      surface_fracture: 0,
      fissure_glow: 0,
      crack_severity: 0,
      darken_factor: 0,
      fade_factor: 0,
    },
    dependencies_out: 0,
    dependencies_in: 0,
  }
}

describe('resolveTerrainLayout', () => {
  it('preserves hierarchy coordinates', () => {
    const nodes = [node('alpha', 'api', 3, 7)]
    const slots = resolveTerrainLayout(nodes, { mode: 'hierarchy', gridColumns: 'auto' })
    expect(slots[0]?.x).toBe(3)
    expect(slots[0]?.z).toBe(7)
  })

  it('lays out grid columns', () => {
    const nodes = [
      node('alpha', 'a', 0, 0),
      node('alpha', 'b', 0, 0),
      node('alpha', 'c', 0, 0),
    ]
    const slots = resolveTerrainLayout(nodes, { mode: 'grid', gridColumns: 4 })
    expect(slots[0]?.x).toBe(0)
    expect(slots[1]?.x).toBeGreaterThan(0)
    expect(slots[1]?.z).toBe(0)
  })

  it('wraps nodes on a sphere', () => {
    const nodes = [node('alpha', 'a', 0, 0), node('alpha', 'b', 0, 0)]
    const slots = resolveTerrainLayout(nodes, { mode: 'sphere', gridColumns: 'auto' })
    const radius = Math.hypot(slots[0]?.x ?? 0, slots[0]?.y ?? 0, slots[0]?.z ?? 0)
    expect(radius).toBeGreaterThan(10)
    expect(Math.abs(slots[0]?.normalY ?? 0)).toBeLessThanOrEqual(1)
  })
})
