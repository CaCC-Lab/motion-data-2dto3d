"""統合ワークフローのPydanticモデル."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class GenerateModelRequest(BaseModel):
    """text2image2modelへの3Dモデル生成リクエスト."""

    prompt: str = Field(..., min_length=1, max_length=1000)
    engine_3d: str = "hunyuan3d"
    image_engine: str = "sdxl"
    checkpoint: str = "2-Step"
    mesh_quality: str = "balanced"
    remove_background: bool = True


class ExtractMotionRequest(BaseModel):
    """motion-data-2dto3dへのモーション抽出リクエスト."""

    video_id: str
    fps: float = 30.0
    threshold: float = 0.3
    smoothing: int = 5
    output_format: Literal["bvh"] = "bvh"
    batch_size: int = 32
    bvh_mode: Literal["position"] = "position"
    smooth_3d: float = 1.0
    root_motion_scale: float = 2.5


class RigRequest(BaseModel):
    """GLB→VRM自動リギングリクエスト."""

    glb_path: str
    method: Literal["blender", "mixamo"] = "blender"


class RetargetRequest(BaseModel):
    """BVH→VRMリターゲティングリクエスト."""

    bvh_path: str
    vrm_path: str


class ExportRequest(BaseModel):
    """アニメーション出力リクエスト."""

    blend_path: str
    formats: List[Literal["glb", "blend"]] = ["glb", "blend"]


class WorkflowRequest(BaseModel):
    """統合ワークフロー全体のリクエスト."""

    prompt: str = Field("", max_length=1000)
    glb_file_id: Optional[str] = None  # アップロード済みGLBのID
    video_id: Optional[str] = None
    video_path: Optional[str] = None
    engine_3d: str = "hunyuan3d"
    image_engine: str = "sdxl"
    mesh_quality: str = "balanced"
    motion_fps: float = 30.0


class WorkflowStatus(BaseModel):
    """ワークフローの進捗状態."""

    workflow_id: str
    status: Literal["pending", "generating_model", "extracting_motion", "rigging", "retargeting", "exporting", "completed", "failed"]
    progress: float = 0.0
    current_step: str = ""
    model_glb_url: Optional[str] = None
    vrm_path: Optional[str] = None
    bvh_path: Optional[str] = None
    animation_glb_url: Optional[str] = None
    blend_path: Optional[str] = None
    error: Optional[str] = None
