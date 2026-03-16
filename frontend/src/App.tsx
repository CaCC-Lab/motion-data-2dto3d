import React, { useState, useCallback } from 'react'
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
      const jid = await startProcessing({ ...params, video_id: videoId })
      setJobId(jid)

      subscribeJobStatus(
        jid,
        (status) => {
          setJobStatus(status)
          if (status.status === 'completed') {
            setAppState('complete')
            if (status.result_file?.endsWith('.bvh')) {
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
        <div style={styles.error}>
          <strong>Error:</strong> {error}
        </div>
      )}
      {appState === 'complete' && (
        <button onClick={handleReset} style={styles.resetBtn}>
          新しい動画を処理
        </button>
      )}
    </>
  )

  const rightPanel = <BvhViewer bvhText={bvhText} />

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>Video Motion Extraction</h1>
        <span style={styles.subtitle}>動画から3Dモーションデータを抽出</span>
      </header>
      <Layout left={leftPanel} right={rightPanel} />
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    background: '#0f0f13',
    color: '#e0e0e0',
  },
  header: {
    padding: '16px 24px',
    borderBottom: '1px solid #2a2a35',
    display: 'flex',
    alignItems: 'baseline',
    gap: '16px',
  },
  title: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#fff',
  },
  subtitle: {
    fontSize: '14px',
    color: '#888',
  },
  error: {
    margin: '12px 0',
    padding: '12px',
    background: '#3d1c1c',
    border: '1px solid #7a2e2e',
    borderRadius: '8px',
    color: '#ff8888',
    fontSize: '13px',
  },
  resetBtn: {
    marginTop: '12px',
    padding: '10px 20px',
    background: '#2a2a35',
    color: '#e0e0e0',
    border: '1px solid #444',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    width: '100%',
  },
}
