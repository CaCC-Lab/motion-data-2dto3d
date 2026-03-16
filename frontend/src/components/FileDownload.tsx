import React from 'react'
import { getResultDownloadUrl } from '../api/client'

interface Props {
  jobId: string
}

export default function FileDownload({ jobId }: Props) {
  return (
    <div style={styles.section}>
      <a href={getResultDownloadUrl(jobId)} download style={styles.downloadBtn}>
        結果ファイルをダウンロード
      </a>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  section: { marginBottom: '16px' },
  downloadBtn: {
    display: 'block',
    padding: '12px',
    background: '#059669',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '15px',
    fontWeight: 600,
    textAlign: 'center' as const,
    textDecoration: 'none',
    cursor: 'pointer',
    width: '100%',
  },
}
