import type { UploadResponse, VideoInfo, ProcessingParams, JobStatus, HistoryItem, WorkflowStatus } from '../types'

const BASE = '/api'
const INTEGRATION_BASE = import.meta.env.VITE_INTEGRATION_URL || ''

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json()
}

export async function getVideoInfo(videoId: string): Promise<VideoInfo> {
  const res = await fetch(`${BASE}/video/${videoId}/info`)
  if (!res.ok) throw new Error('Failed to get video info')
  return res.json()
}

export async function startProcessing(params: ProcessingParams): Promise<string> {
  const res = await fetch(`${BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to start processing')
  }
  const data = await res.json()
  return data.job_id
}

export function subscribeJobStatus(
  jobId: string,
  onUpdate: (status: JobStatus) => void,
  onError: (err: Error) => void,
): () => void {
  const eventSource = new EventSource(`${BASE}/jobs/${jobId}/status`)

  eventSource.onmessage = (event) => {
    try {
      const data: JobStatus = JSON.parse(event.data)
      onUpdate(data)
      if (data.status === 'completed' || data.status === 'failed') {
        eventSource.close()
      }
    } catch (e) {
      onError(new Error('Failed to parse SSE data'))
      eventSource.close()
    }
  }

  eventSource.onerror = () => {
    onError(new Error('SSE connection lost'))
    eventSource.close()
  }

  return () => eventSource.close()
}

export function getResultDownloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/result`
}

export function getVideoStreamUrl(videoId: string): string {
  return `${BASE}/video/${videoId}/stream`
}

export async function getBvhText(jobId: string): Promise<string> {
  const res = await fetch(`${BASE}/bvh/${jobId}`)
  if (!res.ok) throw new Error('Failed to get BVH data')
  const data = await res.json()
  return data.bvh
}

// === History API ===

export async function getHistoryList(limit = 50, offset = 0): Promise<{ items: HistoryItem[]; total: number }> {
  const res = await fetch(`${BASE}/history?limit=${limit}&offset=${offset}`)
  if (!res.ok) throw new Error('Failed to get history')
  return res.json()
}

export async function deleteHistoryItem(jobId: string): Promise<void> {
  const res = await fetch(`${BASE}/history/${jobId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete history item')
}

export async function getHistoryBvhText(jobId: string): Promise<string> {
  const res = await fetch(`${BASE}/history/${jobId}/bvh`)
  if (!res.ok) throw new Error('Failed to get history BVH data')
  const data = await res.json()
  return data.bvh
}

export function getHistoryThumbnailUrl(jobId: string): string {
  return `${BASE}/history/${jobId}/thumbnail`
}

// === Integration Workflow API ===

export async function uploadGlb(file: File): Promise<{ glb_id: string; filename: string }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${INTEGRATION_BASE}/api/integration/upload-glb`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'GLB upload failed')
  }
  return res.json()
}

export async function startWorkflow(params: {
  prompt?: string
  glb_file_id?: string
  video_id?: string
  video_path?: string
  engine_3d?: string
  image_engine?: string
  mesh_quality?: string
  motion_fps?: number
}): Promise<string> {
  const res = await fetch(`${INTEGRATION_BASE}/api/integration/workflow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to start workflow')
  }
  const data = await res.json()
  return data.workflow_id
}

export function subscribeWorkflowStatus(
  workflowId: string,
  onUpdate: (status: WorkflowStatus) => void,
  onError: (err: Error) => void,
): () => void {
  const eventSource = new EventSource(
    `${INTEGRATION_BASE}/api/integration/workflow/${workflowId}/status`
  )

  eventSource.onmessage = (event) => {
    try {
      const data: WorkflowStatus = JSON.parse(event.data)
      onUpdate(data)
      if (data.status === 'completed' || data.status === 'failed') {
        eventSource.close()
      }
    } catch {
      onError(new Error('Failed to parse SSE data'))
      eventSource.close()
    }
  }

  eventSource.onerror = () => {
    onError(new Error('SSE connection lost'))
    eventSource.close()
  }

  return () => eventSource.close()
}

export function getIntegrationFileUrl(filename: string): string {
  return `${INTEGRATION_BASE}/api/integration/files/${filename}`
}

export async function checkIntegrationHealth(): Promise<boolean> {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 3000)
    const res = await fetch(`${INTEGRATION_BASE}/api/integration/health`, {
      signal: controller.signal,
      mode: 'cors',
    })
    clearTimeout(timer)
    return res.ok
  } catch {
    return false
  }
}
