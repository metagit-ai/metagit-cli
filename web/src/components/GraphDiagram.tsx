import { useMemo } from 'react'
import type { GraphViewEdge, GraphViewNode } from '../api/client'
import styles from './GraphDiagram.module.css'

const COLUMN_WIDTH = 160
const PROJECT_HEIGHT = 44
const REPO_HEIGHT = 36
const REPO_GAP = 10
const PADDING = 32

export interface GraphDiagramProps {
  nodes: GraphViewNode[]
  edges: GraphViewEdge[]
  manualEdgeCount: number
  inferredEdgeCount: number
  structureEdgeCount: number
}

interface LayoutNode {
  node: GraphViewNode
  x: number
  y: number
  width: number
  height: number
}

function edgeStroke(source: GraphViewEdge['source'], type: string): string {
  if (source === 'manual') {
    return 'var(--graph-edge-manual)'
  }
  if (source === 'structure' || type === 'contains') {
    return 'var(--graph-edge-structure)'
  }
  return 'var(--graph-edge-inferred)'
}

function computeLayout(nodes: GraphViewNode[]): Map<string, LayoutNode> {
  const byProject = new Map<string, { project?: GraphViewNode; repos: GraphViewNode[] }>()
  for (const node of nodes) {
    const projectName = node.project_name ?? '_'
    const bucket = byProject.get(projectName) ?? { repos: [] }
    if (node.kind === 'project') {
      bucket.project = node
    } else {
      bucket.repos.push(node)
    }
    byProject.set(projectName, bucket)
  }

  const positions = new Map<string, LayoutNode>()
  let column = 0
  for (const [, bucket] of [...byProject.entries()].sort(([a], [b]) =>
    a.localeCompare(b),
  )) {
    const x = PADDING + column * COLUMN_WIDTH
    let y = PADDING
    if (bucket.project) {
      positions.set(bucket.project.id, {
        node: bucket.project,
        x,
        y,
        width: COLUMN_WIDTH - 16,
        height: PROJECT_HEIGHT,
      })
      y += PROJECT_HEIGHT + REPO_GAP
    }
    const repos = [...bucket.repos].sort((a, b) => a.label.localeCompare(b.label))
    for (const repo of repos) {
      positions.set(repo.id, {
        node: repo,
        x,
        y,
        width: COLUMN_WIDTH - 16,
        height: REPO_HEIGHT,
      })
      y += REPO_HEIGHT + REPO_GAP
    }
    column += 1
  }
  return positions
}

function center(layout: LayoutNode): { cx: number; cy: number } {
  return {
    cx: layout.x + layout.width / 2,
    cy: layout.y + layout.height / 2,
  }
}

export default function GraphDiagram({
  nodes,
  edges,
  manualEdgeCount,
  inferredEdgeCount,
  structureEdgeCount,
}: GraphDiagramProps) {
  const layout = useMemo(() => computeLayout(nodes), [nodes])

  const { width, height } = useMemo(() => {
    let maxX = 400
    let maxY = 200
    for (const item of layout.values()) {
      maxX = Math.max(maxX, item.x + item.width + PADDING)
      maxY = Math.max(maxY, item.y + item.height + PADDING)
    }
    return { width: maxX, height: maxY }
  }, [layout])

  if (nodes.length === 0) {
    return (
      <p className={styles.empty}>
        No graph nodes yet. Add workspace projects/repos or manual relationships in
        `.metagit.yml` under `graph`.
      </p>
    )
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.legend} aria-label="Edge legend">
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: 'var(--graph-edge-manual)' }}
          />
          Manual ({manualEdgeCount})
        </span>
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: 'var(--graph-edge-inferred)' }}
          />
          Inferred ({inferredEdgeCount})
        </span>
        <span className={styles.legendItem}>
          <span
            className={styles.legendSwatch}
            style={{ background: 'var(--graph-edge-structure)' }}
          />
          Structure ({structureEdgeCount})
        </span>
      </div>
      <div className={styles.canvasScroll}>
        <svg
          className={styles.canvas}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Workspace relationship diagram"
        >
          <defs>
            <marker
              id="graph-arrow"
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="4"
              orient="auto"
            >
              <path d="M0,0 L8,4 L0,8 z" fill="var(--color-text-muted)" />
            </marker>
          </defs>
          {edges.map((edge) => {
            const from = layout.get(edge.from_id)
            const to = layout.get(edge.to_id)
            if (!from || !to) {
              return null
            }
            const start = center(from)
            const end = center(to)
            const stroke = edgeStroke(edge.source, edge.type)
            const dash =
              edge.source === 'structure' || edge.type === 'contains'
                ? '6 4'
                : undefined
            return (
              <g key={edge.id}>
                <line
                  x1={start.cx}
                  y1={start.cy}
                  x2={end.cx}
                  y2={end.cy}
                  stroke={stroke}
                  strokeWidth={edge.source === 'manual' ? 2.5 : 1.5}
                  strokeDasharray={dash}
                  markerEnd="url(#graph-arrow)"
                  opacity={0.85}
                />
                {edge.label && edge.source === 'manual' ? (
                  <text
                    x={(start.cx + end.cx) / 2}
                    y={(start.cy + end.cy) / 2 - 6}
                    className={styles.edgeLabel}
                    textAnchor="middle"
                  >
                    {edge.label}
                  </text>
                ) : null}
              </g>
            )
          })}
          {[...layout.values()].map((item) => (
            <g key={item.node.id}>
              <rect
                x={item.x}
                y={item.y}
                width={item.width}
                height={item.height}
                rx={8}
                className={
                  item.node.kind === 'project'
                    ? styles.nodeProject
                    : styles.nodeRepo
                }
              />
              <text
                x={item.x + item.width / 2}
                y={item.y + item.height / 2 + 4}
                className={styles.nodeLabel}
                textAnchor="middle"
              >
                {item.node.label}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  )
}
