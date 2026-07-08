"""データモデル定義."""

from dataclasses import dataclass
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

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"width/height must be positive: {self.width}x{self.height}"
            )
        if self.fps <= 0:
            raise ValueError(f"fps must be positive: {self.fps}")
        if self.total_frames < 1:
            raise ValueError(f"total_frames must be >= 1: {self.total_frames}")


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError(
                f"BoundingBox size must be non-negative: {self.width}x{self.height}"
            )


@dataclass
class Pose2DFrame:
    frame_id: int
    keypoints: np.ndarray  # (N, 2)
    confidence: np.ndarray  # (N,)
    bounding_box: Optional[BoundingBox]

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            raise ValueError(f"frame_id must be >= 0: {self.frame_id}")
        if self.keypoints.ndim != 2 or self.keypoints.shape[1] != 2:
            raise ValueError(
                f"keypoints must have shape (N, 2): {self.keypoints.shape}"
            )
        if self.confidence.shape != (self.keypoints.shape[0],):
            raise ValueError(
                "confidence length must match keypoints count: "
                f"{self.confidence.shape} vs {self.keypoints.shape}"
            )
        if self.confidence.size > 0 and (
            np.min(self.confidence) < 0.0 or np.max(self.confidence) > 1.0
        ):
            raise ValueError("confidence values must be within [0, 1]")


@dataclass
class Pose2DSequence:
    frames: List[Pose2DFrame]
    joint_names: List[str]
    fps: float

    def __post_init__(self) -> None:
        if self.fps <= 0:
            raise ValueError(f"fps must be positive: {self.fps}")
        num_joints = len(self.joint_names)
        for frame in self.frames:
            if frame.keypoints.shape[0] != num_joints:
                raise ValueError(
                    "keypoints count must match joint_names length: "
                    f"{frame.keypoints.shape[0]} vs {num_joints}"
                )


@dataclass
class Motion3DFrame:
    frame_id: int
    positions: np.ndarray  # (N, 3)
    rotations: np.ndarray  # (N, 4) quaternions

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            raise ValueError(f"frame_id must be >= 0: {self.frame_id}")
        if self.positions.ndim != 2 or self.positions.shape[1] != 3:
            raise ValueError(
                f"positions must have shape (N, 3): {self.positions.shape}"
            )
        if self.rotations.shape != (self.positions.shape[0], 4):
            raise ValueError(
                "rotations must have shape (N, 4) matching positions: "
                f"{self.rotations.shape} vs {self.positions.shape}"
            )


@dataclass
class Motion3DData:
    frames: List[Motion3DFrame]
    joint_names: List[str]
    joint_hierarchy: Dict[str, str]
    fps: float
    quality_score: Optional[float] = None

    def __post_init__(self) -> None:
        if self.fps <= 0:
            raise ValueError(f"fps must be positive: {self.fps}")
        num_joints = len(self.joint_names)
        for frame in self.frames:
            if frame.positions.shape[0] != num_joints:
                raise ValueError(
                    "positions count must match joint_names length: "
                    f"{frame.positions.shape[0]} vs {num_joints}"
                )
