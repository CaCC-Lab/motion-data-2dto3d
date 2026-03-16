import { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { BVHLoader } from 'three/examples/jsm/loaders/BVHLoader.js'

interface BvhAnimationState {
  duration: number
  currentTime: number
  isPlaying: boolean
  speed: number
}

interface BvhAnimationControls {
  play: () => void
  pause: () => void
  toggle: () => void
  seek: (time: number) => void
  setSpeed: (speed: number) => void
}

export function useBvhAnimation(
  bvhText: string | null,
  sceneRef: React.MutableRefObject<THREE.Scene | null>,
  cameraRef: React.MutableRefObject<THREE.PerspectiveCamera | null>,
) {
  const mixerRef = useRef<THREE.AnimationMixer | null>(null)
  const actionRef = useRef<THREE.AnimationAction | null>(null)
  const clockRef = useRef(new THREE.Clock())
  const skeletonRef = useRef<THREE.SkeletonHelper | null>(null)
  const bonesGroupRef = useRef<THREE.Group | null>(null)
  const frameIdRef = useRef<number>(0)

  const [state, setState] = useState<BvhAnimationState>({
    duration: 0,
    currentTime: 0,
    isPlaying: false,
    speed: 1,
  })
  const isPlayingRef = useRef(false)

  // BVHテキストが変わったらパース＆セットアップ
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene || !bvhText) return

    // 既存のスケルトンをクリア
    if (skeletonRef.current) {
      scene.remove(skeletonRef.current)
      skeletonRef.current = null
    }
    if (bonesGroupRef.current) {
      scene.remove(bonesGroupRef.current)
      bonesGroupRef.current = null
    }
    if (mixerRef.current) {
      mixerRef.current.stopAllAction()
      mixerRef.current = null
    }

    try {
      const loader = new BVHLoader()
      const result = loader.parse(bvhText)

      // ボーンのルートをシーンに追加
      const skeleton = result.skeleton
      const rootBone = skeleton.bones[0]

      const group = new THREE.Group()
      group.add(rootBone)
      scene.add(group)
      bonesGroupRef.current = group

      // スケルトンヘルパー
      const skeletonHelper = new THREE.SkeletonHelper(rootBone)
      ;(skeletonHelper.material as THREE.LineBasicMaterial).linewidth = 2
      ;(skeletonHelper.material as THREE.LineBasicMaterial).color.set('#6366f1')
      scene.add(skeletonHelper)
      skeletonRef.current = skeletonHelper

      // 関節に小球体を追加
      const sphereGeo = new THREE.SphereGeometry(0.02, 8, 8)
      const sphereMat = new THREE.MeshBasicMaterial({ color: '#a5b4fc' })
      skeleton.bones.forEach((bone) => {
        const sphere = new THREE.Mesh(sphereGeo, sphereMat)
        bone.add(sphere)
      })

      // AnimationMixer
      const mixer = new THREE.AnimationMixer(rootBone)
      const clip = result.clip
      const action = mixer.clipAction(clip)
      action.play()

      mixerRef.current = mixer
      actionRef.current = action
      clockRef.current = new THREE.Clock()

      isPlayingRef.current = true
      setState({
        duration: clip.duration,
        currentTime: 0,
        isPlaying: true,
        speed: 1,
      })

      // カメラ自動配置
      if (cameraRef.current) {
        const box = new THREE.Box3().setFromObject(group)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const dist = maxDim * 2.5

        cameraRef.current.position.set(center.x + dist * 0.5, center.y + dist * 0.3, center.z + dist)
        cameraRef.current.lookAt(center)
        cameraRef.current.updateProjectionMatrix()
      }
    } catch (e) {
      console.warn('BVH parse error:', e)
    }
  }, [bvhText, sceneRef, cameraRef])

  // アニメーションループ更新（外部から呼ばれる）
  const update = useCallback(() => {
    if (mixerRef.current && isPlayingRef.current) {
      const delta = clockRef.current.getDelta()
      mixerRef.current.update(delta)

      if (actionRef.current) {
        setState((prev) => ({
          ...prev,
          currentTime: actionRef.current!.time,
        }))
      }
    }
  }, [])

  const controls: BvhAnimationControls = {
    play: useCallback(() => {
      isPlayingRef.current = true
      clockRef.current.start()
      setState((prev) => ({ ...prev, isPlaying: true }))
    }, []),
    pause: useCallback(() => {
      isPlayingRef.current = false
      clockRef.current.stop()
      setState((prev) => ({ ...prev, isPlaying: false }))
    }, []),
    toggle: useCallback(() => {
      setState((prev) => {
        const next = !prev.isPlaying
        isPlayingRef.current = next
        if (next) {
          clockRef.current.start()
        } else {
          clockRef.current.stop()
        }
        return { ...prev, isPlaying: next }
      })
    }, []),
    seek: useCallback((time: number) => {
      if (actionRef.current) {
        actionRef.current.time = time
        mixerRef.current?.update(0)
        setState((prev) => ({ ...prev, currentTime: time }))
      }
    }, []),
    setSpeed: useCallback((speed: number) => {
      if (mixerRef.current) {
        mixerRef.current.timeScale = speed
      }
      setState((prev) => ({ ...prev, speed }))
    }, []),
  }

  return { state, controls, update }
}
