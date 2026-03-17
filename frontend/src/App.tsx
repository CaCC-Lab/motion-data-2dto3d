import React, { useState, useCallback, useRef } from 'react'
import type { AppState, VideoInfo, JobStatus, ProcessingParams } from './types'
import Layout from './components/Layout'
import VideoUpload from './components/VideoUpload'
import ParameterForm from './components/ParameterForm'
import ProcessingLog from './components/ProcessingLog'
import FileDownload from './components/FileDownload'
import BvhViewer from './components/BvhViewer'
import { uploadVideo, getVideoInfo, startProcessing, subscribeJobStatus, getBvhText } from './api/client'

const DEFAULT_PARAMS: Omit<ProcessingParams, 'video_id'> = {
  fps: 30,
  threshold: 0.3,
  smoothing: 5,
  remove_joints: '',
  output_format: 'bvh',
  batch_size: 32,
  bvh_mode: 'position',
  smooth_3d: 1.0,
  root_motion_scale: 2.5,
}

export default function App() {
  const [appState, setAppState] = useState<AppState>('idle')
  const [videoId, setVideoId] = useState<string | null>(null)
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null)
  const [params, setParams] = useState(DEFAULT_PARAMS)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [bvhText, setBvhText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  const handleUpload = useCallback(async (file: File) => {
    try {
      setAppState('uploading')
      setError(null)
      setBvhText(null)
      setJobStatus(null)
      const res = await uploadVideo(file)
      setVideoId(res.video_id)
      const info = await getVideoInfo(res.video_id)
      setVideoInfo(info)
      setAppState('idle')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      setAppState('error')
    }
  }, [])

  const handleProcess = useCallback(async () => {
    if (!videoId) return
    try {
      setAppState('processing')
      setError(null)
      setBvhText(null)
      unsubscribeRef.current?.()
      const jid = await startProcessing({ ...params, video_id: videoId })
      setJobId(jid)

      unsubscribeRef.current = subscribeJobStatus(
        jid,
        (status) => {
          setJobStatus(status)
          if (status.status === 'completed') {
            setAppState('complete')
            if (status.output_format === 'bvh') {
              getBvhText(jid).then(setBvhText).catch(() => {})
            }
          } else if (status.status === 'failed') {
            setAppState('error')
            setError(status.error || 'Processing failed')
          }
        },
        (err) => {
          setAppState('error')
          setError(err.message)
        },
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start processing')
      setAppState('error')
    }
  }, [videoId, params])

  const handleReset = useCallback(() => {
    unsubscribeRef.current?.()
    unsubscribeRef.current = null
    setAppState('idle')
    setVideoId(null)
    setVideoInfo(null)
    setJobId(null)
    setJobStatus(null)
    setBvhText(null)
    setError(null)
  }, [])

  const leftPanel = (
    <>
      <VideoUpload
        onUpload={handleUpload}
        videoInfo={videoInfo}
        disabled={appState === 'processing' || appState === 'uploading'}
      />
      <ParameterForm
        params={params}
        onChange={setParams}
        onSubmit={handleProcess}
        disabled={!videoId || appState === 'processing' || appState === 'uploading'}
        processing={appState === 'processing'}
      />
      {(appState === 'processing' || appState === 'complete' || appState === 'error') && (
        <ProcessingLog jobStatus={jobStatus} />
      )}
      {appState === 'complete' && jobId && <FileDownload jobId={jobId} />}
      {error && (
        <div className="animate-in" style={styles.error}>
          <span style={styles.errorDot} />
          {error}
        </div>
      )}
      {appState === 'complete' && (
        <button onClick={handleReset} style={styles.resetBtn}>
          <span style={{ opacity: 0.5, marginRight: '6px' }}>+</span>
          新しい動画を処理
        </button>
      )}
    </>
  )

  const rightPanel = <BvhViewer bvhText={bvhText} videoId={videoId} />

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div style={styles.logoGroup}>
          <div style={styles.logoMark} />
          <div>
            <h1 style={styles.title}>MOTION LAB</h1>
            <span style={styles.subtitle}>Video Motion Extraction</span>
          </div>
        </div>
        <div style={styles.statusChip}>
          <span style={{
            ...styles.statusDot,
            background: appState === 'processing' ? 'var(--accent)' :
              appState === 'complete' ? 'var(--success)' :
              appState === 'error' ? 'var(--error)' : 'var(--text-tertiary)',
          }} />
          <span style={styles.statusText}>
            {appState === 'idle' ? 'Ready' :
             appState === 'uploading' ? 'Uploading...' :
             appState === 'processing' ? 'Processing...' :
             appState === 'complete' ? 'Complete' : 'Error'}
          </span>
        </div>
      </header>
      <Layout left={leftPanel} right={rightPanel} />
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    background: 'var(--bg-root)',
    color: 'var(--text-primary)',
  },
  header: {
    height: 'var(--header-height)',
    padding: '0 var(--space-xl)',
    borderBottom: '1px solid var(--border-default)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: 'var(--bg-surface)',
  },
  logoGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
  },
  logoMark: {
    width: '28px',
    height: '28px',
    borderRadius: '8px',
    background: 'linear-gradient(135deg, var(--main) 0%, var(--main-dim) 100%)',
    boxShadow: '0 2px 8px rgba(59, 59, 107, 0.25)',
  },
  title: {
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--main)',
    letterSpacing: '2.5px',
    fontFamily: 'var(--font-ui)',
    lineHeight: 1,
  },
  subtitle: {
    fontSize: '10px',
    color: 'var(--text-tertiary)',
    fontFamily: 'var(--font-mono)',
    fontWeight: 400,
    letterSpacing: '0.5px',
  },
  statusChip: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 12px',
    background: 'var(--bg-root)',
    borderRadius: '20px',
    border: '1px solid var(--border-default)',
  },
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    display: 'inline-block',
  },
  statusText: {
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  error: {
    margin: 'var(--space-md) 0',
    padding: 'var(--space-md) var(--space-lg)',
    background: 'var(--error-dim)',
    border: '1px solid rgba(210, 72, 72, 0.15)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--sub)',
    fontSize: '12px',
    fontFamily: 'var(--font-mono)',
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-sm)',
  },
  errorDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--error)',
    flexShrink: 0,
    display: 'inline-block',
  },
  resetBtn: {
    marginTop: 'var(--space-md)',
    padding: 'var(--space-md) var(--space-lg)',
    background: 'var(--bg-surface)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: 'var(--font-ui)',
    fontWeight: 500,
    width: '100%',
    transition: 'all 0.2s',
  },
}
