"""データモデル定義."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class VideoMetadata:
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float
    codec: str


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass
class Pose2DFrame:
    frame_id: int
    keypoints: np.ndarray  # (N, 2)
    confidence: np.ndarray  # (N,)
    bounding_box: Optional[BoundingBox]


@dataclass
class Pose2DSequence:
    frames: List[Pose2DFrame]
    joint_names: List[str]
    fps: float


@dataclass
class Motion3DFrame:
    frame_id: int
    positions: np.ndarray  # (N, 3)
    rotations: np.ndarray  # (N, 4) quaternions


@dataclass
class Motion3DData:
    frames: List[Motion3DFrame]
    joint_names: List[str]
    joint_hierarchy: Dict[str, str]
    fps: float
