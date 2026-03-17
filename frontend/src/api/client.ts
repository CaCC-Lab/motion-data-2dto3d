import type { UploadResponse, VideoInfo, ProcessingParams, JobStatus } from '../types'

const BASE = '/api'

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
