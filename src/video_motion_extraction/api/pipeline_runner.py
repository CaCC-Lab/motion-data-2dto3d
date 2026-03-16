"""バックグラウンドパイプライン実行 + 進捗管理."""

import tempfile
import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

from video_motion_extraction import logger
from video_motion_extraction.api.schemas import JobStatusResponse
from video_motion_extraction.config import (
    Converter3DConfig,
    ExtractorConfig,
    PoseModelConfig,
    ProcessingConfig,
)
from video_motion_extraction.converter_3d import Converter3D
from video_motion_extraction.data_processor import DataProcessor
from video_motion_extraction.pose_estimator import PoseEstimator
from video_motion_extraction.video_extractor import VideoExtractor

# インメモリジョブストア（単一ユーザー前提）
_jobs: Dict[str, JobStatusResponse] = {}
_jobs_lock = threading.Lock()

# アップロード動画ストア
_videos: Dict[str, Path] = {}


def register_video(video_path: Path) -> str:
    """動画を登録してvideo_idを返す."""
    video_id = uuid.uuid4().hex[:12]
    _videos[video_id] = video_path
    return video_id


def get_video_path(video_id: str) -> Optional[Path]:
    """video_idからパスを取得."""
    return _videos.get(video_id)


def get_job(job_id: str) -> Optional[JobStatusResponse]:
    """ジョブ状態を取得."""
    with _jobs_lock:
        return _jobs.get(job_id)


def _update_job(job_id: str, **kwargs) -> None:
    """ジョブ状態を更新."""
    with _jobs_lock:
        if job_id in _jobs:
            for k, v in kwargs.items():
                setattr(_jobs[job_id], k, v)


def start_processing(
    video_path: str,
    fps: float,
    threshold: float,
    smoothing: int,
    remove_joints: str,
    output_format: str,
    batch_size: int,
    bvh_mode: str,
    smooth_3d: float,
    root_motion_scale: float,
) -> str:
    """パイプラインをバックグラウンドで実行開始し、job_idを返す."""
    job_id = uuid.uuid4().hex[:12]

    with _jobs_lock:
        _jobs[job_id] = JobStatusResponse(
            job_id=job_id,
            status="queued",
            progress=0.0,
            current_step="queued",
            log="",
        )

    thread = threading.Thread(
        target=_run_pipeline,
        args=(
            job_id,
            video_path,
            fps,
            threshold,
            smoothing,
            remove_joints,
            output_format,
            batch_size,
            bvh_mode,
            smooth_3d,
            root_motion_scale,
        ),
        daemon=True,
    )
    thread.start()
    return job_id


def _append_log(job_id: str, message: str) -> None:
    """ログ行を追加."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job.log = job.log + message + "\n" if job.log else message + "\n"


def _run_pipeline(
    job_id: str,
    video_path: str,
    fps: float,
    threshold: float,
    smoothing: int,
    remove_joints: str,
    output_format: str,
    batch_size: int,
    bvh_mode: str,
    smooth_3d: float,
    root_motion_scale: float,
) -> None:
    """パイプライン実行（gui.pyのprocess_videoと同等ロジック）."""
    logger.step("api.pipeline_runner", context={"job_id": job_id, "video_path": video_path}, ai_todo=["run"])

    _update_job(job_id, status="running", current_step="initializing")

    try:
        # メタデータ取得
        extractor_for_meta = VideoExtractor()
        meta = extractor_for_meta.get_video_metadata(video_path)
        _append_log(
            job_id,
            f"=== Video Info ===\n"
            f"Resolution: {meta.width}x{meta.height}\n"
            f"FPS: {meta.fps}\n"
            f"Frames: {meta.total_frames}\n"
            f"Duration: {meta.duration:.2f}s\n"
            f"Codec: {meta.codec}",
        )

        # 1. フレーム抽出 (0% → 25%)
        _update_job(job_id, current_step="extracting_frames", progress=0.05)
        _append_log(job_id, "Extracting frames...")
        extractor = VideoExtractor(ExtractorConfig(target_fps=fps))
        frames = extractor.extract_frames(video_path, target_fps=fps)
        _update_job(job_id, progress=0.25)
        _append_log(job_id, f"  {len(frames)} frames extracted")

        # 2. 2Dポーズ推定 (25% → 50%)
        _update_job(job_id, current_step="estimating_poses", progress=0.25)
        _append_log(job_id, "Estimating 2D poses...")
        estimator = PoseEstimator(PoseModelConfig(batch_size=batch_size))
        pose_2d = estimator.estimate_2d_pose(frames, batch_size=batch_size)
        _update_job(job_id, progress=0.50)
        _append_log(job_id, f"  {len(pose_2d.frames)} poses ({len(pose_2d.joint_names)} joints)")

        # 3. データ処理 (50% → 75%)
        _update_job(job_id, current_step="processing_data", progress=0.50)
        _append_log(job_id, "Processing data...")
        joints_to_remove = [j.strip() for j in remove_joints.split(",") if j.strip()] if remove_joints else []
        processor = DataProcessor(
            ProcessingConfig(
                confidence_threshold=threshold,
                smoothing_window=smoothing,
                joints_to_remove=joints_to_remove,
            )
        )
        pose_2d = processor.interpolate_missing(pose_2d)
        pose_2d = processor.smooth_trajectory(pose_2d, window_size=smoothing)
        if joints_to_remove:
            pose_2d = processor.remove_joints(pose_2d, joints_to_remove)
            _append_log(job_id, f"  {len(pose_2d.joint_names)} joints remaining")
        _update_job(job_id, progress=0.75)

        # 4. 3D変換 & エクスポート (75% → 100%)
        _update_job(job_id, current_step="converting_3d", progress=0.75)
        _append_log(job_id, "Converting to 3D...")
        converter = Converter3D(Converter3DConfig(
            bvh_mode=bvh_mode,
            smooth_3d_sigma=smooth_3d,
            root_motion_scale=root_motion_scale,
        ))
        motion_3d = converter.convert_to_3d(pose_2d)

        suffix = f".{output_format}"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="vme_")
        converter.export(motion_3d, tmp.name, output_format)
        tmp.close()

        _update_job(
            job_id,
            status="completed",
            progress=1.0,
            current_step="done",
            result_file=tmp.name,
        )
        _append_log(job_id, f"Done! Exported as {output_format}")

    except Exception as exc:
        logger.error(
            "api.pipeline_runner",
            what="Pipeline failed",
            why=str(exc),
            how="Check input and parameters",
        )
        _update_job(
            job_id,
            status="failed",
            current_step="error",
            error=str(exc),
        )
        _append_log(job_id, f"\nError: {exc}")
