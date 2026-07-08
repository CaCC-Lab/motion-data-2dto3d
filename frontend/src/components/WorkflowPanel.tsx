import React, { useState, useCallback, useRef } from 'react'
import type { WorkflowStatus } from '../types'
import { uploadGlb } from '../api/client'

type ModelInputMode = 'prompt' | 'glb'

interface Props {
  onStart: (params: {
    prompt?: string
    glb_file_id?: string
    video_id?: string
    engine_3d: string
    mesh_quality: string
    motion_fps: number
  }) => void
  workflowStatus: WorkflowStatus | null
  disabled: boolean
  onUploadVideo: (file: File) => Promise<string>
}

const STEP_LABELS: Record<string, string> = {
  idle: '待機中',
  pending: '初期化中',
  generating_model: '3Dモデル生成中',
  extracting_motion: 'モーション抽出中',
  rigging: '自動リギング中',
  retargeting: 'リターゲティング中',
  exporting: 'エクスポート中',
  completed: '完了',
  failed: 'エラー',
}

const STEP_ORDER = [
  'generating_model',
  'rigging',
  'extracting_motion',
  'retargeting',
  'completed',
]

export default function WorkflowPanel({ onStart, workflowStatus, disabled, onUploadVideo }: Props) {
  const [modelMode, setModelMode] = useState<ModelInputMode>('glb')
  const [prompt, setPrompt] = useState('')
  const [glbFile, setGlbFile] = useState<File | null>(null)
  const [glbFileId, setGlbFileId] = useState<string | null>(null)
  const [glbUploading, setGlbUploading] = useState(false)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [videoId, setVideoId] = useState<string | null>(null)
  const [engine3d, setEngine3d] = useState('hunyuan3d')
  const [meshQuality, setMeshQuality] = useState('balanced')
  const [motionFps, setMotionFps] = useState(30)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const glbInputRef = useRef<HTMLInputElement>(null)

  const isRunning = workflowStatus != null &&
    !['completed', 'failed'].includes(workflowStatus.status) &&
    workflowStatus.status !== 'idle'

  const handleGlbSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setGlbFile(file)
    setGlbUploading(true)
    try {
      const res = await uploadGlb(file)
      setGlbFileId(res.glb_id)
    } catch {
      setGlbFileId(null)
    }
    setGlbUploading(false)
  }, [])

  const handleVideoSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setVideoFile(file)
    setUploading(true)
    try {
      const id = await onUploadVideo(file)
      setVideoId(id)
    } catch {
      setVideoId(null)
    }
    setUploading(false)
  }, [onUploadVideo])

  const handleStart = useCallback(() => {
    const hasModel = modelMode === 'prompt' ? prompt.trim().length > 0 : !!glbFileId
    if (!hasModel || !videoId) return
    onStart({
      ...(modelMode === 'prompt'
        ? { prompt: prompt.trim(), engine_3d: engine3d, mesh_quality: meshQuality }
        : { glb_file_id: glbFileId! }),
      video_id: videoId,
      engine_3d: engine3d,
      mesh_quality: meshQuality,
      motion_fps: motionFps,
    })
  }, [modelMode, prompt, glbFileId, videoId, engine3d, meshQuality, motionFps, onStart])

  const hasModel = modelMode === 'prompt' ? prompt.trim().length > 0 : !!glbFileId
  const canStart = hasModel && videoId && !disabled && !isRunning

  return (
    <div>
      {/* Step 1: Model */}
      <h3 style={styles.sectionTitle}>
        <span style={styles.sectionNum}>01</span>
        CREATE MODEL
      </h3>
      <div style={styles.card} className="animate-in">
        {/* Mode toggle */}
        <div style={styles.modelModeToggle}>
          <button
            type="button"
            onClick={() => setModelMode('glb')}
            disabled={isRunning}
            style={{
              ...styles.modelModeBtn,
              ...(modelMode === 'glb' ? styles.modelModeBtnActive : {}),
            }}
          >
            GLBアップロード
          </button>
          <button
            type="button"
            onClick={() => setModelMode('prompt')}
            disabled={isRunning}
            style={{
              ...styles.modelModeBtn,
              ...(modelMode === 'prompt' ? styles.modelModeBtnActive : {}),
            }}
          >
            テキスト生成
          </button>
        </div>

        {modelMode === 'prompt' ? (
          <>
            <label style={styles.label}>プロンプト</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="ピッチャーのキャラクター、野球ユニフォーム..."
              disabled={isRunning}
              style={styles.textarea}
              rows={3}
            />
            <div style={styles.row}>
              <div style={styles.field}>
                <label style={styles.label}>3Dエンジン</label>
                <select
                  value={engine3d}
                  onChange={(e) => setEngine3d(e.target.value)}
                  disabled={isRunning}
                  style={styles.select}
                >
                  <option value="hunyuan3d">Hunyuan3D (高品質)</option>
                  <option value="triposr">TripoSR (高速)</option>
                  <option value="hunyuan3d_mv">Hunyuan3D MV</option>
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>メッシュ品質</label>
                <select
                  value={meshQuality}
                  onChange={(e) => setMeshQuality(e.target.value)}
                  disabled={isRunning}
                  style={styles.select}
                >
                  <option value="fast">Fast (100k)</option>
                  <option value="balanced">Balanced (200k)</option>
                  <option value="high">High (無制限)</option>
                </select>
              </div>
            </div>
          </>
        ) : (
          <>
            <label style={styles.label}>3Dモデルファイル (.glb / .vrm)</label>
            <div style={styles.fileInput}>
              <input
                ref={glbInputRef}
                type="file"
                accept=".glb,.gltf,.vrm"
                onChange={handleGlbSelect}
                disabled={isRunning}
                style={styles.hiddenInput}
              />
              <button
                type="button"
                onClick={() => glbInputRef.current?.click()}
                disabled={isRunning}
                style={{
                  ...styles.fileLabel,
                  ...(isRunning ? { opacity: 0.5, pointerEvents: 'none' as const } : {}),
                }}
              >
                {glbUploading ? 'アップロード中...' :
                 glbFile ? glbFile.name :
                 'GLB/VRMファイルを選択'}
              </button>
              {glbFileId && (
                <span style={styles.checkmark}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2.5">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* Step 2: Motion */}
      <h3 style={{ ...styles.sectionTitle, marginTop: 'var(--space-xl)' }}>
        <span style={styles.sectionNum}>02</span>
        CAPTURE MOTION
      </h3>
      <div style={styles.card} className="animate-in animate-in-delay-1">
        <span style={styles.label}>モーション動画</span>
        <div style={styles.fileInput}>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleVideoSelect}
            disabled={isRunning}
            style={styles.hiddenInput}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isRunning}
            style={{
              ...styles.fileLabel,
              ...(isRunning ? { opacity: 0.5, pointerEvents: 'none' as const } : {}),
            }}
          >
            {uploading ? 'アップロード中...' :
             videoFile ? videoFile.name :
             '動画ファイルを選択'}
          </button>
          {videoId && (
            <span style={styles.checkmark}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2.5">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </span>
          )}
        </div>
        <div style={styles.row}>
          <div style={styles.field}>
            <label style={styles.label}>FPS</label>
            <input
              type="number"
              value={motionFps}
              onChange={(e) => setMotionFps(Number(e.target.value))}
              min={1}
              max={120}
              disabled={isRunning}
              style={styles.numberInput}
            />
          </div>
        </div>
      </div>

      {/* Step 3: Execute */}
      <h3 style={{ ...styles.sectionTitle, marginTop: 'var(--space-xl)' }}>
        <span style={styles.sectionNum}>03</span>
        ANIMATE
      </h3>
      <div style={styles.card} className="animate-in animate-in-delay-2">
        <button
          onClick={handleStart}
          disabled={!canStart}
          style={{
            ...styles.startBtn,
            ...(!canStart ? styles.startBtnDisabled : {}),
            ...(isRunning ? styles.startBtnRunning : {}),
          }}
        >
          {isRunning ? (
            <>
              <span style={styles.spinner} />
              処理中...
            </>
          ) : '統合パイプラインを実行'}
        </button>
        {!canStart && !isRunning && (
          <div style={styles.hint}>
            {!hasModel && !videoId
              ? (modelMode === 'prompt' ? 'プロンプトと動画を入力してください' : 'GLBファイルと動画をアップロードしてください')
              : !hasModel
              ? (modelMode === 'prompt' ? 'プロンプトを入力してください' : 'GLBファイルをアップロードしてください')
              : !videoId ? '動画をアップロードしてください' : ''}
          </div>
        )}

        {/* Progress */}
        {workflowStatus && workflowStatus.status !== 'idle' && (
          <div style={styles.progress}>
            <div style={styles.stepIndicators}>
              {STEP_ORDER.map((step, i) => {
                const currentIdx = STEP_ORDER.indexOf(workflowStatus.status)
                const stepIdx = i
                const isDone = stepIdx < currentIdx || workflowStatus.status === 'completed'
                const isCurrent = step === workflowStatus.status
                const isFailed = workflowStatus.status === 'failed'

                return (
                  <div key={step} style={styles.stepItem}>
                    <div style={{
                      ...styles.stepDot,
                      background: isDone ? 'var(--success)' :
                        isCurrent ? (isFailed ? 'var(--error)' : 'var(--accent)') :
                        'var(--border-default)',
                      ...(isCurrent && !isFailed ? { animation: 'progressPulse 1.5s ease-in-out infinite' } : {}),
                    }} />
                    <span style={{
                      ...styles.stepText,
                      color: isCurrent ? 'var(--text-primary)' :
                        isDone ? 'var(--success)' : 'var(--text-tertiary)',
                      fontWeight: isCurrent ? 600 : 400,
                    }}>
                      {STEP_LABELS[step] || step}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Progress bar */}
            <div style={styles.progressTrack}>
              <div style={{
                ...styles.progressFill,
                width: `${workflowStatus.progress * 100}%`,
                background: workflowStatus.status === 'failed' ? 'var(--error)' :
                  workflowStatus.status === 'completed' ? 'var(--success)' :
                  'linear-gradient(90deg, var(--main-dim), var(--main))',
              }} />
            </div>

            <div style={styles.statusText}>
              {workflowStatus.current_step}
              {workflowStatus.progress > 0 && workflowStatus.progress < 1 && (
                <span style={{ marginLeft: '8px', color: 'var(--main)' }}>
                  {Math.round(workflowStatus.progress * 100)}%
                </span>
              )}
            </div>

            {workflowStatus.error && (
              <div style={styles.errorBox}>
                <span style={styles.errorDot} />
                {workflowStatus.error}
              </div>
            )}
          </div>
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
    display: 'flex', flexDirection: 'column' as const, gap: 'var(--space-md)',
  },
  label: {
    fontSize: '11px', fontWeight: 500, color: 'var(--text-secondary)',
    fontFamily: 'var(--font-mono)', letterSpacing: '0.5px',
  },
  textarea: {
    width: '100%', padding: 'var(--space-md)',
    background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)', fontSize: '13px',
    fontFamily: 'var(--font-ui)', color: 'var(--text-primary)',
    resize: 'vertical' as const, outline: 'none',
    boxSizing: 'border-box' as const,
  },
  row: {
    display: 'flex', gap: 'var(--space-md)',
  },
  field: {
    flex: 1, display: 'flex', flexDirection: 'column' as const, gap: '4px',
  },
  select: {
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)', fontSize: '12px',
    fontFamily: 'var(--font-mono)', color: 'var(--text-primary)',
    outline: 'none',
  },
  numberInput: {
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)', fontSize: '12px',
    fontFamily: 'var(--font-mono)', color: 'var(--text-primary)',
    outline: 'none', width: '80px',
  },
  fileInput: {
    display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
  },
  hiddenInput: {
    display: 'none',
  },
  fileLabel: {
    padding: 'var(--space-sm) var(--space-lg)',
    background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)', fontSize: '12px',
    fontFamily: 'var(--font-ui)', color: 'var(--text-secondary)',
    cursor: 'pointer', transition: 'all 0.15s',
  },
  checkmark: {
    display: 'flex', alignItems: 'center',
  },
  startBtn: {
    padding: 'var(--space-md) var(--space-xl)',
    background: 'linear-gradient(135deg, var(--main) 0%, var(--main-dim) 100%)',
    color: '#ffffff', border: 'none',
    borderRadius: 'var(--radius-md)', fontSize: '14px',
    fontFamily: 'var(--font-ui)', fontWeight: 600,
    cursor: 'pointer', width: '100%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 'var(--space-sm)', transition: 'all 0.2s',
    letterSpacing: '0.5px',
  },
  startBtnDisabled: {
    opacity: 0.4, cursor: 'not-allowed',
  },
  startBtnRunning: {
    background: 'var(--bg-surface)', color: 'var(--text-secondary)',
    border: '1px solid var(--border-default)', cursor: 'default',
  },
  spinner: {
    width: '14px', height: '14px',
    border: '2px solid var(--border-default)',
    borderTopColor: 'var(--main)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
    display: 'inline-block',
  },
  progress: {
    display: 'flex', flexDirection: 'column' as const, gap: 'var(--space-md)',
    marginTop: 'var(--space-sm)',
  },
  stepIndicators: {
    display: 'flex', flexDirection: 'column' as const, gap: '6px',
  },
  stepItem: {
    display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
  },
  stepDot: {
    width: '8px', height: '8px', borderRadius: '50%',
    flexShrink: 0, transition: 'all 0.3s',
  },
  stepText: {
    fontSize: '11px', fontFamily: 'var(--font-mono)',
    transition: 'all 0.2s',
  },
  progressTrack: {
    height: '3px', background: 'var(--border-default)',
    borderRadius: '2px', overflow: 'hidden',
  },
  progressFill: {
    height: '100%', borderRadius: '2px',
    transition: 'width 0.4s ease',
  },
  statusText: {
    fontSize: '12px', fontFamily: 'var(--font-mono)',
    color: 'var(--text-secondary)',
  },
  errorBox: {
    padding: 'var(--space-sm) var(--space-md)',
    background: 'var(--error-dim)', border: '1px solid rgba(210,72,72,0.15)',
    borderRadius: 'var(--radius-sm)', fontSize: '11px',
    fontFamily: 'var(--font-mono)', color: 'var(--sub)',
    display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
  },
  errorDot: {
    width: '6px', height: '6px', borderRadius: '50%',
    background: 'var(--error)', flexShrink: 0,
  },
  hint: {
    fontSize: '11px', fontFamily: 'var(--font-mono)',
    color: 'var(--text-tertiary)', textAlign: 'center' as const,
  },
  modelModeToggle: {
    display: 'flex', borderRadius: '6px',
    border: '1px solid var(--border-default)', overflow: 'hidden',
  },
  modelModeBtn: {
    flex: 1, padding: '6px 12px', fontSize: '11px',
    fontFamily: 'var(--font-mono)', fontWeight: 500,
    color: 'var(--text-tertiary)', background: 'transparent',
    border: 'none', cursor: 'pointer', transition: 'all 0.15s',
  },
  modelModeBtnActive: {
    background: 'var(--main)', color: '#ffffff',
  },
}
