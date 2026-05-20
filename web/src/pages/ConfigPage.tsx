import { useQuery } from '@tanstack/react-query'
import { useCallback, useMemo, useState } from 'react'
import type { ConfigOperation, SchemaFieldNode } from '../api/client'
import FieldEditor from '../components/FieldEditor'
import SchemaTree from '../components/SchemaTree'
import {
  configTreeQueryKey,
  fetchConfigTree,
  type ConfigTarget,
} from './configQueries'
import styles from './ConfigPage.module.css'

interface ConfigPageProps {
  target: ConfigTarget
  title: string
}

function findNodeByPath(
  root: SchemaFieldNode | undefined,
  path: string | null,
): SchemaFieldNode | null {
  if (!root || path === null) {
    return null
  }
  if (path === '' || path === root.path) {
    return root
  }
  for (const child of root.children ?? []) {
    const found = findNodeByPath(child, path)
    if (found) {
      return found
    }
  }
  return null
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

export default function ConfigPage({ target, title }: ConfigPageProps) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [pendingOps, setPendingOps] = useState<ConfigOperation[]>([])

  const { data } = useQuery({
    queryKey: configTreeQueryKey(target),
    queryFn: () => fetchConfigTree(target),
  })

  const selectedNode = useMemo(
    () => findNodeByPath(data?.tree, selectedPath),
    [data?.tree, selectedPath],
  )

  const handleSelect = useCallback((node: SchemaFieldNode) => {
    setSelectedPath(node.path)
  }, [])

  const handleOperationApplied = useCallback((op: ConfigOperation) => {
    setPendingOps((current) => mergePendingOp(current, op))
  }, [])

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>{title}</h2>
          {data?.config_path ? (
            <p className={styles.subtitle}>{data.config_path}</p>
          ) : null}
        </div>
      </header>

      <div className={styles.layout}>
        <aside className={styles.treePanel}>
          <h3 className={styles.treeHeading}>Schema</h3>
          <SchemaTree
            target={target}
            selectedPath={selectedPath}
            onSelect={handleSelect}
            onOperationApplied={handleOperationApplied}
          />
        </aside>
        <FieldEditor
          target={target}
          node={selectedNode}
          pendingOps={pendingOps}
          onPendingChange={setPendingOps}
        />
      </div>
    </section>
  )
}
