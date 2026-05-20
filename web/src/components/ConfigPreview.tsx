import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import type { ConfigOperation, ConfigPreviewStyle } from '../api/client'
import { fetchConfigPreview, type ConfigTarget } from '../pages/configQueries'
import styles from './ConfigPreview.module.css'

interface ConfigPreviewProps {
  target: ConfigTarget
  pendingOps: ConfigOperation[]
}

export default function ConfigPreview({ target, pendingOps }: ConfigPreviewProps) {
  const [style, setStyle] = useState<ConfigPreviewStyle>('normalized')

  const operations = useMemo(
    () => (style === 'disk' ? [] : pendingOps),
    [pendingOps, style],
  )

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['config-preview', target, style, operations],
    queryFn: () => fetchConfigPreview(target, style, operations),
  })

  return (
    <section className={styles.previewPanel} aria-label="YAML preview">
      <header className={styles.header}>
        <h3 className={styles.title}>YAML preview</h3>
        <div className={styles.controls}>
          <select
            className={styles.select}
            value={style}
            aria-label="Preview style"
            onChange={(event) =>
              setStyle(event.target.value as ConfigPreviewStyle)
            }
          >
            <option value="normalized">Normalized</option>
            <option value="minimal">Minimal (non-default)</option>
            <option value="disk">On disk</option>
          </select>
          {data?.draft ? <span className={styles.badge}>Draft</span> : null}
          {data && !data.ok ? (
            <span className={`${styles.badge} ${styles.badgeInvalid}`}>
              Invalid
            </span>
          ) : null}
        </div>
      </header>

      {isLoading ? <p className={styles.state}>Rendering preview…</p> : null}
      {isError ? (
        <p className={styles.state}>
          {error instanceof Error ? error.message : 'Preview failed'}
        </p>
      ) : null}

      {data?.validation_errors && data.validation_errors.length > 0 ? (
        <ul className={styles.errors}>
          {data.validation_errors.map((entry) => (
            <li key={`${entry.path}:${entry.message}`}>
              {entry.path ? `${entry.path}: ` : ''}
              {entry.message}
            </li>
          ))}
        </ul>
      ) : null}

      {data?.yaml ? (
        <div className={styles.codeWrap}>
          <pre className={styles.code}>{data.yaml}</pre>
        </div>
      ) : null}
    </section>
  )
}
