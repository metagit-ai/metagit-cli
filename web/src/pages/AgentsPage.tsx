import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import type { AgentCatalogEntry } from '../api/client'
import {
  agentCatalogQueryKey,
  agentPreviewQueryKey,
  fetchAgentCatalog,
  fetchAgentPreview,
  groupAgentsByCategory,
  initAgentOverlay,
} from './agentQueries'
import styles from './AgentsPage.module.css'

const VENDORS = [
  'claude_code',
  'cursor',
  'github_copilot',
  'hermes',
  'openclaw',
  'opencode',
  'windsurf',
  'codex',
] as const

type DetailTab = 'metadata' | 'preview'

export default function AgentsPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<DetailTab>('metadata')
  const [previewVendor, setPreviewVendor] = useState<string>('claude_code')
  const [overlayMessage, setOverlayMessage] = useState<string | null>(null)

  const overlayInit = useMutation({
    mutationFn: (templateId: string) =>
      initAgentOverlay(templateId, {
        mode: 'full',
        force: false,
      }),
    onSuccess: (response) => {
      if (!response.ok || !response.overlay) {
        setOverlayMessage(response.error?.message ?? 'Overlay init failed.')
        return
      }
      setOverlayMessage(
        `Overlay ready at ${response.overlay.overlay_path} (${response.overlay.scope}) — commit .metagit-agents/ to git.`,
      )
      void queryClient.invalidateQueries({ queryKey: agentCatalogQueryKey })
    },
    onError: (mutationError: Error) => {
      setOverlayMessage(mutationError.message)
    },
  })

  const { data, isLoading, isError, error } = useQuery({
    queryKey: agentCatalogQueryKey,
    queryFn: fetchAgentCatalog,
  })

  const templates = data?.catalog.templates ?? []
  const grouped = useMemo(() => groupAgentsByCategory(templates), [templates])
  const selected = templates.find((entry) => entry.id === selectedId) ?? null

  const {
    data: previewData,
    isLoading: previewLoading,
    isError: previewError,
  } = useQuery({
    queryKey: agentPreviewQueryKey(selectedId ?? '', previewVendor),
    queryFn: () => fetchAgentPreview(selectedId as string, previewVendor),
    enabled: detailTab === 'preview' && selectedId !== null,
  })

  const installCommand = selected
    ? `metagit agent create ${selected.id} --vendor ${previewVendor}`
    : ''

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Agent templates</h2>
          <p className={styles.subtitle}>
            Bundled archetypes for Metagit-managed workspaces. Team overlays live in
            `.metagit-agents/` (commit to git); personal overrides use `.metagit/.agent-templates/`.
          </p>
        </div>
      </header>

      {isLoading ? <p className={styles.status}>Loading catalog…</p> : null}
      {isError ? (
        <p className={styles.error}>
          Failed to load catalog: {error instanceof Error ? error.message : 'unknown error'}
        </p>
      ) : null}

      {!isLoading && !isError ? (
        <>
          {[...grouped.entries()].map(([category, entries]) => (
            <section key={category} className={styles.section}>
              <h3 className={styles.sectionTitle}>{category}</h3>
              <div className={styles.grid}>
                {entries.map((entry) => (
                  <AgentCard
                    key={entry.id}
                    entry={entry}
                    active={entry.id === selectedId}
                    onSelect={() => {
                      setSelectedId(entry.id)
                      setDetailTab('metadata')
                    }}
                  />
                ))}
              </div>
            </section>
          ))}

          {selected ? (
            <section className={styles.detail} aria-label="Template detail">
              <h3 className={styles.detailTitle}>{selected.label}</h3>
              <p>{selected.description}</p>
              <div className={styles.previewControls}>
                {selected.source === 'bundled' ? (
                  <button
                    type="button"
                    className={styles.copyButton}
                    disabled={overlayInit.isPending}
                    onClick={() => {
                      setOverlayMessage(null)
                      overlayInit.mutate(selected.id)
                    }}
                  >
                    {overlayInit.isPending ? 'Creating overlay…' : 'Create team overlay (.metagit-agents)'}
                  </button>
                ) : (
                  <p className={styles.subtitle}>
                    Overlay path:{' '}
                    <code>{selected.overlay_path ?? `.metagit/.agent-templates/${selected.id}`}</code>
                  </p>
                )}
                {overlayMessage ? <p className={styles.status}>{overlayMessage}</p> : null}
              </div>
              <div className={styles.tabs}>
                <button
                  type="button"
                  className={detailTab === 'metadata' ? styles.tabActive : styles.tab}
                  onClick={() => setDetailTab('metadata')}
                >
                  Metadata
                </button>
                <button
                  type="button"
                  className={detailTab === 'preview' ? styles.tabActive : styles.tab}
                  onClick={() => setDetailTab('preview')}
                >
                  Preview
                </button>
              </div>

              {detailTab === 'metadata' ? (
                <MetadataPanel entry={selected} />
              ) : (
                <div>
                  <div className={styles.previewControls}>
                    <label htmlFor="agent-vendor">Vendor</label>
                    <select
                      id="agent-vendor"
                      className={styles.select}
                      value={previewVendor}
                      onChange={(event) => setPreviewVendor(event.target.value)}
                    >
                      {VENDORS.map((vendor) => (
                        <option key={vendor} value={vendor}>
                          {vendor}
                        </option>
                      ))}
                    </select>
                  </div>
                  {previewLoading ? <p className={styles.status}>Rendering preview…</p> : null}
                  {previewError ? (
                    <p className={styles.error}>Failed to load preview.</p>
                  ) : null}
                  {previewData?.preview.content ? (
                    <pre className={styles.previewBox}>{previewData.preview.content}</pre>
                  ) : null}
                </div>
              )}

              <div>
                <p className={styles.subtitle}>Install command</p>
                <div className={styles.installBox}>
                  <input
                    className={styles.installInput}
                    readOnly
                    value={installCommand}
                    aria-label="Install command"
                  />
                  <button
                    type="button"
                    className={styles.copyButton}
                    onClick={() => navigator.clipboard.writeText(installCommand)}
                  >
                    Copy
                  </button>
                </div>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

function AgentCard({
  entry,
  active,
  onSelect,
}: {
  entry: AgentCatalogEntry
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      className={active ? `${styles.card} ${styles.cardActive}` : styles.card}
      onClick={onSelect}
    >
      <div className={styles.cardHeader}>
        <h4 className={styles.cardTitle}>{entry.label}</h4>
        <span className={styles.badge}>{entry.source}</span>
      </div>
      <p className={styles.cardDescription}>{entry.description}</p>
      <div className={styles.meta}>
        <span className={styles.metaTag}>{entry.archetype}</span>
        <span className={styles.metaTag}>{entry.scope}</span>
      </div>
    </button>
  )
}

function MetadataPanel({ entry }: { entry: AgentCatalogEntry }) {
  return (
    <div>
      <ul className={styles.list}>
        <li>
          <strong>ID:</strong> {entry.id}
        </li>
        <li>
          <strong>Status:</strong> {entry.status} ({entry.version})
        </li>
        <li>
          <strong>Prompt kinds:</strong> {entry.prompt_kinds.join(', ') || '—'}
        </li>
        <li>
          <strong>Skills:</strong> {entry.recommended_skills.join(', ') || '—'}
        </li>
        <li>
          <strong>Delegates to:</strong> {entry.delegates_to.join(', ') || '—'}
        </li>
        <li>
          <strong>Delegated by:</strong> {entry.delegated_by.join(', ') || '—'}
        </li>
        <li>
          <strong>Vendors:</strong> {entry.vendors.join(', ')}
        </li>
      </ul>
    </div>
  )
}
