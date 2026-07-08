import React from 'react'
import type { HistoryItem } from '../types'
import { getHistoryThumbnailUrl } from '../api/client'

interface Props {
  items: HistoryItem[]
  onSelect: (jobId: string) => void
  onDelete: (jobId: string) => void
  selectedJobId: string | null
}

function formatDate(iso: string): string {
  const d = new Date(iso + 'Z')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const mins = String(d.getMinutes()).padStart(2, '0')
  return `${month}/${day} ${hours}:${mins}`
}

function formatDuration(sec: number | null): string {
  if (sec == null) return ''
  return `${sec.toFixed(1)}s`
}

export default function ProcessingHistory({ items, onSelect, onDelete, selectedJobId }: Props) {
  if (items.length === 0) return null

  return (
    <div className="animate-in animate-in-delay-3">
      <h3 style={styles.sectionTitle}>
        <span style={styles.sectionNum}>04</span>
        HISTORY
      </h3>

      <div style={styles.card}>
        <div style={styles.list}>
          {items.map((item) => (
            <div
              key={item.job_id}
              style={{
                ...styles.item,
                ...(selectedJobId === item.job_id ? styles.itemSelected : {}),
              }}
              onClick={() => onSelect(item.job_id)}
            >
              <div style={styles.thumbWrap}>
                {item.thumbnail_path ? (
                  <img
                    src={getHistoryThumbnailUrl(item.job_id)}
                    alt=""
                    style={styles.thumb}
                  />
                ) : (
                  <div style={styles.thumbPlaceholder}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
                      <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}
              </div>

              <div style={styles.itemInfo}>
                <div style={styles.itemName} title={item.filename}>
                  {item.filename.replace(/^[0-9a-f]{8}_/, '')}
                </div>
                <div style={styles.itemMeta}>
                  <span>{formatDate(item.created_at)}</span>
                  {item.video_duration != null && (
                    <span>{formatDuration(item.video_duration)}</span>
                  )}
                </div>
              </div>

              <div style={styles.itemActions}>
                <span style={{
                  ...styles.formatBadge,
                  background: item.output_format === 'bvh' ? 'rgba(59,59,107,0.1)' : 'rgba(204,175,96,0.15)',
                  color: item.output_format === 'bvh' ? 'var(--main)' : 'var(--accent)',
                }}>
                  {item.output_format.toUpperCase()}
                </span>
                <button
                  style={styles.deleteBtn}
                  onClick={(e) => { e.stopPropagation(); onDelete(item.job_id) }}
                  title="削除"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  sectionTitle: {
    fontSize: '11px', fontWeight: 600, color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const, letterSpacing: '1.5px',
    marginBottom: 'var(--space-sm)', fontFamily: 'var(--font-mono)',
    display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
  },
  sectionNum: { color: 'var(--main)', fontSize: '10px', fontWeight: 600 },
  card: {
    background: 'var(--bg-root)', borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-sm)', border: '1px solid var(--border-subtle)',
  },
  list: {
    maxHeight: '320px',
    overflowY: 'auto' as const,
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '2px',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-md)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    transition: 'background 0.15s',
    background: 'transparent',
  },
  itemSelected: {
    background: 'rgba(59, 59, 107, 0.08)',
  },
  thumbWrap: {
    width: '60px',
    height: '40px',
    borderRadius: '4px',
    overflow: 'hidden',
    flexShrink: 0,
    background: 'var(--bg-surface)',
    border: '1px solid var(--border-subtle)',
  },
  thumb: {
    width: '100%',
    height: '100%',
    objectFit: 'cover' as const,
  },
  thumbPlaceholder: {
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--bg-surface)',
  },
  itemInfo: {
    flex: 1,
    minWidth: 0,
  },
  itemName: {
    fontSize: '12px',
    fontWeight: 500,
    fontFamily: 'var(--font-ui)',
    color: 'var(--text-primary)',
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  itemMeta: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-tertiary)',
    display: 'flex',
    gap: 'var(--space-sm)',
    marginTop: '2px',
  },
  itemActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-xs)',
    flexShrink: 0,
  },
  formatBadge: {
    fontSize: '9px',
    fontWeight: 600,
    fontFamily: 'var(--font-mono)',
    padding: '2px 6px',
    borderRadius: '4px',
    letterSpacing: '0.5px',
  },
  deleteBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--text-tertiary)',
    padding: '4px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'color 0.15s',
  },
}
