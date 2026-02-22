"""設定クラス定義."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ExtractorConfig:
    target_fps: float = 30.0
    max_resolution: int = 1920


@dataclass
class PoseModelConfig:
    model_name: str = "mmpose_hrnet"
    batch_size: int = 32
    device: str = "cpu"


@dataclass
class ProcessingConfig:
    interpolation_method: str = "spline"
    confidence_threshold: float = 0.3
    smoothing_window: int = 5
    joints_to_remove: List[str] = field(default_factory=list)


@dataclass
class Converter3DConfig:
    model_name: str = "videopose3d"
    device: str = "cpu"
    quality_threshold: float = 0.5
