"""メインパイプライン: VideoExtractor → PoseEstimator → DataProcessor → Converter3D.

CLI / Gradio GUI / FastAPI の3つのエントリポイントから共通利用される
単一のパイプライン実装（tasks.md 9.1 の MotionExtractor に対応）。
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

from video_motion_extraction import logger
from video_motion_extraction.config import (
    Converter3DConfig,
    ExtractorConfig,
    PoseModelConfig,
    ProcessingConfig,
)
from video_motion_extraction.converter_3d import Converter3D
from video_motion_extraction.data_processor import DataProcessor
from video_motion_extraction.models import Motion3DData
from video_motion_extraction.pose_estimator import PoseEstimator
from video_motion_extraction.validators import validate_output_path
from video_motion_extraction.video_extractor import VideoExtractor

# 進捗コールバック: (step名, 進捗0.0〜1.0, 表示メッセージ)
ProgressCallback = Callable[[str, float, str], None]


def _strict_default() -> bool:
    """環境変数 VME_STRICT からstrictモードのデフォルト値を決定."""
    return os.environ.get("VME_STRICT", "").lower() in ("1", "true", "yes")


def _device_default() -> str:
    """環境変数 VME_DEVICE からデバイスのデフォルト値を決定."""
    return os.environ.get("VME_DEVICE", "auto")


@dataclass
class PipelineOptions:
    """パイプライン実行オプション."""

    fps: float = 30.0
    threshold: float = 0.3
    smoothing: int = 5
    joints_to_remove: List[str] = field(default_factory=list)
    batch_size: int = 32
    bvh_mode: str = "position"
    smooth_3d: float = 1.0
    root_motion_scale: float = 2.5
    compute_angular_velocity: bool = False
    strict: bool = field(default_factory=_strict_default)
    device: str = field(default_factory=_device_default)


@dataclass
class PipelineResult:
    """パイプライン実行結果."""

    motion_3d: Motion3DData
    angular_velocity: Optional[np.ndarray] = None

    @property
    def quality_score(self) -> Optional[float]:
        return self.motion_3d.quality_score


class MotionExtractor:
    """動画から3Dモーションデータを抽出するメインパイプライン."""

    def __init__(self, options: Optional[PipelineOptions] = None) -> None:
        self._options = options or PipelineOptions()
        self._converter: Optional[Converter3D] = None

    def process(
        self,
        video_path: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> PipelineResult:
        """全コンポーネントを結合してパイプラインを実行.

        Args:
            video_path: 入力動画パス
            on_progress: 進捗通知コールバック（省略可）

        Returns:
            3Dモーションデータと派生データを含む実行結果
        """
        opts = self._options

        def notify(step: str, progress: float, message: str) -> None:
            # コールバック内の例外でパイプライン本体を中断させない
            if on_progress is None:
                return
            try:
                on_progress(step, progress, message)
            except Exception as cb_exc:
                logger.warning(
                    "pipeline.notify",
                    context={"step": step, "error": str(cb_exc)},
                    ai_todo=["fix_progress_callback"],
                )

        logger.step(
            "pipeline.process",
            context={"video_path": video_path, "options": str(opts)},
            ai_todo=["run_full_pipeline"],
        )

        # 1. フレーム抽出
        notify("extracting_frames", 0.05, "Extracting frames...")
        extractor = VideoExtractor(ExtractorConfig(target_fps=opts.fps))
        frames = extractor.extract_frames(video_path, target_fps=opts.fps)
        notify("extracting_frames", 0.25, f"  {len(frames)} frames extracted")

        # 2. 2Dポーズ推定（GPU）
        notify("estimating_poses", 0.25, "Estimating 2D poses...")
        estimator = PoseEstimator(
            PoseModelConfig(
                batch_size=opts.batch_size,
                device=opts.device,
                strict=opts.strict,
            )
        )
        pose_2d = estimator.estimate_2d_pose(
            frames, batch_size=opts.batch_size, fps=opts.fps
        )
        notify(
            "estimating_poses",
            0.50,
            f"  {len(pose_2d.frames)} poses estimated ({len(pose_2d.joint_names)} joints)",
        )

        # 3. データ処理（補間・スムージング・関節削除・角速度）
        notify("processing_data", 0.50, "Processing data...")
        processor = DataProcessor(
            ProcessingConfig(
                confidence_threshold=opts.threshold,
                smoothing_window=opts.smoothing,
                joints_to_remove=opts.joints_to_remove,
            )
        )
        pose_2d = processor.interpolate_missing(pose_2d)
        pose_2d = processor.smooth_trajectory(pose_2d, window_size=opts.smoothing)
        if opts.joints_to_remove:
            pose_2d = processor.remove_joints(pose_2d, opts.joints_to_remove)
            notify(
                "processing_data",
                0.65,
                f"  {len(pose_2d.joint_names)} joints remaining after removal",
            )

        angular_velocity: Optional[np.ndarray] = None
        if opts.compute_angular_velocity:
            angular_velocity = processor.calculate_angular_velocity(pose_2d)
            notify(
                "processing_data",
                0.70,
                f"  angular velocity computed ({angular_velocity.shape[0]} frames)",
            )
        notify("processing_data", 0.75, "  data processing done")

        # 4. 3D変換（GPU）
        notify("converting_3d", 0.75, "Converting to 3D...")
        self._converter = Converter3D(
            Converter3DConfig(
                bvh_mode=opts.bvh_mode,
                smooth_3d_sigma=opts.smooth_3d,
                root_motion_scale=opts.root_motion_scale,
                device=opts.device,
                strict=opts.strict,
            )
        )
        motion_3d = self._converter.convert_to_3d(pose_2d)
        if motion_3d.quality_score is not None:
            notify(
                "converting_3d",
                0.95,
                f"  quality score: {motion_3d.quality_score:.3f}",
            )

        return PipelineResult(motion_3d=motion_3d, angular_velocity=angular_velocity)

    def export(
        self, motion_data: Motion3DData, output_path: str, output_format: str
    ) -> None:
        """モーションデータを指定フォーマットでエクスポート."""
        converter = self._converter or Converter3D(
            Converter3DConfig(
                bvh_mode=self._options.bvh_mode,
                device=self._options.device,
            )
        )
        # パス検証をディレクトリ作成より先に行う（検証前のmkdir副作用を防止）
        validate_output_path(output_path)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        converter.export(motion_data, output_path, output_format)


def export_angular_velocity(
    angular_velocity: np.ndarray, output_path: str, fps: float
) -> None:
    """角速度データをJSONでエクスポート."""
    payload = {
        "fps": fps,
        "unit": "rad/s",
        "shape": list(angular_velocity.shape),
        "values": angular_velocity.tolist(),
    }
    validate_output_path(output_path)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
