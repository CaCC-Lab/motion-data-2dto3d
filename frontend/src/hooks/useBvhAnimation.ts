import { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'

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

interface ParsedBvh {
  jointNames: string[]
  rootChannels: number
  frameTime: number
  frames: number[][]
}

// H36Mスケルトンの接続関係
const BONE_CONNECTIONS: [string, string][] = [
  ['Hip', 'RHip'], ['RHip', 'RKnee'], ['RKnee', 'RFoot'],
  ['Hip', 'LHip'], ['LHip', 'LKnee'], ['LKnee', 'LFoot'],
  ['Hip', 'Spine'], ['Spine', 'Thorax'],
  ['Thorax', 'Nose'], ['Nose', 'Head'],
  ['Thorax', 'LShoulder'], ['LShoulder', 'LElbow'], ['LElbow', 'LWrist'],
  ['Thorax', 'RShoulder'], ['RShoulder', 'RElbow'], ['RElbow', 'RWrist'],
]

function parseBvhPositionMode(text: string): ParsedBvh {
  const lines = text.split('\n')
  const jointNames: string[] = []
  const rootChannels = 6
  let inMotion = false
  let frameTime = 0.033333
  const frames: number[][] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line === 'MOTION') { inMotion = true; continue }
    if (!inMotion) {
      const rootMatch = line.match(/^ROOT\s+(\S+)/)
      if (rootMatch) { jointNames.push(rootMatch[1]); continue }
      const jointMatch = line.match(/^JOINT\s+(\S+)/)
      if (jointMatch) { jointNames.push(jointMatch[1]); continue }
    } else {
      const ftMatch = line.match(/^Frame Time:\s*([\d.]+)/)
      if (ftMatch) { frameTime = parseFloat(ftMatch[1]); continue }
      if (line.length > 0 && !line.startsWith('Frames:')) {
        const values = line.split(/\s+/).map(Number)
        if (values.length > 0 && !isNaN(values[0])) frames.push(values)
      }
    }
  }
  return { jointNames, rootChannels, frameTime, frames }
}

function getJointPositions(parsed: ParsedBvh, frameIdx: number): Map<string, THREE.Vector3> {
  const positions = new Map<string, THREE.Vector3>()
  const frame = parsed.frames[frameIdx]
  if (!frame) return positions

  const rootX = frame[0], rootY = frame[1], rootZ = frame[2]
  positions.set(parsed.jointNames[0], new THREE.Vector3(rootX, rootY, rootZ))

  for (let j = 1; j < parsed.jointNames.length; j++) {
    const offset = parsed.rootChannels + (j - 1) * 3
    positions.set(
      parsed.jointNames[j],
      new THREE.Vector3(rootX + frame[offset], rootY + frame[offset + 1], rootZ + frame[offset + 2]),
    )
  }
  return positions
}

function updateSceneFrame(
  parsed: ParsedBvh,
  frameIdx: number,
  jointMeshes: Map<string, THREE.Mesh>,
  boneGeo: THREE.BufferGeometry | null,
) {
  const positions = getJointPositions(parsed, frameIdx)
  for (const [name, pos] of positions) {
    const mesh = jointMeshes.get(name)
    if (mesh) mesh.position.copy(pos)
  }
  if (boneGeo) {
    const posAttr = boneGeo.attributes.position as THREE.BufferAttribute
    const arr = posAttr.array as Float32Array
    const validConnections = BONE_CONNECTIONS.filter(
      ([a, b]) => parsed.jointNames.includes(a) && parsed.jointNames.includes(b),
    )
    let li = 0
    for (const [a, b] of validConnections) {
      const pa = positions.get(a), pb = positions.get(b)
      if (pa && pb) {
        arr[li * 6] = pa.x; arr[li * 6 + 1] = pa.y; arr[li * 6 + 2] = pa.z
        arr[li * 6 + 3] = pb.x; arr[li * 6 + 4] = pb.y; arr[li * 6 + 5] = pb.z
      }
      li++
    }
    posAttr.needsUpdate = true
  }
  return positions
}

export function useBvhAnimation(
  bvhText: string | null,
  sceneRef: React.MutableRefObject<THREE.Scene | null>,
  cameraRef: React.MutableRefObject<THREE.PerspectiveCamera | null>,
) {
  const groupRef = useRef<THREE.Group | null>(null)
  const jointMeshesRef = useRef<Map<string, THREE.Mesh>>(new Map())
  const boneLineRef = useRef<THREE.LineSegments | null>(null)
  const boneGeoRef = useRef<THREE.BufferGeometry | null>(null)
  const sphereGeoRef = useRef<THREE.SphereGeometry | null>(null)
  const sphereMatRef = useRef<THREE.MeshBasicMaterial | null>(null)
  const lineMatRef = useRef<THREE.LineBasicMaterial | null>(null)
  const parsedRef = useRef<ParsedBvh | null>(null)
  const currentFrameRef = useRef(0)
  const clockRef = useRef(new THREE.Clock())
  const accumulatorRef = useRef(0)

  const [state, setState] = useState<BvhAnimationState>({
    duration: 0, currentTime: 0, isPlaying: false, speed: 1,
  })
  const isPlayingRef = useRef(false)
  const speedRef = useRef(1)

  const cleanupScene = useCallback(() => {
    const scene = sceneRef.current
    if (boneLineRef.current && scene) { scene.remove(boneLineRef.current); boneLineRef.current = null }
    if (groupRef.current && scene) { scene.remove(groupRef.current); groupRef.current = null }
    boneGeoRef.current?.dispose(); boneGeoRef.current = null
    sphereGeoRef.current?.dispose(); sphereGeoRef.current = null
    sphereMatRef.current?.dispose(); sphereMatRef.current = null
    lineMatRef.current?.dispose(); lineMatRef.current = null
    jointMeshesRef.current.clear()
    parsedRef.current = null
    isPlayingRef.current = false
    currentFrameRef.current = 0
    accumulatorRef.current = 0
  }, [sceneRef])

  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return
    cleanupScene()
    if (!bvhText) {
      setState({ duration: 0, currentTime: 0, isPlaying: false, speed: 1 })
      return
    }

    try {
      const parsed = parseBvhPositionMode(bvhText)
      parsedRef.current = parsed
      if (parsed.frames.length === 0 || parsed.jointNames.length === 0) return

      const group = new THREE.Group()
      scene.add(group)
      groupRef.current = group

      // 関節球体
      const sphereGeo = new THREE.SphereGeometry(0.015, 8, 8)
      const sphereMat = new THREE.MeshBasicMaterial({ color: '#D24848' })
      sphereGeoRef.current = sphereGeo
      sphereMatRef.current = sphereMat

      const meshes = new Map<string, THREE.Mesh>()
      for (const name of parsed.jointNames) {
        const mesh = new THREE.Mesh(sphereGeo, sphereMat)
        group.add(mesh)
        meshes.set(name, mesh)
      }
      jointMeshesRef.current = meshes

      // ボーンライン
      const validConnections = BONE_CONNECTIONS.filter(
        ([a, b]) => parsed.jointNames.includes(a) && parsed.jointNames.includes(b),
      )
      const linePositions = new Float32Array(validConnections.length * 2 * 3)
      const boneGeo = new THREE.BufferGeometry()
      boneGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3))
      boneGeoRef.current = boneGeo

      const lineMat = new THREE.LineBasicMaterial({ color: '#3b3b6b', linewidth: 2 })
      lineMatRef.current = lineMat

      const boneLine = new THREE.LineSegments(boneGeo, lineMat)
      scene.add(boneLine)
      boneLineRef.current = boneLine

      // 初期フレーム描画
      const positions = updateSceneFrame(parsed, 0, meshes, boneGeo)

      const duration = parsed.frames.length * parsed.frameTime

      // カメラ自動配置
      if (cameraRef.current && positions.size > 0) {
        const box = new THREE.Box3()
        for (const p of positions.values()) box.expandByPoint(p)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const dist = maxDim * 2.5
        cameraRef.current.position.set(center.x + dist * 0.5, center.y + dist * 0.3, center.z + dist)
        cameraRef.current.lookAt(center)
        cameraRef.current.updateProjectionMatrix()
      }

      isPlayingRef.current = true
      clockRef.current = new THREE.Clock()
      currentFrameRef.current = 0
      accumulatorRef.current = 0
      setState({ duration, currentTime: 0, isPlaying: true, speed: 1 })
    } catch (e) {
      console.warn('BVH parse error:', e)
    }
  }, [bvhText, sceneRef, cameraRef, cleanupScene])

  const lastTimeRef = useRef(0)
  const update = useCallback(() => {
    const parsed = parsedRef.current
    if (!parsed || !isPlayingRef.current) return

    const delta = clockRef.current.getDelta() * speedRef.current
    accumulatorRef.current += delta

    const totalFrames = parsed.frames.length
    const frameTime = parsed.frameTime
    const duration = totalFrames * frameTime

    let currentTime = currentFrameRef.current * frameTime + accumulatorRef.current
    if (currentTime >= duration) {
      currentTime = currentTime % duration
      currentFrameRef.current = 0
      accumulatorRef.current = currentTime
    }

    const frameIdx = Math.min(Math.floor(currentTime / frameTime), totalFrames - 1)

    if (frameIdx !== currentFrameRef.current) {
      currentFrameRef.current = frameIdx
      accumulatorRef.current = currentTime - frameIdx * frameTime
      updateSceneFrame(parsed, frameIdx, jointMeshesRef.current, boneGeoRef.current)
    }

    if (Math.abs(currentTime - lastTimeRef.current) > 0.01) {
      lastTimeRef.current = currentTime
      setState((prev) => ({ ...prev, currentTime }))
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
        if (next) clockRef.current.start()
        else clockRef.current.stop()
        return { ...prev, isPlaying: next }
      })
    }, []),
    seek: useCallback((time: number) => {
      const parsed = parsedRef.current
      if (!parsed) return
      const frameIdx = Math.min(Math.floor(time / parsed.frameTime), parsed.frames.length - 1)
      currentFrameRef.current = frameIdx
      accumulatorRef.current = 0
      updateSceneFrame(parsed, frameIdx, jointMeshesRef.current, boneGeoRef.current)
      setState((prev) => ({ ...prev, currentTime: time }))
    }, []),
    setSpeed: useCallback((speed: number) => {
      speedRef.current = speed
      setState((prev) => ({ ...prev, speed }))
    }, []),
  }

  return { state, controls, update }
}
