import React from 'react'
import type { ProcessingParams } from '../types'

type Params = Omit<ProcessingParams, 'video_id'>

interface Props {
  params: Params
  onChange: (params: Params) => void
  onSubmit: () => void
  disabled: boolean
  processing: boolean
}

export default function ParameterForm({ params, onChange, onSubmit, disabled, processing }: Props) {
  const set = <K extends keyof Params>(key: K, value: Params[K]) =>
    onChange({ ...params, [key]: value })

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>パラメータ</h3>
      <div style={styles.form}>
        <SliderField label="FPS" value={params.fps} min={1} max={120} step={1} onChange={(v) => set('fps', v)} />
        <SliderField label="信頼度閾値" value={params.threshold} min={0} max={1} step={0.05} onChange={(v) => set('threshold', v)} />
        <SliderField label="スムージング窓" value={params.smoothing} min={1} max={21} step={2} onChange={(v) => set('smoothing', v)} />
        <div style={styles.field}>
          <label style={styles.label}>除外関節</label>
          <input
            style={styles.input}
            type="text"
            value={params.remove_joints}
            onChange={(e) => set('remove_joints', e.target.value)}
            placeholder="left_hand_*,right_hand_*"
          />
        </div>
        <div style={styles.field}>
          <label style={styles.label}>出力フォーマット</label>
          <select
            style={styles.input}
            value={params.output_format}
            onChange={(e) => set('output_format', e.target.value as 'bvh' | 'fbx' | 'json')}
          >
            <option value="bvh">BVH</option>
            <option value="fbx">FBX</option>
            <option value="json">JSON</option>
          </select>
        </div>
        <SliderField label="バッチサイズ" value={params.batch_size} min={1} max={128} step={1} onChange={(v) => set('batch_size', v)} />
        <div style={styles.field}>
          <label style={styles.label}>BVHモード</label>
          <div style={styles.radioGroup}>
            {(['position', 'rotation'] as const).map((mode) => (
              <label key={mode} style={styles.radioLabel}>
                <input
                  type="radio"
                  name="bvh_mode"
                  value={mode}
                  checked={params.bvh_mode === mode}
                  onChange={() => set('bvh_mode', mode)}
                />
                {mode}
              </label>
            ))}
          </div>
        </div>
        <SliderField label="3Dスムージングσ" value={params.smooth_3d} min={0} max={5} step={0.1} onChange={(v) => set('smooth_3d', v)} />
        <SliderField
          label="ルートモーション補正"
          value={params.root_motion_scale}
          min={0.1}
          max={10}
          step={0.1}
          onChange={(v) => set('root_motion_scale', v)}
        />
      </div>
      <button style={{ ...styles.submitBtn, ...(disabled ? styles.btnDisabled : {}) }} onClick={onSubmit} disabled={disabled}>
        {processing ? '処理中...' : '実行'}
      </button>
    </div>
  )
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
}) {
  return (
    <div style={styles.field}>
      <div style={styles.sliderHeader}>
        <label style={styles.label}>{label}</label>
        <span style={styles.value}>{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={styles.slider}
      />
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
  form: { display: 'flex', flexDirection: 'column', gap: '10px' },
  field: {},
  label: { fontSize: '13px', color: '#999', display: 'block', marginBottom: '4px' },
  sliderHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  value: { fontSize: '13px', color: '#6366f1', fontWeight: 600 },
  slider: { width: '100%', accentColor: '#6366f1' },
  input: {
    width: '100%',
    padding: '8px 10px',
    background: '#16161d',
    border: '1px solid #2a2a35',
    borderRadius: '6px',
    color: '#e0e0e0',
    fontSize: '13px',
    outline: 'none',
  },
  radioGroup: { display: 'flex', gap: '16px' },
  radioLabel: { fontSize: '13px', color: '#ccc', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' },
  submitBtn: {
    marginTop: '12px',
    padding: '12px',
    background: '#6366f1',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '15px',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
    transition: 'background 0.2s',
  },
  btnDisabled: {
    background: '#3a3a45',
    color: '#666',
    cursor: 'not-allowed',
  },
}
