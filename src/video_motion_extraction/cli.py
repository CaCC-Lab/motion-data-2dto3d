"""CLI エントリポイント（click使用）."""

import sys
from pathlib import Path
from typing import Optional

import click

from video_motion_extraction import logger
from video_motion_extraction.config import (
    Converter3DConfig,
    ExtractorConfig,
    PoseModelConfig,
    ProcessingConfig,
)
from video_motion_extraction.converter_3d import Converter3D
from video_motion_extraction.data_processor import DataProcessor
from video_motion_extraction.errors import GPUMemoryError, ValidationError, VideoLoadError
from video_motion_extraction.pose_estimator import PoseEstimator
from video_motion_extraction.video_extractor import VideoExtractor

FORMAT_EXTENSIONS = {".bvh": "bvh", ".fbx": "fbx", ".json": "json"}
SUPPORTED_FORMATS = ("bvh", "fbx", "json")


def _detect_format(output_path: str) -> str:
    """出力パスの拡張子からフォーマットを自動判定."""
    ext = Path(output_path).suffix.lower()
    fmt = FORMAT_EXTENSIONS.get(ext)
    if fmt is None:
        raise click.BadParameter(
            f"Cannot detect format from extension '{ext}'. "
            f"Use --format to specify one of: {', '.join(SUPPORTED_FORMATS)}"
        )
    return fmt


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("-o", "--output", "output_path", type=click.Path(), default=None, help="出力ファイルパス")
@click.option(
    "-f", "--format", "output_format",
    type=click.Choice(SUPPORTED_FORMATS, case_sensitive=False),
    default=None,
    help="出力フォーマット (デフォルト: 拡張子から自動判定)",
)
@click.option("--fps", type=float, default=30.0, show_default=True, help="ターゲットFPS")
@click.option("--threshold", type=float, default=0.3, show_default=True, help="信頼度閾値")
@click.option("--smoothing", type=int, default=5, show_default=True, help="スムージング窓サイズ")
@click.option("--remove-joints", type=str, default=None, help="除外する関節パターン (カンマ区切り)")
@click.option("--batch-size", type=int, default=32, show_default=True, help="GPU バッチサイズ")
@click.option(
    "--bvh-mode", type=click.Choice(["position", "rotation"]),
    default="position", show_default=True, help="BVH出力モード",
)
@click.option("--smooth-3d", type=float, default=1.0, show_default=True, help="3Dスムージングσ (0=無効)")
@click.option("--info", is_flag=True, default=False, help="動画メタデータのみ表示して終了")
def main(
    video_path: str,
    output_path: Optional[str],
    output_format: Optional[str],
    fps: float,
    threshold: float,
    smoothing: int,
    remove_joints: Optional[str],
    batch_size: int,
    bvh_mode: str,
    smooth_3d: float,
    info: bool,
) -> None:
    """動画から3Dモーションデータを抽出する.

    VIDEO_PATH: 入力動画ファイルのパス
    """
    logger.step("cli.main", context={"video_path": video_path, "info": info}, ai_todo=["parse_args", "run_pipeline"])

    extractor = VideoExtractor(ExtractorConfig(target_fps=fps))

    if info:
        _show_info(extractor, video_path)
        return

    if output_path is None:
        raise click.UsageError("--output / -o は必須です (--info を使う場合を除く)")

    fmt = output_format or _detect_format(output_path)

    joints_to_remove = [j.strip() for j in remove_joints.split(",") if j.strip()] if remove_joints else []

    try:
        _run_pipeline(
            video_path=video_path,
            output_path=output_path,
            fmt=fmt,
            fps=fps,
            threshold=threshold,
            smoothing=smoothing,
            joints_to_remove=joints_to_remove,
            batch_size=batch_size,
            bvh_mode=bvh_mode,
            smooth_3d=smooth_3d,
        )
    except (ValidationError, VideoLoadError) as exc:
        logger.error("cli.main", what="Input error", why=str(exc), how="Check input file and parameters")
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except GPUMemoryError as exc:
        logger.error("cli.main", what="GPU memory error", why=str(exc), how="Reduce --batch-size")
        click.echo(f"GPU Error: {exc}", err=True)
        sys.exit(2)


def _show_info(extractor: VideoExtractor, video_path: str) -> None:
    """動画メタデータを表示."""
    try:
        meta = extractor.get_video_metadata(video_path)
    except (ValidationError, VideoLoadError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"File:       {video_path}")
    click.echo(f"Resolution: {meta.width}x{meta.height}")
    click.echo(f"FPS:        {meta.fps}")
    click.echo(f"Frames:     {meta.total_frames}")
    click.echo(f"Duration:   {meta.duration:.2f}s")
    click.echo(f"Codec:      {meta.codec}")


def _run_pipeline(
    *,
    video_path: str,
    output_path: str,
    fmt: str,
    fps: float,
    threshold: float,
    smoothing: int,
    joints_to_remove: list,
    batch_size: int,
    bvh_mode: str = "position",
    smooth_3d: float = 1.0,
) -> None:
    """パイプライン実行: VideoExtractor → PoseEstimator → DataProcessor → Converter3D → export."""
    logger.step("cli.pipeline", context={"video_path": video_path, "format": fmt}, ai_todo=["run_full_pipeline"])

    # 1. フレーム抽出
    click.echo("Extracting frames...")
    extractor = VideoExtractor(ExtractorConfig(target_fps=fps))
    frames = extractor.extract_frames(video_path, target_fps=fps)
    click.echo(f"  {len(frames)} frames extracted")

    # 2. 2Dポーズ推定
    click.echo("Estimating 2D poses...")
    estimator = PoseEstimator(PoseModelConfig(batch_size=batch_size))
    pose_2d = estimator.estimate_2d_pose(frames, batch_size=batch_size)
    click.echo(f"  {len(pose_2d.frames)} poses estimated ({len(pose_2d.joint_names)} joints)")

    # 3. データ処理
    click.echo("Processing data...")
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
        click.echo(f"  {len(pose_2d.joint_names)} joints remaining after removal")

    # 4. 3D変換 & エクスポート
    click.echo("Converting to 3D...")
    converter = Converter3D(Converter3DConfig(
        bvh_mode=bvh_mode,
        smooth_3d_sigma=smooth_3d,
    ))
    motion_3d = converter.convert_to_3d(pose_2d)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    converter.export(motion_3d, output_path, fmt)
    click.echo(f"Exported to {output_path} ({fmt})")


if __name__ == "__main__":
    main()
