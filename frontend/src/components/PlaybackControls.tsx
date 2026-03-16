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
        {state.isPlaying ? '\u23F8' : '\u25B6'}
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
        {formatTime(state.currentTime)} / {formatTime(state.duration)}
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
    bottom: 0,
    left: 0,
    right: 0,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: 'rgba(15,15,19,0.9)',
    backdropFilter: 'blur(8px)',
    borderTop: '1px solid #2a2a35',
  },
  playBtn: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    border: 'none',
    background: '#6366f1',
    color: '#fff',
    fontSize: '16px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  timeline: {
    flex: 1,
    accentColor: '#6366f1',
  },
  time: {
    fontSize: '12px',
    color: '#888',
    fontFamily: 'monospace',
    minWidth: '90px',
    textAlign: 'right' as const,
  },
  speedGroup: {
    display: 'flex',
    gap: '2px',
  },
  speedBtn: {
    padding: '4px 8px',
    fontSize: '11px',
    background: 'transparent',
    color: '#888',
    border: '1px solid #333',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  speedActive: {
    background: '#6366f1',
    color: '#fff',
    borderColor: '#6366f1',
  },
}
