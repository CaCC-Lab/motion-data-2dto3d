import React, { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useBvhAnimation } from '../hooks/useBvhAnimation'
import PlaybackControls from './PlaybackControls'

interface Props {
  bvhText: string | null
}

export default function BvhViewer({ bvhText }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const frameIdRef = useRef<number>(0)

  const { state: animState, controls: animControls, update: animUpdate } = useBvhAnimation(
    bvhText,
    sceneRef,
    cameraRef,
  )

  // Three.jsシーン初期化
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0f0f13')
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.01, 1000)
    camera.position.set(0, 1.5, 3)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Controls
    const orbitControls = new OrbitControls(camera, renderer.domElement)
    orbitControls.enableDamping = true
    orbitControls.dampingFactor = 0.1
    orbitControls.target.set(0, 1, 0)
    controlsRef.current = orbitControls

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    scene.add(ambientLight)
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8)
    dirLight.position.set(5, 10, 7)
    scene.add(dirLight)

    // Ground grid
    const grid = new THREE.GridHelper(10, 20, '#2a2a35', '#1a1a22')
    scene.add(grid)

    // Resize handler
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
      renderer.dispose()
      container.removeChild(renderer.domElement)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={styles.wrapper}>
      <div ref={containerRef} style={styles.canvas} />
      {!bvhText && (
        <div style={styles.placeholder}>
          <div style={styles.placeholderIcon}>&#x1F3AD;</div>
          <div>動画を処理するとここに3Dスケルトンが表示されます</div>
          <div style={styles.placeholderHint}>マウスで回転・ズーム・パン操作可能</div>
        </div>
      )}
      {bvhText && <PlaybackControls state={animState} controls={animControls} />}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: 'relative',
    width: '100%',
    height: '100%',
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
    color: '#555',
    fontSize: '14px',
    pointerEvents: 'none',
  },
  placeholderIcon: {
    fontSize: '48px',
    marginBottom: '12px',
  },
  placeholderHint: {
    fontSize: '12px',
    marginTop: '6px',
    color: '#444',
  },
}
