import React, { useEffect, useRef } from 'react'
import type { JobStatus } from '../types'

interface Props {
  jobStatus: JobStatus | null
}

const STEP_LABELS: Record<string, string> = {
  queued: '待機中',
  initializing: '初期化中',
  extracting_frames: 'フレーム抽出中',
  estimating_poses: 'ポーズ推定中',
  processing_data: 'データ処理中',
  converting_3d: '3D変換中',
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
  const stepLabel = STEP_LABELS[jobStatus.current_step] || jobStatus.current_step

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>進捗</h3>
      <div style={styles.progressContainer}>
        <div style={styles.progressHeader}>
          <span style={styles.stepLabel}>{stepLabel}</span>
          <span style={styles.pct}>{pct}%</span>
        </div>
        <div style={styles.progressBar}>
          <div
            style={{
              ...styles.progressFill,
              width: `${pct}%`,
              background: jobStatus.status === 'failed' ? '#ef4444' : '#6366f1',
            }}
          />
        </div>
      </div>
      <pre ref={logRef} style={styles.log}>
        {jobStatus.log || 'Waiting...'}
      </pre>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  section: { marginBottom: '16px' },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#aaa',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: '8px',
  },
  progressContainer: { marginBottom: '8px' },
  progressHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '4px',
  },
  stepLabel: { fontSize: '13px', color: '#ccc' },
  pct: { fontSize: '13px', color: '#6366f1', fontWeight: 600 },
  progressBar: {
    height: '6px',
    background: '#2a2a35',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
  },
  log: {
    background: '#0a0a0f',
    border: '1px solid #2a2a35',
    borderRadius: '8px',
    padding: '10px',
    fontSize: '12px',
    color: '#9ca3af',
    maxHeight: '200px',
    overflowY: 'auto' as const,
    whiteSpace: 'pre-wrap' as const,
    fontFamily: 'monospace',
    lineHeight: 1.5,
  },
}
