import React, { useRef, useEffect, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { VRMLoaderPlugin } from '@pixiv/three-vrm'

interface Props {
  glbUrl: string | null
}

export default function VrmViewer({ glbUrl }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const mixerRef = useRef<THREE.AnimationMixer | null>(null)
  const clockRef = useRef(new THREE.Clock())
  const modelRef = useRef<THREE.Group | null>(null)
  const animFrameRef = useRef<number>(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const isPlayingRef = useRef(true)
  const [hasAnimation, setHasAnimation] = useState(false)

  // シーン初期化
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#e8e6e0')
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.01,
      100,
    )
    camera.position.set(0, 1.2, 3)
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 0.9, 0)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.update()
    controlsRef.current = controls

    // ライティング
    const ambient = new THREE.AmbientLight(0xcccccc, 0.6)
    scene.add(ambient)
    const mainLight = new THREE.DirectionalLight(0xffffff, 1.2)
    mainLight.position.set(3, 5, 3)
    scene.add(mainLight)
    const fillLight = new THREE.DirectionalLight(0x3b3b6b, 0.3)
    fillLight.position.set(-2, 3, -2)
    scene.add(fillLight)

    // グリッド
    const grid = new THREE.GridHelper(6, 30, '#b0aeb0', '#d0cec8')
    scene.add(grid)

    // 地面
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(6, 6),
      new THREE.MeshStandardMaterial({ color: '#e0ded8', transparent: true, opacity: 0.5 }),
    )
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -0.001
    scene.add(ground)

    // アニメーションループ
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate)
      const delta = clockRef.current.getDelta()
      if (mixerRef.current && isPlayingRef.current) {
        mixerRef.current.update(delta)
      }
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // リサイズ
    const handleResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animFrameRef.current)
      controls.dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  // isPlaying変更時にrefとclockを同期
  useEffect(() => {
    isPlayingRef.current = isPlaying
    if (isPlaying) {
      clockRef.current.start()
    } else {
      clockRef.current.stop()
    }
  }, [isPlaying])

  // GLBモデルのロード
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene || !glbUrl) return

    // 既存モデルを削除
    if (modelRef.current) {
      scene.remove(modelRef.current)
      modelRef.current = null
    }
    mixerRef.current = null

    const loader = new GLTFLoader()
    loader.register((parser) => new VRMLoaderPlugin(parser))

    loader.load(
      glbUrl,
      (gltf) => {
        const model = gltf.scene
        scene.add(model)
        modelRef.current = model

        // VRM/GLBモデルの向き補正（VRM由来モデルは-Z方向を向くため180°回転）
        const vrm = (gltf as any).userData?.vrm
        if (vrm) {
          vrm.scene.rotation.y = Math.PI
        } else {
          model.rotation.y = Math.PI
        }

        // アニメーション
        if (gltf.animations.length > 0) {
          const mixer = new THREE.AnimationMixer(model)
          mixerRef.current = mixer

          // T-Poseを除外し、一番チャンネル数の多いアニメーションを選択
          const candidates = gltf.animations.filter(
            (a) => !a.name.toLowerCase().includes('t-pose')
          )
          const bestClip = candidates.length > 0
            ? candidates.reduce((a, b) => (a.tracks.length >= b.tracks.length ? a : b))
            : gltf.animations[0]

          console.log(`Playing animation: "${bestClip.name}" (${bestClip.tracks.length} tracks, ${bestClip.duration.toFixed(1)}s)`)
          const action = mixer.clipAction(bestClip)
          action.play()
          clockRef.current.start()
          setIsPlaying(true)
          setHasAnimation(true)
        } else {
          setHasAnimation(false)
        }

        // カメラをモデルに合わせる
        const box = new THREE.Box3().setFromObject(model)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)

        if (cameraRef.current && controlsRef.current) {
          controlsRef.current.target.copy(center)
          cameraRef.current.position.set(
            center.x + maxDim * 1.5,
            center.y + maxDim * 0.3,
            center.z + maxDim * 1.5,
          )
          controlsRef.current.update()
        }
      },
      undefined,
      (err) => {
        console.error('GLB load error:', err)
      },
    )
  }, [glbUrl])

  return (
    <div style={styles.wrapper}>
      <div ref={containerRef} style={styles.canvas} />
      {!glbUrl && (
        <div style={styles.placeholderOverlay}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          <p style={styles.placeholderText}>3Dモデルがここに表示されます</p>
          <p style={styles.placeholderSub}>テキストからキャラクター生成 → モーション適用</p>
        </div>
      )}
      {hasAnimation && glbUrl && (
        <div style={styles.controls}>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            style={styles.playBtn}
          >
            {isPlaying ? '⏸' : '▶'}
          </button>
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    width: '100%',
    height: '100%',
    position: 'relative',
  },
  canvas: {
    width: '100%',
    height: '100%',
  },
  placeholderOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--space-md)',
    background: 'linear-gradient(180deg, #e8e6e0 0%, #d0cec8 100%)',
    zIndex: 1,
  },
  placeholderText: {
    fontSize: '14px',
    fontFamily: 'var(--font-ui)',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  placeholderSub: {
    fontSize: '11px',
    fontFamily: 'var(--font-mono)',
    color: 'var(--text-tertiary)',
  },
  controls: {
    position: 'absolute',
    bottom: 'var(--space-lg)',
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    gap: 'var(--space-sm)',
    padding: 'var(--space-sm) var(--space-lg)',
    background: 'rgba(255,255,255,0.85)',
    backdropFilter: 'blur(8px)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-subtle)',
  },
  playBtn: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    border: '1px solid var(--border-default)',
    background: 'var(--bg-surface)',
    cursor: 'pointer',
    fontSize: '14px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
}
