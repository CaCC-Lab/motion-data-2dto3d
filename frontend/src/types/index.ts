export interface UploadResponse {
  video_id: string
  filename: string
}

export interface VideoInfo {
  video_id: string
  width: number
  height: number
  fps: number
  total_frames: number
  duration: number
  codec: string
}

export interface ProcessingParams {
  video_id: string
  fps: number
  threshold: number
  smoothing: number
  remove_joints: string
  output_format: 'bvh' | 'fbx' | 'json'
  batch_size: number
  bvh_mode: 'position' | 'rotation'
  smooth_3d: number
  root_motion_scale: number
}

export interface JobStatus {
  job_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress: number
  current_step: string
  log: string
  output_format: 'bvh' | 'fbx' | 'json' | null
  error: string | null
}

export interface HistoryItem {
  id: number
  job_id: string
  created_at: string
  filename: string
  thumbnail_path: string | null
  bvh_path: string | null
  output_format: string
  video_width: number | null
  video_height: number | null
  video_fps: number | null
  video_duration: number | null
  params_json: string
  status: string
  processing_log: string | null
}

export type AppState = 'idle' | 'uploading' | 'processing' | 'complete' | 'error'
