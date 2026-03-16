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
  frames: number[][]  // frames[frameIdx][valueIdx]
}

// H36Mスケルトンの接続関係（ボーン描画用）
const BONE_CONNECTIONS: [string, string][] = [
  // 右脚
  ['Hip', 'RHip'], ['RHip', 'RKnee'], ['RKnee', 'RFoot'],
  // 左脚
  ['Hip', 'LHip'], ['LHip', 'LKnee'], ['LKnee', 'LFoot'],
  // 胴体
  ['Hip', 'Spine'], ['Spine', 'Thorax'],
  // 頭
  ['Thorax', 'Nose'], ['Nose', 'Head'],
  // 左腕
  ['Thorax', 'LShoulder'], ['LShoulder', 'LElbow'], ['LElbow', 'LWrist'],
  // 右腕
  ['Thorax', 'RShoulder'], ['RShoulder', 'RElbow'], ['RElbow', 'RWrist'],
]

function parseBvhPositionMode(text: string): ParsedBvh {
  const lines = text.split('\n')

  // ヘッダーから関節名を抽出
  const jointNames: string[] = []
  let rootChannels = 6
  let inMotion = false
  let frameTime = 0.033333
  const frames: number[][] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line === 'MOTION') {
      inMotion = true
      continue
    }
    if (!inMotion) {
      // ROOT または JOINT の名前を取得
      const rootMatch = line.match(/^ROOT\s+(\S+)/)
      if (rootMatch) {
        jointNames.push(rootMatch[1])
        continue
      }
      const jointMatch = line.match(/^JOINT\s+(\S+)/)
      if (jointMatch) {
        jointNames.push(jointMatch[1])
        continue
      }
    } else {
      const framesMatch = line.match(/^Frames:\s*(\d+)/)
      if (framesMatch) continue
      const ftMatch = line.match(/^Frame Time:\s*([\d.]+)/)
      if (ftMatch) {
        frameTime = parseFloat(ftMatch[1])
        continue
      }
      // モーションデータ行
      if (line.length > 0) {
        const values = line.split(/\s+/).map(Number)
        if (values.length > 0 && !isNaN(values[0])) {
          frames.push(values)
        }
      }
    }
  }

  return { jointNames, rootChannels, frameTime, frames }
}

function getJointPositions(
  parsed: ParsedBvh,
  frameIdx: number,
): Map<string, THREE.Vector3> {
  const positions = new Map<string, THREE.Vector3>()
  const frame = parsed.frames[frameIdx]
  if (!frame) return positions

  // Root: 最初の3値が位置 (X, Y, Z)
  const rootX = frame[0]
  const rootY = frame[1]
  const rootZ = frame[2]
  positions.set(parsed.jointNames[0], new THREE.Vector3(rootX, rootY, rootZ))

  // 子関節: root channels(6)の後、3値ずつ（Hipからの相対位置）
  for (let j = 1; j < parsed.jointNames.length; j++) {
    const offset = parsed.rootChannels + (j - 1) * 3
    const relX = frame[offset]
    const relY = frame[offset + 1]
    const relZ = frame[offset + 2]
    // 相対位置 + Root位置 = 絶対位置
    positions.set(
      parsed.jointNames[j],
      new THREE.Vector3(rootX + relX, rootY + relY, rootZ + relZ),
    )
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
    duration: 0,
    currentTime: 0,
    isPlaying: false,
    speed: 1,
  })
  const isPlayingRef = useRef(false)
  const speedRef = useRef(1)

  const cleanupScene = useCallback(() => {
    const scene = sceneRef.current
    if (boneLineRef.current && scene) {
      scene.remove(boneLineRef.current)
      boneLineRef.current = null
    }
    if (groupRef.current && scene) {
      scene.remove(groupRef.current)
      groupRef.current = null
    }
    if (boneGeoRef.current) {
      boneGeoRef.current.dispose()
      boneGeoRef.current = null
    }
    if (sphereGeoRef.current) {
      sphereGeoRef.current.dispose()
      sphereGeoRef.current = null
    }
    if (sphereMatRef.current) {
      sphereMatRef.current.dispose()
      sphereMatRef.current = null
    }
    if (lineMatRef.current) {
      lineMatRef.current.dispose()
      lineMatRef.current = null
    }
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

      // 関節球体の作成
      const sphereGeo = new THREE.SphereGeometry(0.015, 8, 8)
      const sphereMat = new THREE.MeshBasicMaterial({ color: '#a5b4fc' })
      sphereGeoRef.current = sphereGeo
      sphereMatRef.current = sphereMat

      const meshes = new Map<string, THREE.Mesh>()
      for (const name of parsed.jointNames) {
        const mesh = new THREE.Mesh(sphereGeo, sphereMat)
        group.add(mesh)
        meshes.set(name, mesh)
      }
      jointMeshesRef.current = meshes

      // ボーンライン用のジオメトリ
      // 有効な接続のみフィルタ
      const validConnections = BONE_CONNECTIONS.filter(
        ([a, b]) => parsed.jointNames.includes(a) && parsed.jointNames.includes(b),
      )
      const linePositions = new Float32Array(validConnections.length * 2 * 3)
      const boneGeo = new THREE.BufferGeometry()
      boneGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3))
      boneGeoRef.current = boneGeo

      const lineMat = new THREE.LineBasicMaterial({ color: '#6366f1', linewidth: 2 })
      lineMatRef.current = lineMat

      const boneLine = new THREE.LineSegments(boneGeo, lineMat)
      scene.add(boneLine)
      boneLineRef.current = boneLine

      // 初期フレームを描画
      const positions = getJointPositions(parsed, 0)
      for (const [name, pos] of positions) {
        const mesh = meshes.get(name)
        if (mesh) mesh.position.copy(pos)
      }

      // ボーンラインの初期位置
      let li = 0
      for (const [a, b] of validConnections) {
        const pa = positions.get(a)
        const pb = positions.get(b)
        if (pa && pb) {
          linePositions[li * 6] = pa.x
          linePositions[li * 6 + 1] = pa.y
          linePositions[li * 6 + 2] = pa.z
          linePositions[li * 6 + 3] = pb.x
          linePositions[li * 6 + 4] = pb.y
          linePositions[li * 6 + 5] = pb.z
        }
        li++
      }
      boneGeo.attributes.position.needsUpdate = true

      const duration = parsed.frames.length * parsed.frameTime

      // カメラ自動配置（初期フレームから）
      if (cameraRef.current) {
        const posArray = Array.from(positions.values())
        const box = new THREE.Box3()
        for (const p of posArray) box.expandByPoint(p)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const dist = maxDim * 2.5

        cameraRef.current.position.set(
          center.x + dist * 0.5,
          center.y + dist * 0.3,
          center.z + dist,
        )
        cameraRef.current.lookAt(center)
        cameraRef.current.updateProjectionMatrix()
      }

      isPlayingRef.current = true
      clockRef.current = new THREE.Clock()
      currentFrameRef.current = 0
      accumulatorRef.current = 0

      setState({
        duration,
        currentTime: 0,
        isPlaying: true,
        speed: 1,
      })
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

    // フレーム進行
    let currentTime = currentFrameRef.current * frameTime + accumulatorRef.current
    if (currentTime >= duration) {
      currentTime = currentTime % duration
      currentFrameRef.current = 0
      accumulatorRef.current = currentTime
    }

    const frameIdx = Math.min(
      Math.floor(currentTime / frameTime),
      totalFrames - 1,
    )

    if (frameIdx !== currentFrameRef.current) {
      currentFrameRef.current = frameIdx
      accumulatorRef.current = currentTime - frameIdx * frameTime

      // 関節位置を更新
      const positions = getJointPositions(parsed, frameIdx)
      for (const [name, pos] of positions) {
        const mesh = jointMeshesRef.current.get(name)
        if (mesh) mesh.position.copy(pos)
      }

      // ボーンラインを更新
      if (boneGeoRef.current) {
        const posAttr = boneGeoRef.current.attributes.position as THREE.BufferAttribute
        const arr = posAttr.array as Float32Array
        const validConnections = BONE_CONNECTIONS.filter(
          ([a, b]) => parsed.jointNames.includes(a) && parsed.jointNames.includes(b),
        )
        let li = 0
        for (const [a, b] of validConnections) {
          const pa = positions.get(a)
          const pb = positions.get(b)
          if (pa && pb) {
            arr[li * 6] = pa.x
            arr[li * 6 + 1] = pa.y
            arr[li * 6 + 2] = pa.z
            arr[li * 6 + 3] = pb.x
            arr[li * 6 + 4] = pb.y
            arr[li * 6 + 5] = pb.z
          }
          li++
        }
        posAttr.needsUpdate = true
      }
    }

    // UIのcurrentTime更新（スロットル）
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
        if (next) {
          clockRef.current.start()
        } else {
          clockRef.current.stop()
        }
        return { ...prev, isPlaying: next }
      })
    }, []),
    seek: useCallback((time: number) => {
      const parsed = parsedRef.current
      if (!parsed) return
      const frameIdx = Math.min(
        Math.floor(time / parsed.frameTime),
        parsed.frames.length - 1,
      )
      currentFrameRef.current = frameIdx
      accumulatorRef.current = 0

      // フレーム描画
      const positions = getJointPositions(parsed, frameIdx)
      for (const [name, pos] of positions) {
        const mesh = jointMeshesRef.current.get(name)
        if (mesh) mesh.position.copy(pos)
      }
      if (boneGeoRef.current) {
        const posAttr = boneGeoRef.current.attributes.position as THREE.BufferAttribute
        const arr = posAttr.array as Float32Array
        const validConnections = BONE_CONNECTIONS.filter(
          ([a, b]) => parsed.jointNames.includes(a) && parsed.jointNames.includes(b),
        )
        let li = 0
        for (const [a, b] of validConnections) {
          const pa = positions.get(a)
          const pb = positions.get(b)
          if (pa && pb) {
            arr[li * 6] = pa.x
            arr[li * 6 + 1] = pa.y
            arr[li * 6 + 2] = pa.z
            arr[li * 6 + 3] = pb.x
            arr[li * 6 + 4] = pb.y
            arr[li * 6 + 5] = pb.z
          }
          li++
        }
        posAttr.needsUpdate = true
      }

      setState((prev) => ({ ...prev, currentTime: time }))
    }, []),
    setSpeed: useCallback((speed: number) => {
      speedRef.current = speed
      setState((prev) => ({ ...prev, speed }))
    }, []),
  }

  return { state, controls, update }
}
