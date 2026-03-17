import React from 'react'
import { getResultDownloadUrl } from '../api/client'

interface Props {
  jobId: string
}

export default function FileDownload({ jobId }: Props) {
  return (
    <div className="animate-in animate-in-delay-3">
      <a href={getResultDownloadUrl(jobId)} download style={styles.downloadBtn}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        結果ファイルをダウンロード
      </a>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  downloadBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px',
    background: 'linear-gradient(135deg, #2d6a4f, #3a8a5c)',
    color: '#fff',
    border: '1px solid rgba(58, 138, 92, 0.25)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: 'var(--font-ui)',
    textAlign: 'center' as const,
    textDecoration: 'none',
    cursor: 'pointer',
    width: '100%',
    transition: 'all 0.2s',
    letterSpacing: '0.3px',
  },
}
