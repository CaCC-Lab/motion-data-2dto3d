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
    (file: File) => {
      if (!disabled) onUpload(file)
    },
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
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>動画入力</h3>
      <div
        style={{
          ...styles.dropzone,
          ...(dragOver ? styles.dropzoneActive : {}),
          ...(disabled ? styles.disabled : {}),
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
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
        <div style={styles.icon}>&#x1F3AC;</div>
        <div style={styles.text}>
          クリックまたはドラッグ&ドロップで動画をアップロード
        </div>
        <div style={styles.hint}>MP4, AVI, MOV, MKV, WebM (最大500MB)</div>
      </div>
      {videoInfo && (
        <div style={styles.info}>
          <div style={styles.infoRow}>
            <span>解像度</span>
            <span>
              {videoInfo.width}x{videoInfo.height}
            </span>
          </div>
          <div style={styles.infoRow}>
            <span>FPS</span>
            <span>{videoInfo.fps}</span>
          </div>
          <div style={styles.infoRow}>
            <span>フレーム数</span>
            <span>{videoInfo.total_frames}</span>
          </div>
          <div style={styles.infoRow}>
            <span>長さ</span>
            <span>{videoInfo.duration.toFixed(2)}s</span>
          </div>
          <div style={styles.infoRow}>
            <span>コーデック</span>
            <span>{videoInfo.codec}</span>
          </div>
        </div>
      )}
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
  dropzone: {
    border: '2px dashed #3a3a45',
    borderRadius: '10px',
    padding: '24px',
    textAlign: 'center' as const,
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: '#16161d',
  },
  dropzoneActive: {
    borderColor: '#6366f1',
    background: '#1a1a2e',
  },
  disabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  icon: { fontSize: '32px', marginBottom: '8px' },
  text: { fontSize: '14px', color: '#ccc', marginBottom: '4px' },
  hint: { fontSize: '12px', color: '#666' },
  info: {
    marginTop: '10px',
    padding: '10px',
    background: '#16161d',
    borderRadius: '8px',
    fontSize: '13px',
  },
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '3px 0',
    color: '#bbb',
  },
}
