import React, { useEffect, useRef, useCallback, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useBvhAnimation } from '../hooks/useBvhAnimation'
import PlaybackControls from './PlaybackControls'
import { getVideoStreamUrl } from '../api/client'

interface Props {
  bvhText: string | null
  videoId: string | null
}

export default function BvhViewer({ bvhText, videoId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const frameIdRef = useRef<number>(0)
  const videoRef = useRef<HTMLVideoElement>(null)

  const [showPip, setShowPip] = useState(true)

  const { state: animState, controls: animControls, update: animUpdate } = useBvhAnimation(
    bvhText,
    sceneRef,
    cameraRef,
  )

  // 動画の再生/一時停止をアニメーションに同期
  const prevPlayingRef = useRef(false)
  useEffect(() => {
    const video = videoRef.current
    if (!video || !bvhText) return
    if (animState.isPlaying && !prevPlayingRef.current) {
      video.play().catch(() => {})
    } else if (!animState.isPlaying && prevPlayingRef.current) {
      video.pause()
    }
    prevPlayingRef.current = animState.isPlaying
  }, [animState.isPlaying, bvhText])

  // シーク同期
  const prevTimeRef = useRef(0)
  useEffect(() => {
    const video = videoRef.current
    if (!video || !bvhText) return
    if (Math.abs(animState.currentTime - prevTimeRef.current) > 0.1) {
      video.currentTime = animState.currentTime
    }
    prevTimeRef.current = animState.currentTime
  }, [animState.currentTime, bvhText])

  // 速度同期
  useEffect(() => {
    const video = videoRef.current
    if (video) video.playbackRate = animState.speed
  }, [animState.speed])

  // Three.jsシーン初期化
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    sceneRef.current = scene

    // ライトモード背景（明るいグレーのグラデーション）
    const canvas = document.createElement('canvas')
    canvas.width = 2
    canvas.height = 256
    const ctx = canvas.getContext('2d')!
    const grad = ctx.createLinearGradient(0, 0, 0, 256)
    grad.addColorStop(0, '#e8e6e0')
    grad.addColorStop(0.5, '#dddbd5')
    grad.addColorStop(1, '#d0cec8')
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, 2, 256)
    const bgTexture = new THREE.CanvasTexture(canvas)
    bgTexture.mapping = THREE.EquirectangularReflectionMapping
    scene.background = bgTexture

    // Camera
    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.01, 1000)
    camera.position.set(0, 1.5, 3)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.4
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Controls
    const orbitControls = new OrbitControls(camera, renderer.domElement)
    orbitControls.enableDamping = true
    orbitControls.dampingFactor = 0.1
    orbitControls.target.set(0, 1, 0)
    controlsRef.current = orbitControls

    // Lights — 明るい自然光 + メインカラーのフィルライト
    const ambientLight = new THREE.AmbientLight(0xcccccc, 0.6)
    scene.add(ambientLight)
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2)
    dirLight.position.set(5, 10, 7)
    scene.add(dirLight)
    const fillLight = new THREE.DirectionalLight(0x3b3b6b, 0.3)
    fillLight.position.set(-5, 3, -5)
    scene.add(fillLight)

    // グラウンドグリッド（明るい色調）
    const grid = new THREE.GridHelper(10, 20, '#b0aeb0', '#c8c6c0')
    grid.material.transparent = true
    grid.material.opacity = 0.5
    scene.add(grid)

    // グラウンドプレーン
    const groundGeo = new THREE.PlaneGeometry(10, 10)
    const groundMat = new THREE.MeshStandardMaterial({
      color: '#c8c6c0',
      metalness: 0.05,
      roughness: 0.9,
      transparent: true,
      opacity: 0.3,
    })
    const ground = new THREE.Mesh(groundGeo, groundMat)
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -0.001
    scene.add(ground)

    // Resize
    const onResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    // Animation loop
    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate)
      animUpdate()
      orbitControls.update()
      renderer.render(scene, camera)
    }
    animate()

    return () => {
      window.removeEventListener('resize', onResize)
      cancelAnimationFrame(frameIdRef.current)
      orbitControls.dispose()
      renderer.dispose()
      bgTexture.dispose()
      groundGeo.dispose()
      groundMat.dispose()
      container.removeChild(renderer.domElement)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const hasVideo = bvhText && videoId

  return (
    <div style={styles.wrapper}>
      {/* 3Dビューワー（常に全画面） */}
      <div style={{ ...styles.viewerArea, height: '100%' }}>
        <div ref={containerRef} style={styles.canvas} />
        {!bvhText && (
          <div style={styles.placeholder}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#3b3b6b', marginBottom: '16px', opacity: 0.4 }}>
              <circle cx="12" cy="5" r="2" />
              <line x1="12" y1="7" x2="12" y2="15" />
              <line x1="12" y1="10" x2="8" y2="13" />
              <line x1="12" y1="10" x2="16" y2="13" />
              <line x1="12" y1="15" x2="9" y2="20" />
              <line x1="12" y1="15" x2="15" y2="20" />
            </svg>
            <div style={styles.placeholderTitle}>3D Skeleton Viewer</div>
            <div style={styles.placeholderHint}>動画を処理するとここにモーションが表示されます</div>
          </div>
        )}
        {bvhText && (
          <div style={styles.viewerBadge}>
            <span style={styles.viewerBadgeDot} />
            3D Motion
          </div>
        )}

        {/* PiPトグルボタン */}
        {hasVideo && (
          <button
            onClick={() => setShowPip(prev => !prev)}
            style={{
              ...styles.pipToggle,
              ...(showPip ? styles.pipToggleActive : styles.pipToggleInactive),
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <rect x="12" y="9" width="8" height="6" rx="1" fill={showPip ? 'currentColor' : 'none'} />
            </svg>
            Video
          </button>
        )}

        {/* PiPビデオオーバーレイ（非表示時もDOMに残して同期維持） */}
        {hasVideo && (
          <div style={{
            ...styles.pipContainer,
            display: showPip ? 'block' : 'none',
          }}>
            <video
              ref={videoRef}
              src={getVideoStreamUrl(videoId)}
              style={styles.pipVideo}
              muted
              playsInline
              loop
            />
          </div>
        )}
      </div>

      {/* 再生コントロール（一番下に配置） */}
      {bvhText && <PlaybackControls state={animState} controls={animControls} />}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: 'relative',
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg-root)',
  },
  viewerArea: {
    position: 'relative',
    width: '100%',
    flexShrink: 0,
  },
  canvas: {
    width: '100%',
    height: '100%',
  },
  placeholder: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    textAlign: 'center' as const,
    color: 'var(--text-tertiary)',
    pointerEvents: 'none',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  placeholderTitle: {
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-secondary)',
    letterSpacing: '1px',
    textTransform: 'uppercase' as const,
  },
  placeholderHint: {
    fontSize: '11px',
    marginTop: '8px',
    color: 'var(--text-tertiary)',
    fontFamily: 'var(--font-ui)',
  },
  viewerBadge: {
    position: 'absolute',
    top: '12px',
    right: '12px',
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    color: 'var(--main)',
    background: 'rgba(255, 255, 255, 0.85)',
    backdropFilter: 'blur(8px)',
    padding: '4px 10px',
    borderRadius: '12px',
    border: '1px solid rgba(59, 59, 107, 0.2)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    letterSpacing: '0.5px',
    textTransform: 'uppercase' as const,
    zIndex: 1,
  },
  viewerBadgeDot: {
    width: '5px',
    height: '5px',
    borderRadius: '50%',
    background: 'var(--main)',
    boxShadow: '0 0 4px rgba(59, 59, 107, 0.4)',
    display: 'inline-block',
  },
  pipToggle: {
    position: 'absolute',
    top: '12px',
    left: '12px',
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    padding: '4px 10px',
    borderRadius: '12px',
    border: '1px solid rgba(59, 59, 107, 0.2)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    letterSpacing: '0.5px',
    textTransform: 'uppercase' as const,
    zIndex: 2,
    transition: 'all 0.2s ease',
    outline: 'none',
  } as React.CSSProperties,
  pipToggleActive: {
    color: 'var(--main)',
    background: 'rgba(255, 255, 255, 0.9)',
    backdropFilter: 'blur(8px)',
  } as React.CSSProperties,
  pipToggleInactive: {
    color: 'var(--text-tertiary)',
    background: 'rgba(255, 255, 255, 0.5)',
    backdropFilter: 'blur(8px)',
    opacity: 0.7,
  } as React.CSSProperties,
  pipContainer: {
    position: 'absolute',
    bottom: '56px',
    right: '16px',
    width: '240px',
    borderRadius: 'var(--radius-md, 8px)',
    boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
    zIndex: 2,
  } as React.CSSProperties,
  pipVideo: {
    width: '100%',
    height: 'auto',
    display: 'block',
  } as React.CSSProperties,
}
