"""Pydantic request/response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProcessingRequest(BaseModel):
    """パイプライン実行リクエスト."""

    video_id: str
    fps: float = Field(default=30.0, ge=1, le=120)
    threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    smoothing: int = Field(default=5, ge=1, le=21)
    remove_joints: str = ""
    output_format: Literal["bvh", "fbx", "json"] = "bvh"
    batch_size: int = Field(default=32, ge=1, le=128)
    bvh_mode: Literal["position", "rotation"] = "position"
    smooth_3d: float = Field(default=1.0, ge=0.0, le=5.0)
    root_motion_scale: float = Field(default=2.5, ge=0.1, le=10.0)


class UploadResponse(BaseModel):
    """動画アップロードレスポンス."""

    video_id: str
    filename: str


class VideoInfoResponse(BaseModel):
    """動画メタデータレスポンス."""

    video_id: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float
    codec: str


class ProcessResponse(BaseModel):
    """パイプライン実行開始レスポンス."""

    job_id: str


class JobStatusResponse(BaseModel):
    """ジョブ状態レスポンス."""

    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_step: str = ""
    log: str = ""
    result_file: Optional[str] = None
    error: Optional[str] = None
