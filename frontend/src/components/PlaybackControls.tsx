import React from 'react'

interface AnimState {
  duration: number
  currentTime: number
  isPlaying: boolean
  speed: number
}

interface Controls {
  play: () => void
  pause: () => void
  toggle: () => void
  seek: (time: number) => void
  setSpeed: (speed: number) => void
}

interface Props {
  state: AnimState
  controls: Controls
}

const SPEED_OPTIONS = [0.25, 0.5, 1, 2]

export default function PlaybackControls({ state, controls }: Props) {
  if (state.duration === 0) return null

  const formatTime = (t: number) => {
    const s = Math.floor(t)
    const ms = Math.floor((t - s) * 100)
    return `${s}.${ms.toString().padStart(2, '0')}`
  }

  return (
    <div style={styles.container}>
      <button style={styles.playBtn} onClick={controls.toggle}>
        {state.isPlaying ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" rx="1" />
            <rect x="14" y="4" width="4" height="16" rx="1" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="6,4 20,12 6,20" />
          </svg>
        )}
      </button>

      <input
        type="range"
        min={0}
        max={state.duration}
        step={0.01}
        value={state.currentTime}
        onChange={(e) => controls.seek(Number(e.target.value))}
        style={styles.timeline}
      />

      <span style={styles.time}>
        {formatTime(state.currentTime)}
        <span style={styles.timeSep}>/</span>
        {formatTime(state.duration)}
      </span>

      <div style={styles.speedGroup}>
        {SPEED_OPTIONS.map((s) => (
          <button
            key={s}
            style={{
              ...styles.speedBtn,
              ...(state.speed === s ? styles.speedActive : {}),
            }}
            onClick={() => controls.setSpeed(s)}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'absolute',
    bottom: 0, left: 0, right: 0,
    display: 'flex', alignItems: 'center', gap: '10px',
    padding: '10px 16px',
    background: 'rgba(255, 255, 255, 0.92)',
    backdropFilter: 'blur(12px)',
    borderTop: '1px solid var(--border-default)',
  },
  playBtn: {
    width: '32px', height: '32px', borderRadius: '50%',
    border: '1px solid rgba(59, 59, 107, 0.25)',
    background: 'rgba(59, 59, 107, 0.08)',
    color: 'var(--main)', fontSize: '14px', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, transition: 'all 0.2s',
  },
  timeline: { flex: 1 },
  time: {
    fontSize: '11px', color: 'var(--text-secondary)',
    fontFamily: 'var(--font-mono)', fontWeight: 500,
    minWidth: '90px', textAlign: 'right' as const,
  },
  timeSep: {
    color: 'var(--text-tertiary)', margin: '0 2px',
  },
  speedGroup: { display: 'flex', gap: '2px' },
  speedBtn: {
    padding: '3px 7px', fontSize: '10px',
    background: 'transparent', color: 'var(--text-tertiary)',
    border: '1px solid var(--border-default)', borderRadius: '4px',
    cursor: 'pointer', fontFamily: 'var(--font-mono)', fontWeight: 500,
    transition: 'all 0.15s',
  },
  speedActive: {
    background: 'rgba(59, 59, 107, 0.1)',
    color: 'var(--main)',
    borderColor: 'rgba(59, 59, 107, 0.3)',
  },
}
