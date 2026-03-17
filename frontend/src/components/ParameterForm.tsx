import React from 'react'
import type { ProcessingParams } from '../types'

interface Props {
  params: Omit<ProcessingParams, 'video_id'>
  onChange: (p: Omit<ProcessingParams, 'video_id'>) => void
  onSubmit: () => void
  disabled: boolean
  processing: boolean
}

export default function ParameterForm({ params, onChange, onSubmit, disabled, processing }: Props) {
  const set = <K extends keyof typeof params>(key: K, val: (typeof params)[K]) =>
    onChange({ ...params, [key]: val })

  return (
    <div className="animate-in animate-in-delay-1">
      <h3 style={styles.sectionTitle}>
        <span style={styles.sectionNum}>02</span>
        PARAMETERS
      </h3>

      <div style={styles.card}>
        <div style={styles.paramGrid}>
          <SliderParam label="FPS" value={params.fps} min={1} max={120} step={1} onChange={(v) => set('fps', v)} />
          <SliderParam label="信頼度閾値" value={params.threshold} min={0} max={1} step={0.05} onChange={(v) => set('threshold', v)} />
          <SliderParam label="スムージング" value={params.smoothing} min={1} max={21} step={2} onChange={(v) => set('smoothing', v)} />
          <SliderParam label="バッチサイズ" value={params.batch_size} min={1} max={128} step={1} onChange={(v) => set('batch_size', v)} />
        </div>

        <div style={styles.divider} />

        <div style={styles.paramGrid}>
          <div style={styles.field}>
            <label style={styles.label}>出力フォーマット</label>
            <select value={params.output_format} onChange={(e) => set('output_format', e.target.value as 'bvh' | 'fbx' | 'json')} style={styles.select}>
              <option value="bvh">BVH</option>
              <option value="fbx">FBX</option>
              <option value="json">JSON</option>
            </select>
          </div>
          <div style={styles.field}>
            <label style={styles.label}>BVHモード</label>
            <select value={params.bvh_mode} onChange={(e) => set('bvh_mode', e.target.value as 'position' | 'rotation')} style={styles.select}>
              <option value="position">Position</option>
              <option value="rotation">Rotation</option>
            </select>
          </div>
        </div>

        <div style={styles.divider} />

        <div style={styles.paramGrid}>
          <SliderParam label="3Dスムーズσ" value={params.smooth_3d} min={0} max={5} step={0.1} onChange={(v) => set('smooth_3d', v)} />
          <SliderParam label="ルートモーション" value={params.root_motion_scale} min={0.1} max={10} step={0.1} onChange={(v) => set('root_motion_scale', v)} />
        </div>

        <div style={styles.field}>
          <label style={styles.label}>除外関節</label>
          <input type="text" value={params.remove_joints} onChange={(e) => set('remove_joints', e.target.value)} placeholder="例: left_hand_*, right_hand_*" style={styles.input} />
        </div>
      </div>

      <button onClick={onSubmit} disabled={disabled} style={{ ...styles.submitBtn, ...(disabled ? styles.submitDisabled : {}), ...(processing ? styles.submitProcessing : {}) }}>
        {processing ? '処理中...' : 'モーション抽出を実行'}
      </button>
    </div>
  )
}

function SliderParam({ label, value, min, max, step, onChange }: {
  label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void
}) {
  return (
    <div style={styles.field}>
      <div style={styles.sliderHeader}>
        <label style={styles.label}>{label}</label>
        <span style={styles.sliderValue}>{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} style={styles.slider} />
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
  paramGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md) var(--space-lg)' },
  divider: { height: '1px', background: 'var(--border-subtle)', margin: 'var(--space-xs) 0' },
  field: { display: 'flex', flexDirection: 'column', gap: '4px' },
  label: {
    fontSize: '10px', fontWeight: 500, color: 'var(--text-tertiary)',
    fontFamily: 'var(--font-mono)', textTransform: 'uppercase' as const, letterSpacing: '0.5px',
  },
  sliderHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  sliderValue: { fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--main)', fontWeight: 600 },
  slider: { width: '100%' },
  input: {
    width: '100%', padding: '8px 10px', background: 'var(--bg-input)',
    border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)',
    color: 'var(--text-primary)', fontSize: '12px', fontFamily: 'var(--font-mono)', outline: 'none',
  },
  select: {
    width: '100%', padding: '8px 10px', background: 'var(--bg-input)',
    border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)',
    color: 'var(--text-primary)', fontSize: '12px', fontFamily: 'var(--font-mono)', outline: 'none',
  },
  submitBtn: {
    marginTop: 'var(--space-md)', padding: '12px',
    background: 'linear-gradient(135deg, var(--main) 0%, var(--main-dim) 100%)',
    color: '#fff', border: '1px solid rgba(59, 59, 107, 0.3)',
    borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600,
    fontFamily: 'var(--font-ui)', cursor: 'pointer', width: '100%',
    transition: 'all 0.25s', letterSpacing: '0.5px',
  },
  submitDisabled: {
    background: 'var(--bg-root)', borderColor: 'var(--border-default)',
    color: 'var(--text-tertiary)', cursor: 'not-allowed',
  },
  submitProcessing: { animation: 'pulseGlow 2s ease-in-out infinite' },
}
