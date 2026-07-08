import React, { useState, useCallback, useRef, useEffect } from 'react'
import type { AppState, AppMode, VideoInfo, JobStatus, ProcessingParams, HistoryItem, WorkflowStatus } from './types'
import Layout from './components/Layout'
import VideoUpload from './components/VideoUpload'
import ParameterForm from './components/ParameterForm'
import ProcessingLog from './components/ProcessingLog'
import FileDownload from './components/FileDownload'
import BvhViewer from './components/BvhViewer'
import VrmViewer from './components/VrmViewer'
import ProcessingHistory from './components/ProcessingHistory'
import WorkflowPanel from './components/WorkflowPanel'
import {
  uploadVideo, getVideoInfo, startProcessing, subscribeJobStatus, getBvhText,
  getHistoryList, deleteHistoryItem, getHistoryBvhText,
  startWorkflow, subscribeWorkflowStatus, getIntegrationFileUrl, checkIntegrationHealth,
} from './api/client'

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
  // === Mode ===
  const [mode, setMode] = useState<AppMode>('motion')
  const [integrationAvailable, setIntegrationAvailable] = useState(false)

  // === Motion mode state ===
  const [appState, setAppState] = useState<AppState>('idle')
  const [videoId, setVideoId] = useState<string | null>(null)
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null)
  const [params, setParams] = useState(DEFAULT_PARAMS)
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [bvhText, setBvhText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([])
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  // === Integration mode state ===
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus | null>(null)
  const [animationGlbUrl, setAnimationGlbUrl] = useState<string | null>(null)
  const workflowUnsubRef = useRef<(() => void) | null>(null)

  // Integration API availability check
  useEffect(() => {
    checkIntegrationHealth().then(setIntegrationAvailable)
  }, [])

  // === Motion mode handlers ===
  const fetchHistory = useCallback(async () => {
    try {
      const { items } = await getHistoryList()
      setHistoryItems(items)
    } catch {
      // 履歴取得失敗は静かに無視
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

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
            setSelectedHistoryId(null)
            fetchHistory()
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
  }, [videoId, params, fetchHistory])

  const handleHistorySelect = useCallback(async (historyJobId: string) => {
    try {
      const bvh = await getHistoryBvhText(historyJobId)
      setBvhText(bvh)
      setSelectedHistoryId(historyJobId)
      setVideoId(null)
    } catch {
      setError('履歴BVHの読み込みに失敗しました')
    }
  }, [])

  const handleHistoryDelete = useCallback(async (historyJobId: string) => {
    try {
      await deleteHistoryItem(historyJobId)
      if (selectedHistoryId === historyJobId) {
        setBvhText(null)
        setSelectedHistoryId(null)
      }
      fetchHistory()
    } catch {
      setError('履歴の削除に失敗しました')
    }
  }, [selectedHistoryId, fetchHistory])

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

  // === Integration mode handlers ===
  const handleUploadVideoForWorkflow = useCallback(async (file: File): Promise<string> => {
    const res = await uploadVideo(file)
    return res.video_id
  }, [])

  const handleStartWorkflow = useCallback(async (params: {
    prompt?: string
    glb_file_id?: string
    video_id?: string
    engine_3d: string
    mesh_quality: string
    motion_fps: number
  }) => {
    try {
      setError(null)
      setAnimationGlbUrl(null)
      workflowUnsubRef.current?.()

      const wfId = await startWorkflow(params)

      workflowUnsubRef.current = subscribeWorkflowStatus(
        wfId,
        (status) => {
          setWorkflowStatus(status)

          // モデル生成完了時にプレビュー表示
          if (status.model_glb_url && !animationGlbUrl) {
            setAnimationGlbUrl(getIntegrationFileUrl(status.model_glb_url.split('/').pop() || ''))
          }

          // アニメーション完了時
          if (status.status === 'completed' && status.animation_glb_url) {
            const filename = status.animation_glb_url.split('/').pop() || ''
            setAnimationGlbUrl(getIntegrationFileUrl(filename))
          }
        },
        (err) => {
          setError(err.message)
        },
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start workflow')
    }
  }, [animationGlbUrl])

  // === Render ===
  const isWorkflowRunning = workflowStatus != null &&
    !['completed', 'failed', 'idle'].includes(workflowStatus.status)

  const currentStatus = mode === 'integration'
    ? (isWorkflowRunning ? 'Processing...' :
       workflowStatus?.status === 'completed' ? 'Complete' :
       workflowStatus?.status === 'failed' ? 'Error' : 'Ready')
    : (appState === 'idle' ? 'Ready' :
       appState === 'uploading' ? 'Uploading...' :
       appState === 'processing' ? 'Processing...' :
       appState === 'complete' ? 'Complete' : 'Error')

  const statusColor = currentStatus === 'Processing...' ? 'var(--accent)' :
    currentStatus === 'Complete' ? 'var(--success)' :
    currentStatus === 'Error' ? 'var(--error)' : 'var(--text-tertiary)'

  // Left panel content
  const motionLeftPanel = (
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
      {error && mode === 'motion' && (
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
      <ProcessingHistory
        items={historyItems}
        onSelect={handleHistorySelect}
        onDelete={handleHistoryDelete}
        selectedJobId={selectedHistoryId}
      />
    </>
  )

  const integrationLeftPanel = (
    <>
      <WorkflowPanel
        onStart={handleStartWorkflow}
        workflowStatus={workflowStatus}
        disabled={false}
        onUploadVideo={handleUploadVideoForWorkflow}
      />
      {error && mode === 'integration' && (
        <div className="animate-in" style={{ ...styles.error, marginTop: 'var(--space-lg)' }}>
          <span style={styles.errorDot} />
          {error}
        </div>
      )}
      {workflowStatus?.status === 'completed' && workflowStatus.blend_path && (
        <div className="animate-in" style={styles.exportInfo}>
          <div style={styles.exportTitle}>出力ファイル</div>
          {workflowStatus.animation_glb_url && (
            <a
              href={getIntegrationFileUrl(workflowStatus.animation_glb_url.split('/').pop() || '')}
              download
              style={styles.exportLink}
            >
              Animation GLB
            </a>
          )}
          <div style={styles.exportPath}>
            Blend: {workflowStatus.blend_path}
          </div>
        </div>
      )}
    </>
  )

  const leftPanel = mode === 'motion' ? motionLeftPanel : integrationLeftPanel

  const rightPanel = mode === 'motion'
    ? <BvhViewer bvhText={bvhText} videoId={videoId} />
    : <VrmViewer glbUrl={animationGlbUrl} />

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div style={styles.logoGroup}>
          <div style={styles.logoMark} />
          <div>
            <h1 style={styles.title}>MOTION LAB</h1>
            <span style={styles.subtitle}>
              {mode === 'motion' ? 'Video Motion Extraction' : 'Text → Character Animation'}
            </span>
          </div>
        </div>

        <div style={styles.headerRight}>
          {/* Mode toggle */}
          <div style={styles.modeToggle}>
            <button
              onClick={() => setMode('motion')}
              style={{
                ...styles.modeBtn,
                ...(mode === 'motion' ? styles.modeBtnActive : {}),
              }}
            >
              Motion
            </button>
            <button
              onClick={() => setMode('integration')}
              disabled={!integrationAvailable}
              style={{
                ...styles.modeBtn,
                ...(mode === 'integration' ? styles.modeBtnActive : {}),
                ...(!integrationAvailable ? { opacity: 0.3, cursor: 'not-allowed' } : {}),
              }}
              title={integrationAvailable ? 'テキスト→キャラアニメーション' : 'Integration API未接続'}
            >
              Integrate
            </button>
          </div>

          <div style={styles.statusChip}>
            <span style={{ ...styles.statusDot, background: statusColor }} />
            <span style={styles.statusText}>{currentStatus}</span>
          </div>
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
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-md)',
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
  modeToggle: {
    display: 'flex',
    borderRadius: '8px',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
  },
  modeBtn: {
    padding: '5px 14px',
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    fontWeight: 500,
    color: 'var(--text-tertiary)',
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.15s',
    letterSpacing: '0.5px',
  },
  modeBtnActive: {
    background: 'var(--main)',
    color: '#ffffff',
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
  exportInfo: {
    marginTop: 'var(--space-lg)',
    padding: 'var(--space-lg)',
    background: 'var(--bg-root)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-subtle)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-sm)',
  },
  exportTitle: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase',
    letterSpacing: '1.5px',
  },
  exportLink: {
    fontSize: '13px',
    fontFamily: 'var(--font-ui)',
    color: 'var(--main)',
    fontWeight: 500,
    textDecoration: 'none',
  },
  exportPath: {
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-tertiary)',
    wordBreak: 'break-all',
  },
}
