import { useCallback, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  ApiError,
  getSyncJob,
  postSync,
  type SyncJobRequest,
} from '../api/client'
import { workspaceQueryKey } from '../pages/workspaceQueries'
import styles from './SyncDialog.module.css'

export interface SyncDialogProps {
  open: boolean
  title: string
  repos: string[]
  onClose: () => void
}

type Phase = 'idle' | 'running' | 'done' | 'error'

export default function SyncDialog({
  open,
  title,
  repos,
  onClose,
}: SyncDialogProps) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<SyncJobRequest['mode']>('fetch')
  const [dryRun, setDryRun] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null)

  const reset = useCallback(() => {
    setPhase('idle')
    setJobId(null)
    setMessage('')
    setSummary(null)
  }, [])

  useEffect(() => {
    if (!open) {
      reset()
      setMode('fetch')
      setDryRun(false)
    }
  }, [open, reset])

  useEffect(() => {
    if (!jobId || phase !== 'running') {
      return undefined
    }

    let cancelled = false

    const poll = async () => {
      try {
        const status = await getSyncJob(jobId)
        if (cancelled) {
          return
        }
        if (status.state === 'completed') {
          setPhase('done')
          setSummary(status.summary)
          setMessage('Sync completed.')
          void queryClient.invalidateQueries({ queryKey: workspaceQueryKey })
          return
        }
        if (status.state === 'failed') {
          setPhase('error')
          setMessage(status.error ?? 'Sync failed.')
          return
        }
        setMessage(`Sync ${status.state}…`)
      } catch (err) {
        if (cancelled) {
          return
        }
        const text =
          err instanceof ApiError ? err.message : 'Failed to fetch sync status.'
        setPhase('error')
        setMessage(text)
      }
    }

    void poll()
    const timer = window.setInterval(() => {
      void poll()
    }, 1000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [jobId, phase, queryClient])

  const handleSubmit = async () => {
    reset()
    setPhase('running')
    setMessage('Starting sync job…')
    try {
      const response = await postSync({
        repos: repos.length > 0 ? repos : undefined,
        mode,
        dry_run: dryRun,
      })
      const id =
        typeof response.job_id === 'string'
          ? response.job_id
          : typeof response.status === 'object' &&
              response.status !== null &&
              'job_id' in response.status &&
              typeof (response.status as { job_id: unknown }).job_id === 'string'
            ? (response.status as { job_id: string }).job_id
            : null
      if (!id) {
        setPhase('error')
        setMessage('Server did not return a job id.')
        return
      }
      setJobId(id)
      setMessage('Sync running…')
    } catch (err) {
      setPhase('error')
      setMessage(err instanceof ApiError ? err.message : 'Failed to start sync.')
    }
  }

  if (!open) {
    return null
  }

  const busy = phase === 'running'

  return (
    <div
      className={styles.overlay}
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget && !busy) {
          onClose()
        }
      }}
    >
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="sync-dialog-title"
      >
        <h3 id="sync-dialog-title" className={styles.title}>
          Sync repositories
        </h3>
        <p className={styles.subtitle}>{title}</p>

        {message ? (
          <p
            className={
              phase === 'error' ? `${styles.status} ${styles.statusError}` : styles.status
            }
          >
            {message}
          </p>
        ) : null}

        {summary ? (
          <ul className={styles.summary}>
            {Object.entries(summary).map(([key, value]) => (
              <li key={key}>
                {key}: {String(value)}
              </li>
            ))}
          </ul>
        ) : null}

        {phase === 'idle' || phase === 'error' ? (
          <>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="sync-mode">
                Mode
              </label>
              <select
                id="sync-mode"
                className={styles.select}
                value={mode}
                onChange={(event) =>
                  setMode(event.target.value as SyncJobRequest['mode'])
                }
                disabled={busy}
              >
                <option value="fetch">fetch</option>
                <option value="pull">pull</option>
                <option value="clone">clone</option>
              </select>
            </div>
            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(event) => setDryRun(event.target.checked)}
                disabled={busy}
              />
              Dry run
            </label>
          </>
        ) : null}

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.button}
            onClick={onClose}
            disabled={busy}
          >
            {phase === 'done' ? 'Close' : 'Cancel'}
          </button>
          {phase === 'idle' || phase === 'error' ? (
            <button
              type="button"
              className={`${styles.button} ${styles.buttonPrimary}`}
              onClick={() => void handleSubmit()}
              disabled={busy || repos.length === 0}
            >
              Start sync
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
