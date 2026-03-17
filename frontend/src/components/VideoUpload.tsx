import React, { useCallback, useRef, useState } from 'react'
import type { VideoInfo } from '../types'

interface Props {
  onUpload: (file: File) => void
  videoInfo: VideoInfo | null
  disabled: boolean
}

export default function VideoUpload({ onUpload, videoInfo, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (file: File) => { if (!disabled) onUpload(file) },
    [onUpload, disabled],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  return (
    <div className="animate-in">
      <h3 style={styles.sectionTitle}>
        <span style={styles.sectionNum}>01</span>
        INPUT
      </h3>
      <div
        style={{
          ...styles.dropzone,
          ...(dragOver ? styles.dropzoneActive : {}),
          ...(disabled ? styles.disabled : {}),
        }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
          }}
        />
        <div style={styles.uploadIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <div style={styles.text}>ドラッグ&ドロップ または クリック</div>
        <div style={styles.hint}>MP4, AVI, MOV, MKV, WebM — 最大500MB</div>
      </div>
      {videoInfo && (
        <div style={styles.info} className="animate-in">
          <div style={styles.infoGrid}>
            <InfoCell label="解像度" value={`${videoInfo.width}×${videoInfo.height}`} />
            <InfoCell label="FPS" value={String(videoInfo.fps)} />
            <InfoCell label="フレーム" value={String(videoInfo.total_frames)} />
            <InfoCell label="長さ" value={`${videoInfo.duration.toFixed(2)}s`} />
            <InfoCell label="コーデック" value={videoInfo.codec} />
          </div>
        </div>
      )}
    </div>
  )
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div style={styles.infoCell}>
      <span style={styles.infoLabel}>{label}</span>
      <span style={styles.infoValue}>{value}</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  sectionTitle: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '1.5px',
    marginBottom: 'var(--space-sm)',
    fontFamily: 'var(--font-mono)',
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  sectionNum: {
    color: 'var(--main)',
    fontSize: '10px',
    fontWeight: 600,
  },
  dropzone: {
    border: '1px dashed var(--border-strong)',
    borderRadius: 'var(--radius-lg)',
    padding: 'var(--space-xl)',
    textAlign: 'center' as const,
    cursor: 'pointer',
    transition: 'all 0.25s ease',
    background: 'var(--bg-root)',
  },
  dropzoneActive: {
    borderColor: 'var(--main)',
    background: 'var(--main-light)',
    borderStyle: 'solid',
  },
  disabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
    pointerEvents: 'none' as const,
  },
  uploadIcon: {
    color: 'var(--text-tertiary)',
    marginBottom: 'var(--space-md)',
    display: 'flex',
    justifyContent: 'center',
  },
  text: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    marginBottom: 'var(--space-xs)',
    fontWeight: 500,
  },
  hint: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    fontFamily: 'var(--font-mono)',
  },
  info: {
    marginTop: 'var(--space-sm)',
    padding: 'var(--space-md)',
    background: 'var(--bg-root)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
  },
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 'var(--space-sm) var(--space-lg)',
  },
  infoCell: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  infoLabel: {
    fontSize: '10px',
    color: 'var(--text-tertiary)',
    fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  infoValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontWeight: 500,
  },
}
