"""CLI エントリポイント（click使用）."""

import sys
from pathlib import Path
from typing import Optional

import click

from video_motion_extraction import logger
from video_motion_extraction.config import ExtractorConfig
from video_motion_extraction.errors import (
    GPUMemoryError,
    ModelNotAvailableError,
    ValidationError,
    VideoLoadError,
)
from video_motion_extraction.pipeline import (
    MotionExtractor,
    PipelineOptions,
    export_angular_velocity,
)
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
@click.option("--root-motion-scale", type=float, default=2.5, show_default=True, help="ルートモーション補正係数 (0.1〜10.0)")
@click.option(
    "--device", type=str, default="auto", show_default=True,
    help="推論デバイス (auto/cpu/cuda/cuda:N)",
)
@click.option(
    "--strict/--no-strict", default=None,
    help="strictモード: 推論モデル未ロード時にエラー終了 (デフォルト: 環境変数 VME_STRICT)",
)
@click.option(
    "--angular-velocity", "angular_velocity_path", type=click.Path(), default=None,
    help="角速度データのJSON出力パス (指定時のみ算出)",
)
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
    root_motion_scale: float,
    device: str,
    strict: Optional[bool],
    angular_velocity_path: Optional[str],
    info: bool,
) -> None:
    """動画から3Dモーションデータを抽出する.

    VIDEO_PATH: 入力動画ファイルのパス
    """
    logger.configure()
    logger.step("cli.main", context={"video_path": video_path, "info": info}, ai_todo=["parse_args", "run_pipeline"])

    if info:
        _show_info(VideoExtractor(ExtractorConfig(target_fps=fps)), video_path)
        return

    if output_path is None:
        raise click.UsageError("--output / -o は必須です (--info を使う場合を除く)")

    fmt = output_format or _detect_format(output_path)

    joints_to_remove = [j.strip() for j in remove_joints.split(",") if j.strip()] if remove_joints else []

    options = PipelineOptions(
        fps=fps,
        threshold=threshold,
        smoothing=smoothing,
        joints_to_remove=joints_to_remove,
        batch_size=batch_size,
        bvh_mode=bvh_mode,
        smooth_3d=smooth_3d,
        root_motion_scale=root_motion_scale,
        compute_angular_velocity=angular_velocity_path is not None,
        device=device,
    )
    if strict is not None:
        options.strict = strict

    try:
        extractor = MotionExtractor(options)
        result = extractor.process(
            video_path,
            on_progress=lambda step, progress, message: click.echo(message),
        )
        extractor.export(result.motion_3d, output_path, fmt)
        click.echo(f"Exported to {output_path} ({fmt})")

        if angular_velocity_path and result.angular_velocity is not None:
            export_angular_velocity(
                result.angular_velocity, angular_velocity_path, fps
            )
            click.echo(f"Angular velocity exported to {angular_velocity_path}")
    except (ValidationError, VideoLoadError, ValueError) as exc:
        logger.error("cli.main", what="Input error", why=str(exc), how="Check input file and parameters")
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except GPUMemoryError as exc:
        logger.error("cli.main", what="GPU memory error", why=str(exc), how="Reduce --batch-size")
        click.echo(f"GPU Error: {exc}", err=True)
        sys.exit(2)
    except ModelNotAvailableError as exc:
        logger.error("cli.main", what="Model not available", why=str(exc), how="Install [gpu] extras and download weights")
        click.echo(f"Model Error: {exc}", err=True)
        sys.exit(3)


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


if __name__ == "__main__":
    main()
