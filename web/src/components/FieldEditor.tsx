import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import type { ConfigOperation, SchemaFieldNode } from '../api/client'
import {
  configTreeQueryKey,
  fetchConfigTree,
  patchConfigTree,
  type ConfigTarget,
} from '../pages/configQueries'
import styles from './FieldEditor.module.css'

interface FieldEditorProps {
  target: ConfigTarget
  node: SchemaFieldNode | null
  pendingOps: ConfigOperation[]
  onPendingChange: (ops: ConfigOperation[]) => void
}

function scalarTypes(): Set<string> {
  return new Set(['string', 'integer', 'number', 'boolean', 'enum'])
}

function formatValidationErrors(
  errors: Array<Record<string, string>>,
): Array<{ path: string; message: string }> {
  return errors.map((entry) => ({
    path: entry.path ?? '',
    message: entry.message ?? 'Validation error',
  }))
}

function isMaskedSensitiveValue(node: SchemaFieldNode): boolean {
  return (
    node.sensitive === true &&
    typeof node.value === 'string' &&
    node.value.startsWith('***')
  )
}

function shouldSkipSensitiveSet(node: SchemaFieldNode, draft: string): boolean {
  if (!node.sensitive) {
    return false
  }
  return draft.trim() === ''
}

function normalizeDraftValue(node: SchemaFieldNode): unknown {
  if (isMaskedSensitiveValue(node)) {
    return ''
  }
  if (node.value !== undefined && node.value !== null) {
    return node.value
  }
  if (node.default_value !== undefined && node.default_value !== null) {
    return node.default_value
  }
  if (node.type === 'boolean') {
    return false
  }
  if (node.type === 'integer' || node.type === 'number') {
    return 0
  }
  return ''
}

function parseDraftValue(node: SchemaFieldNode, raw: string): unknown {
  if (node.type === 'boolean') {
    return raw === 'true'
  }
  if (node.type === 'integer') {
    return Number.parseInt(raw, 10)
  }
  if (node.type === 'number') {
    return Number.parseFloat(raw)
  }
  return raw
}

export default function FieldEditor({
  target,
  node,
  pendingOps,
  onPendingChange,
}: FieldEditorProps) {
  const queryClient = useQueryClient()
  const queryKey = configTreeQueryKey(target)
  const { data } = useQuery({
    queryKey,
    queryFn: () => fetchConfigTree(target),
  })

  const [draft, setDraft] = useState<string>('')
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!node) {
      setDraft('')
      setDirty(false)
      return
    }
    const value = normalizeDraftValue(node)
    setDraft(node.type === 'boolean' ? String(value) : String(value ?? ''))
    setDirty(false)
  }, [node])

  const validationErrors = useMemo(
    () => formatValidationErrors(data?.validation_errors ?? []),
    [data?.validation_errors],
  )

  const applyMutation = useMutation({
    mutationFn: (payload: { ops: ConfigOperation[]; save: boolean }) =>
      patchConfigTree(target, payload.ops, payload.save),
    onSuccess: (response, variables) => {
      queryClient.setQueryData(queryKey, response)
      if (variables.save) {
        onPendingChange([])
      } else if (variables.ops.length > 0) {
        const merged = [...pendingOps]
        for (const op of variables.ops) {
          const index = merged.findIndex((item) => item.path === op.path)
          if (index >= 0) {
            merged[index] = op
          } else {
            merged.push(op)
          }
        }
        onPendingChange(merged)
      }
      setDirty(false)
    },
  })

  const enumOptions = useMemo(() => {
    if (!node) {
      return []
    }
    const options = new Set<string>(node.enum_options ?? [])
    if (node.value != null) {
      options.add(String(node.value))
    }
    if (node.default_value != null) {
      options.add(String(node.default_value))
    }
    return [...options]
  }, [node])

  if (!node) {
    return (
      <div className={styles.panel}>
        <p className={styles.empty}>Select a field in the tree to edit.</p>
      </div>
    )
  }

  const isScalar = scalarTypes().has(node.type)
  const isComplex = node.type === 'object' || node.type === 'array'
  const isArray = node.type === 'array'
  const typeLabel = node.type_label ?? node.type
  const editable = node.editable !== false && node.enabled !== false && !isComplex && !isArray

  const queueSetOp = (save: boolean) => {
    if (!node.path || !isScalar) {
      return
    }
    if (shouldSkipSensitiveSet(node, draft)) {
      if (save && pendingOps.length > 0) {
        applyMutation.mutate({ ops: pendingOps, save: true })
      }
      return
    }
    const value = parseDraftValue(node, draft)
    const op: ConfigOperation = { op: 'set', path: node.path, value }
    const nextPending = [
      ...pendingOps.filter((item) => item.path !== node.path),
      op,
    ]
    if (save) {
      applyMutation.mutate({ ops: nextPending, save: true })
      return
    }
    onPendingChange(nextPending)
    applyMutation.mutate({ ops: [op], save: false })
  }

  const saveAllPending = () => {
    if (pendingOps.length === 0 && !dirty) {
      return
    }
    const ops = [...pendingOps]
    if (dirty && node?.path && isScalar && !shouldSkipSensitiveSet(node, draft)) {
      const value = parseDraftValue(node, draft)
      const setOp: ConfigOperation = { op: 'set', path: node.path, value }
      const index = ops.findIndex((item) => item.path === node.path)
      if (index >= 0) {
        ops[index] = setOp
      } else {
        ops.push(setOp)
      }
    }
    applyMutation.mutate({ ops, save: true })
  }

  const revert = () => {
    onPendingChange([])
    setDirty(false)
    void queryClient.invalidateQueries({ queryKey })
  }

  return (
    <div className={styles.panel}>
      <header className={styles.header}>
        <h3 className={styles.title}>{node.key}</h3>
        <p className={styles.path}>{node.path || '(root)'}</p>
        <div className={styles.meta}>
          <span className={styles.badge}>{typeLabel}</span>
          {node.required ? <span className={styles.badge}>required</span> : null}
          {node.sensitive ? <span className={styles.badge}>sensitive</span> : null}
        </div>
      </header>

      {node.description ? (
        <p className={styles.description}>{node.description}</p>
      ) : null}

      {isArray && node.enabled ? (
        <p className={styles.hint}>
          List of {typeLabel}. Use <strong>+</strong> in the schema tree to add items
          and <strong>×</strong> on each row to remove. Currently{' '}
          {node.item_count ?? 0} item{(node.item_count ?? 0) === 1 ? '' : 's'}.
        </p>
      ) : null}

      {node.type === 'object' ? (
        <p className={styles.hint}>Edit via tree — expand nested fields in the schema tree.</p>
      ) : null}

      {editable && node.type === 'boolean' ? (
        <div className={styles.field}>
          <label className={styles.label} htmlFor="field-boolean">
            Value
          </label>
          <select
            id="field-boolean"
            className={styles.select}
            value={draft}
            disabled={applyMutation.isPending}
            onChange={(event) => {
              setDraft(event.target.value)
              setDirty(true)
            }}
          >
            <option value="true">true</option>
            <option value="false">false</option>
          </select>
        </div>
      ) : null}

      {editable && node.type === 'enum' ? (
        <div className={styles.field}>
          <label className={styles.label} htmlFor="field-enum">
            Value
          </label>
          <select
            id="field-enum"
            className={styles.select}
            value={draft}
            disabled={applyMutation.isPending}
            onChange={(event) => {
              setDraft(event.target.value)
              setDirty(true)
            }}
          >
            {enumOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {editable &&
      (node.type === 'string' ||
        node.type === 'integer' ||
        node.type === 'number') ? (
        <div className={styles.field}>
          <label className={styles.label} htmlFor="field-scalar">
            Value
          </label>
          <input
            id="field-scalar"
            className={styles.input}
            type={node.type === 'string' || node.sensitive ? 'text' : 'number'}
            value={draft}
            placeholder={node.sensitive ? '••••••••' : undefined}
            disabled={applyMutation.isPending}
            onChange={(event) => {
              setDraft(event.target.value)
              setDirty(true)
            }}
          />
        </div>
      ) : null}

      {!editable && !isComplex && !isArray ? (
        <p className={styles.hint}>
          This field is not editable (disabled or read-only).
        </p>
      ) : null}

      {validationErrors.length > 0 ? (
        <ul className={styles.errors} aria-live="polite">
          {validationErrors.map((entry) => (
            <li key={`${entry.path}:${entry.message}`}>
              <strong>{entry.path || 'config'}:</strong> {entry.message}
            </li>
          ))}
        </ul>
      ) : null}

      {isScalar && editable ? (
        <div className={styles.actions}>
          <button
            type="button"
            className={`${styles.button} ${styles.buttonPrimary}`}
            disabled={applyMutation.isPending || (!dirty && pendingOps.length === 0)}
            onClick={() => queueSetOp(false)}
          >
            Apply
          </button>
          <button
            type="button"
            className={styles.button}
            disabled={applyMutation.isPending || (!dirty && pendingOps.length === 0)}
            onClick={() => queueSetOp(true)}
          >
            Save field
          </button>
          <button
            type="button"
            className={`${styles.button} ${styles.buttonPrimary}`}
            disabled={applyMutation.isPending}
            onClick={saveAllPending}
          >
            Save to disk
          </button>
          <button
            type="button"
            className={styles.button}
            disabled={applyMutation.isPending}
            onClick={revert}
          >
            Revert
          </button>
        </div>
      ) : null}

      {pendingOps.length > 0 ? (
        <p className={styles.status}>
          {pendingOps.length} pending change{pendingOps.length === 1 ? '' : 's'} not
          saved to disk
        </p>
      ) : null}

      {data?.saved ? (
        <p className={styles.status}>Last write saved to {data.config_path}</p>
      ) : null}
    </div>
  )
}
