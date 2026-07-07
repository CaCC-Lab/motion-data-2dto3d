"""Video Motion Extraction: 動画から人体モーションデータを抽出し2D→3D変換を行うツール."""

from video_motion_extraction.config import (
    Converter3DConfig,
    ExtractorConfig,
    PoseModelConfig,
    ProcessingConfig,
)
from video_motion_extraction.converter_3d import Converter3D
from video_motion_extraction.data_processor import INTERPOLATED_CONFIDENCE, DataProcessor
from video_motion_extraction.errors import (
    GPUMemoryError,
    ModelNotAvailableError,
    ValidationError,
    VideoLoadError,
)
from video_motion_extraction.joint_mapping import (
    COCO_JOINT_NAMES,
    H36M_HIERARCHY,
    H36M_JOINT_NAMES,
    coco_to_h36m_keypoints,
)
from video_motion_extraction.models import (
    BoundingBox,
    Motion3DData,
    Motion3DFrame,
    Pose2DFrame,
    Pose2DSequence,
    VideoMetadata,
)
from video_motion_extraction.pipeline import (
    MotionExtractor,
    PipelineOptions,
    PipelineResult,
)
from video_motion_extraction.pose_estimator import PoseEstimator
from video_motion_extraction.quaternion_utils import (
    normalize_quaternions,
    positions_to_quaternions,
)
from video_motion_extraction.video_extractor import VideoExtractor

__all__ = [
    "BoundingBox",
    "Converter3D",
    "Converter3DConfig",
    "DataProcessor",
    "ExtractorConfig",
    "GPUMemoryError",
    "INTERPOLATED_CONFIDENCE",
    "ModelNotAvailableError",
    "Motion3DData",
    "Motion3DFrame",
    "MotionExtractor",
    "PipelineOptions",
    "PipelineResult",
    "Pose2DFrame",
    "Pose2DSequence",
    "PoseEstimator",
    "PoseModelConfig",
    "ProcessingConfig",
    "ValidationError",
    "VideoExtractor",
    "VideoLoadError",
    "VideoMetadata",
    "COCO_JOINT_NAMES",
    "H36M_HIERARCHY",
    "H36M_JOINT_NAMES",
    "coco_to_h36m_keypoints",
    "normalize_quaternions",
    "positions_to_quaternions",
]
