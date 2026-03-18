"""バックグラウンドパイプライン実行 + 進捗管理."""

import json
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import cv2

from video_motion_extraction import logger
from video_motion_extraction.api.history_db import save_history
from video_motion_extraction.api.history_schemas import HistoryEntry
from video_motion_extraction.api.schemas import JobStatusResponse, ProcessingRequest
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
_job_timestamps: Dict[str, float] = {}  # job_id → 完了時刻
_jobs_lock = threading.Lock()

# アップロード動画ストア: video_id → video_path
_videos: Dict[str, Path] = {}
_video_timestamps: Dict[str, float] = {}  # video_id → 登録時刻

# 完了ジョブの保持時間（秒）
JOB_TTL = 3600  # 1時間
VIDEO_TTL = 7200  # 2時間（ジョブTTLより長めに設定）

# 履歴ディレクトリ
_history_base = Path("data/history")
_history_bvh_dir = _history_base / "bvh"
_history_thumb_dir = _history_base / "thumbnails"
_history_db_path = str(_history_base / "history.db")


def register_video(video_path: Path) -> str:
    """動画を登録してvideo_idを返す."""
    video_id = uuid.uuid4().hex[:12]
    _videos[video_id] = video_path
    _video_timestamps[video_id] = time.time()
    return video_id


def get_video_path(video_id: str) -> Optional[Path]:
    """video_idからパスを取得."""
    return _videos.get(video_id)


def get_job(job_id: str) -> Optional[JobStatusResponse]:
    """ジョブ状態のスナップショットを取得（ロック内でコピー）."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return job.model_copy()


def _cleanup_expired_jobs() -> None:
    """TTL超過の完了/失敗ジョブを削除（成果物ファイルも削除）."""
    now = time.time()
    files_to_delete: List[Path] = []

    with _jobs_lock:
        expired = [
            jid for jid, ts in _job_timestamps.items()
            if now - ts > JOB_TTL
        ]
        for jid in expired:
            job = _jobs.pop(jid, None)
            _job_timestamps.pop(jid, None)
            # 成果物ファイルのパスを収集（ロック外で削除）
            if job and job.result_file:
                files_to_delete.append(Path(job.result_file))

    # ファイルI/Oはロック外で実行
    for f in files_to_delete:
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass

    # TTL超過のアップロード動画も削除
    expired_videos = [
        vid for vid, ts in _video_timestamps.items()
        if now - ts > VIDEO_TTL
    ]
    for vid in expired_videos:
        video_path = _videos.pop(vid, None)
        _video_timestamps.pop(vid, None)
        if video_path:
            try:
                video_path.unlink(missing_ok=True)
            except OSError:
                pass


def _update_job(job_id: str, **kwargs) -> None:
    """ジョブ状態を更新."""
    with _jobs_lock:
        if job_id in _jobs:
            for k, v in kwargs.items():
                setattr(_jobs[job_id], k, v)


def _append_log(job_id: str, message: str) -> None:
    """ログ行を追加."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job.log = job.log + message + "\n" if job.log else message + "\n"


def _record_completion(job_id: str) -> None:
    """ジョブ完了時刻を記録."""
    with _jobs_lock:
        _job_timestamps[job_id] = time.time()


def start_processing(
    video_path: str,
    request: ProcessingRequest,
    filename: str = "",
) -> str:
    """パイプラインをバックグラウンドで実行開始し、job_idを返す."""
    _cleanup_expired_jobs()
    job_id = uuid.uuid4().hex[:12]

    with _jobs_lock:
        _jobs[job_id] = JobStatusResponse(
            job_id=job_id,
            status="queued",
            progress=0.0,
            current_step="queued",
            log="",
            output_format=request.output_format,
        )

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, video_path, request, filename),
        daemon=True,
    )
    thread.start()
    return job_id


def _generate_thumbnail(video_path: str, output_path: Path) -> bool:
    """動画の最初のフレームからサムネイルを生成."""
    try:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return False
        h, w = frame.shape[:2]
        target_w = 320
        target_h = int(h * target_w / w)
        thumb = cv2.resize(frame, (target_w, target_h))
        cv2.imwrite(str(output_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return True
    except Exception:
        return False


def _save_to_history(
    job_id: str,
    video_path: str,
    filename: str,
    req: ProcessingRequest,
    result_file: str,
    meta_width: Optional[int],
    meta_height: Optional[int],
    meta_fps: Optional[float],
    meta_duration: Optional[float],
    log_text: str,
) -> None:
    """処理結果を履歴に保存."""
    try:
        _history_bvh_dir.mkdir(parents=True, exist_ok=True)
        _history_thumb_dir.mkdir(parents=True, exist_ok=True)

        # BVHファイルをコピー
        result_path = Path(result_file)
        bvh_dest = _history_bvh_dir / f"{job_id}{result_path.suffix}"
        shutil.copy2(result_file, bvh_dest)

        # サムネイル生成
        thumb_path = _history_thumb_dir / f"{job_id}.jpg"
        thumb_ok = _generate_thumbnail(video_path, thumb_path)

        # パラメータJSON
        params = {
            "fps": req.fps,
            "threshold": req.threshold,
            "smoothing": req.smoothing,
            "remove_joints": req.remove_joints,
            "output_format": req.output_format,
            "batch_size": req.batch_size,
            "bvh_mode": req.bvh_mode,
            "smooth_3d": req.smooth_3d,
            "root_motion_scale": req.root_motion_scale,
        }

        entry = HistoryEntry(
            job_id=job_id,
            filename=filename or Path(video_path).name,
            thumbnail_path=str(thumb_path.relative_to(_history_base)) if thumb_ok else None,
            bvh_path=str(bvh_dest.relative_to(_history_base)),
            output_format=req.output_format,
            video_width=meta_width,
            video_height=meta_height,
            video_fps=meta_fps,
            video_duration=meta_duration,
            params_json=json.dumps(params),
            status="completed",
            processing_log=log_text,
        )
        save_history(_history_db_path, entry)
    except Exception as exc:
        logger.warning(
            "api.history",
            context={"job_id": job_id, "error": str(exc)},
            ai_todo=["investigate history save failure"],
        )


def _run_pipeline(
    job_id: str,
    video_path: str,
    req: ProcessingRequest,
    filename: str = "",
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
        extractor = VideoExtractor(ExtractorConfig(target_fps=req.fps))
        frames = extractor.extract_frames(video_path, target_fps=req.fps)
        _update_job(job_id, progress=0.25)
        _append_log(job_id, f"  {len(frames)} frames extracted")

        # 2. 2Dポーズ推定 (25% → 50%)
        _update_job(job_id, current_step="estimating_poses", progress=0.25)
        _append_log(job_id, "Estimating 2D poses...")
        estimator = PoseEstimator(PoseModelConfig(batch_size=req.batch_size))
        pose_2d = estimator.estimate_2d_pose(frames, batch_size=req.batch_size)
        _update_job(job_id, progress=0.50)
        _append_log(job_id, f"  {len(pose_2d.frames)} poses ({len(pose_2d.joint_names)} joints)")

        # 3. データ処理 (50% → 75%)
        _update_job(job_id, current_step="processing_data", progress=0.50)
        _append_log(job_id, "Processing data...")
        joints_to_remove = (
            [j.strip() for j in req.remove_joints.split(",") if j.strip()]
            if req.remove_joints
            else []
        )
        processor = DataProcessor(
            ProcessingConfig(
                confidence_threshold=req.threshold,
                smoothing_window=req.smoothing,
                joints_to_remove=joints_to_remove,
            )
        )
        pose_2d = processor.interpolate_missing(pose_2d)
        pose_2d = processor.smooth_trajectory(pose_2d, window_size=req.smoothing)
        if joints_to_remove:
            pose_2d = processor.remove_joints(pose_2d, joints_to_remove)
            _append_log(job_id, f"  {len(pose_2d.joint_names)} joints remaining")
        _update_job(job_id, progress=0.75)

        # 4. 3D変換 & エクスポート (75% → 100%)
        _update_job(job_id, current_step="converting_3d", progress=0.75)
        _append_log(job_id, "Converting to 3D...")
        converter = Converter3D(Converter3DConfig(
            bvh_mode=req.bvh_mode,
            smooth_3d_sigma=req.smooth_3d,
            root_motion_scale=req.root_motion_scale,
        ))
        motion_3d = converter.convert_to_3d(pose_2d)

        suffix = f".{req.output_format}"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="vme_")
        converter.export(motion_3d, tmp.name, req.output_format)
        tmp.close()

        _update_job(
            job_id,
            status="completed",
            progress=1.0,
            current_step="done",
            result_file=tmp.name,
        )
        _append_log(job_id, f"Done! Exported as {req.output_format}")
        _record_completion(job_id)

        # 履歴に保存
        job_snapshot = get_job(job_id)
        _save_to_history(
            job_id=job_id,
            video_path=video_path,
            filename=filename,
            req=req,
            result_file=tmp.name,
            meta_width=meta.width,
            meta_height=meta.height,
            meta_fps=meta.fps,
            meta_duration=meta.duration,
            log_text=job_snapshot.log if job_snapshot else "",
        )

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
        _record_completion(job_id)
