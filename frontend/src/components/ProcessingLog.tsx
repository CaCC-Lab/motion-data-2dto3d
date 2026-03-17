import React, { useEffect, useRef } from 'react'
import type { JobStatus } from '../types'

interface Props {
  jobStatus: JobStatus | null
}

const STEP_LABELS: Record<string, string> = {
  queued: '待機中',
  initializing: '初期化中',
  extracting_frames: 'フレーム抽出',
  estimating_poses: 'ポーズ推定',
  processing_data: 'データ処理',
  converting_3d: '3D変換',
  done: '完了',
  error: 'エラー',
}

export default function ProcessingLog({ jobStatus }: Props) {
  const logRef = useRef<HTMLPreElement>(null)

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [jobStatus?.log])

  if (!jobStatus) return null
  const pct = Math.round(jobStatus.progress * 100)
  const failed = jobStatus.status === 'failed'
  const done = jobStatus.status === 'completed'

  return (
    <div className="animate-in animate-in-delay-2">
      <h3 style={styles.sectionTitle}>
        <span style={styles.sectionNum}>03</span>
        PROGRESS
      </h3>

      <div style={styles.card}>
        {/* Step + percentage */}
        <div style={styles.statusRow}>
          <span style={{
            ...styles.stepLabel,
            color: failed ? 'var(--error)' : done ? 'var(--success)' : 'var(--text-primary)',
          }}>
            {STEP_LABELS[jobStatus.current_step] || jobStatus.current_step}
          </span>
          <span style={{
            ...styles.pct,
            color: failed ? 'var(--error)' : 'var(--main)',
          }}>
            {pct}%
          </span>
        </div>

        {/* Progress bar */}
        <div style={styles.progressTrack}>
          <div style={{
            ...styles.progressFill,
            width: `${pct}%`,
            background: failed ? 'var(--error)' : done
              ? 'var(--success)'
              : 'linear-gradient(90deg, var(--main-dim), var(--main))',
            ...((!done && !failed) ? { animation: 'progressPulse 1.5s ease-in-out infinite' } : {}),
          }} />
        </div>

        {/* Log */}
        {jobStatus.log && (
          <pre ref={logRef} style={styles.logBox}>
            {jobStatus.log}
          </pre>
        )}
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
    padding: 'var(--space-lg)', border: '1px solid var(--border-subtle)',
    display: 'flex', flexDirection: 'column', gap: 'var(--space-md)',
  },
  statusRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  stepLabel: {
    fontSize: '13px', fontWeight: 600, fontFamily: 'var(--font-ui)',
  },
  pct: {
    fontSize: '18px', fontWeight: 700, fontFamily: 'var(--font-mono)',
  },
  progressTrack: {
    height: '4px', background: 'var(--border-default)',
    borderRadius: '2px', overflow: 'hidden',
  },
  progressFill: {
    height: '100%', borderRadius: '2px',
    transition: 'width 0.4s ease',
  },
  logBox: {
    background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-sm)', padding: 'var(--space-md)',
    fontSize: '11px', color: 'var(--text-secondary)',
    maxHeight: '180px', overflowY: 'auto' as const,
    whiteSpace: 'pre-wrap' as const, fontFamily: 'var(--font-mono)',
    lineHeight: 1.6, margin: 0,
  },
}
