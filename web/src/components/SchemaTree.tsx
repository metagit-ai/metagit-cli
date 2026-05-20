import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import type { ConfigOperation, SchemaFieldNode } from '../api/client'
import {
  configTreeQueryKey,
  fetchConfigTree,
  patchConfigTree,
  type ConfigTarget,
} from '../pages/configQueries'
import styles from './SchemaTree.module.css'

interface SchemaTreeProps {
  target: ConfigTarget
  selectedPath: string | null
  onSelect: (node: SchemaFieldNode) => void
  onOperationApplied?: (op: ConfigOperation) => void
}

function isOptionalToggleable(node: SchemaFieldNode): boolean {
  return !node.required && node.path !== ''
}

export default function SchemaTree({
  target,
  selectedPath,
  onSelect,
  onOperationApplied,
}: SchemaTreeProps) {
  const queryClient = useQueryClient()
  const queryKey = configTreeQueryKey(target)

  const { data, isLoading, isError, error } = useQuery({
    queryKey,
    queryFn: () => fetchConfigTree(target),
  })

  const toggleMutation = useMutation({
    mutationFn: (op: ConfigOperation) => patchConfigTree(target, [op], false),
    onSuccess: (response, op) => {
      queryClient.setQueryData(queryKey, response)
      onOperationApplied?.(op)
    },
  })

  const handleToggle = useCallback(
    (node: SchemaFieldNode, checked: boolean) => {
      toggleMutation.mutate({
        op: checked ? 'enable' : 'disable',
        path: node.path,
      })
    },
    [toggleMutation],
  )

  if (isLoading) {
    return <p className={styles.state}>Loading schema…</p>
  }

  if (isError) {
    return (
      <p className={`${styles.state} ${styles.error}`}>
        {error instanceof Error ? error.message : 'Failed to load schema'}
      </p>
    )
  }

  if (!data?.tree) {
    return <p className={styles.state}>No schema data</p>
  }

  return (
    <ul className={styles.tree} role="tree" aria-label="Configuration fields">
      <TreeNodes
        nodes={data.tree.children ?? []}
        selectedPath={selectedPath}
        onSelect={onSelect}
        onToggle={handleToggle}
        togglePending={toggleMutation.isPending}
      />
    </ul>
  )
}

interface TreeNodesProps {
  nodes: SchemaFieldNode[]
  selectedPath: string | null
  onSelect: (node: SchemaFieldNode) => void
  onToggle: (node: SchemaFieldNode, checked: boolean) => void
  togglePending: boolean
}

function TreeNodes({
  nodes,
  selectedPath,
  onSelect,
  onToggle,
  togglePending,
}: TreeNodesProps) {
  return (
    <>
      {nodes.map((node) => (
        <TreeNode
          key={node.path || node.key}
          node={node}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onToggle={onToggle}
          togglePending={togglePending}
        />
      ))}
    </>
  )
}

interface TreeNodeProps {
  node: SchemaFieldNode
  selectedPath: string | null
  onSelect: (node: SchemaFieldNode) => void
  onToggle: (node: SchemaFieldNode, checked: boolean) => void
  togglePending: boolean
}

function TreeNode({
  node,
  selectedPath,
  onSelect,
  onToggle,
  togglePending,
}: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = (node.children?.length ?? 0) > 0
  const showToggle = isOptionalToggleable(node)
  const isSelected = selectedPath === node.path
  const rowClass = [
    styles.row,
    isSelected ? styles.rowSelected : '',
    node.enabled === false ? styles.rowDisabled : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <li role="treeitem" aria-expanded={hasChildren ? expanded : undefined}>
      <div
        className={rowClass}
        onClick={() => onSelect(node)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onSelect(node)
          }
        }}
        role="button"
        tabIndex={0}
      >
        {showToggle ? (
          <input
            type="checkbox"
            className={styles.checkbox}
            checked={node.enabled ?? false}
            disabled={togglePending}
            aria-label={`${node.enabled ? 'Disable' : 'Enable'} ${node.key}`}
            onClick={(event) => event.stopPropagation()}
            onChange={(event) => {
              event.stopPropagation()
              onToggle(node, event.target.checked)
            }}
          />
        ) : (
          <span className={styles.checkboxPlaceholder} aria-hidden />
        )}
        <span className={styles.label}>
          <span className={styles.key}>{node.key}</span>
          <span className={styles.type}>{node.type}</span>
          {node.required ? <span className={styles.required}>required</span> : null}
        </span>
        {hasChildren ? (
          <button
            type="button"
            className={styles.expandBtn}
            aria-label={expanded ? 'Collapse' : 'Expand'}
            onClick={(event) => {
              event.stopPropagation()
              setExpanded((value) => !value)
            }}
          >
            {expanded ? '−' : '+'}
          </button>
        ) : null}
      </div>
      {hasChildren && expanded ? (
        <ul className={`${styles.tree} ${styles.nested}`}>
          <TreeNodes
            nodes={node.children ?? []}
            selectedPath={selectedPath}
            onSelect={onSelect}
            onToggle={onToggle}
            togglePending={togglePending}
          />
        </ul>
      ) : null}
    </li>
  )
}
