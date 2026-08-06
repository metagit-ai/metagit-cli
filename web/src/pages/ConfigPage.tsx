import { useQuery } from '@tanstack/react-query'
import { useCallback, useMemo, useState } from 'react'
import type { ConfigOperation, SchemaFieldNode } from '../api/client'
import ConfigPreview from '../components/ConfigPreview'
import FieldEditor from '../components/FieldEditor'
import SchemaTree from '../components/SchemaTree'
import {
  DEFAULT_CONFIG_DISPLAY_OPTIONS,
  type ConfigDisplayOptions,
} from './configDisplayOptions'
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

const DISPLAY_OPTION_LABELS: {
  key: keyof ConfigDisplayOptions
  label: string
}[] = [
  { key: 'showYamlPreview', label: 'Show YAML preview' },
  { key: 'showUnassigned', label: 'Show unassigned fields' },
  { key: 'showListItemHeaders', label: 'Show list item headers' },
  { key: 'showElementNumbering', label: 'Show element numbering' },
  { key: 'showTypeLabels', label: 'Show type labels' },
]

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
  const [displayOptions, setDisplayOptions] = useState<ConfigDisplayOptions>(
    DEFAULT_CONFIG_DISPLAY_OPTIONS,
  )

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

  const handleDisplayOptionChange = useCallback(
    (key: keyof ConfigDisplayOptions, checked: boolean) => {
      setDisplayOptions((current) => ({ ...current, [key]: checked }))
    },
    [],
  )

  const {
    showYamlPreview,
    showUnassigned,
    showListItemHeaders,
    showElementNumbering,
    showTypeLabels,
  } = displayOptions

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>{title}</h2>
          {data?.config_path ? (
            <p className={styles.subtitle}>{data.config_path}</p>
          ) : null}
        </div>
        <fieldset className={styles.displayOptions}>
          <legend className={styles.displayLegend}>Display</legend>
          {DISPLAY_OPTION_LABELS.map(({ key, label }) => (
            <label key={key} className={styles.displayOption}>
              <input
                type="checkbox"
                checked={displayOptions[key]}
                onChange={(event) =>
                  handleDisplayOptionChange(key, event.target.checked)
                }
              />
              <span>{label}</span>
            </label>
          ))}
        </fieldset>
      </header>

      <div className={styles.layout}>
        <aside className={styles.treePanel}>
          <h3 className={styles.treeHeading}>Schema</h3>
          <SchemaTree
            target={target}
            selectedPath={selectedPath}
            pendingOps={pendingOps}
            displayOptions={{
              showUnassigned,
              showListItemHeaders,
              showElementNumbering,
              showTypeLabels,
            }}
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
      {showYamlPreview ? (
        <div className={styles.previewBelow}>
          <ConfigPreview target={target} pendingOps={pendingOps} />
        </div>
      ) : null}
    </section>
  )
}
