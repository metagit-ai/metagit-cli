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
  pendingOps: ConfigOperation[]
  onSelect: (node: SchemaFieldNode) => void
  onOperationApplied?: (op: ConfigOperation) => void
}

function isOptionalToggleable(node: SchemaFieldNode): boolean {
  return !node.required && node.path !== ''
}

function displayType(node: SchemaFieldNode): string {
  return node.type_label ?? node.type
}

function isListItemNode(node: SchemaFieldNode): boolean {
  return /^\[\d+\]$/.test(node.key)
}

function mergePendingOp(
  pending: ConfigOperation[],
  op: ConfigOperation,
): ConfigOperation[] {
  const next = [...pending]
  const index = next.findIndex((item) => item.path === op.path)
  if (index >= 0) {
    next[index] = op
  } else {
    next.push(op)
  }
  return next
}

export default function SchemaTree({
  target,
  selectedPath,
  pendingOps,
  onSelect,
  onOperationApplied,
}: SchemaTreeProps) {
  const queryClient = useQueryClient()
  const queryKey = configTreeQueryKey(target)

  const { data, isLoading, isError, error } = useQuery({
    queryKey,
    queryFn: () => fetchConfigTree(target),
  })

  const mutation = useMutation({
    mutationFn: (op: ConfigOperation) =>
      patchConfigTree(target, mergePendingOp(pendingOps, op), false),
    onSuccess: (response, op) => {
      queryClient.setQueryData(queryKey, response)
      onOperationApplied?.(op)
    },
  })

  const handleToggle = useCallback(
    (node: SchemaFieldNode, checked: boolean) => {
      mutation.mutate({
        op: checked ? 'enable' : 'disable',
        path: node.path,
      })
    },
    [mutation],
  )

  const handleAppend = useCallback(
    (node: SchemaFieldNode) => {
      mutation.mutate({ op: 'append', path: node.path })
    },
    [mutation],
  )

  const handleRemove = useCallback(
    (node: SchemaFieldNode) => {
      mutation.mutate({ op: 'remove', path: node.path })
    },
    [mutation],
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
        onAppend={handleAppend}
        onRemove={handleRemove}
        mutationPending={mutation.isPending}
      />
    </ul>
  )
}

interface TreeNodesProps {
  nodes: SchemaFieldNode[]
  selectedPath: string | null
  onSelect: (node: SchemaFieldNode) => void
  onToggle: (node: SchemaFieldNode, checked: boolean) => void
  onAppend: (node: SchemaFieldNode) => void
  onRemove: (node: SchemaFieldNode) => void
  mutationPending: boolean
}

function TreeNodes({
  nodes,
  selectedPath,
  onSelect,
  onToggle,
  onAppend,
  onRemove,
  mutationPending,
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
          onAppend={onAppend}
          onRemove={onRemove}
          mutationPending={mutationPending}
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
  onAppend: (node: SchemaFieldNode) => void
  onRemove: (node: SchemaFieldNode) => void
  mutationPending: boolean
}

function TreeNode({
  node,
  selectedPath,
  onSelect,
  onToggle,
  onAppend,
  onRemove,
  mutationPending,
}: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = (node.children?.length ?? 0) > 0
  const showToggle = isOptionalToggleable(node)
  const isSelected = selectedPath === node.path
  const isArray = node.type === 'array'
  const isListItem = isListItemNode(node)
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
            disabled={mutationPending}
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
          <span className={styles.type}>{displayType(node)}</span>
          {node.required ? <span className={styles.required}>required</span> : null}
          {isArray && node.enabled ? (
            <span className={styles.count}>
              {node.item_count ?? 0} item{(node.item_count ?? 0) === 1 ? '' : 's'}
            </span>
          ) : null}
        </span>
        {node.can_append ? (
          <button
            type="button"
            className={styles.listBtn}
            title="Add item"
            aria-label={`Add ${displayType(node)} item`}
            disabled={mutationPending}
            onClick={(event) => {
              event.stopPropagation()
              onAppend(node)
            }}
          >
            +
          </button>
        ) : null}
        {isListItem ? (
          <button
            type="button"
            className={`${styles.listBtn} ${styles.listBtnDanger}`}
            title="Remove item"
            aria-label={`Remove ${node.path}`}
            disabled={mutationPending}
            onClick={(event) => {
              event.stopPropagation()
              onRemove(node)
            }}
          >
            ×
          </button>
        ) : null}
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
            onAppend={onAppend}
            onRemove={onRemove}
            mutationPending={mutationPending}
          />
        </ul>
      ) : null}
    </li>
  )
}
