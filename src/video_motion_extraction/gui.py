"""Gradio WebUI."""

import tempfile
from pathlib import Path
from typing import Optional, Tuple

from video_motion_extraction import logger
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

SUPPORTED_FORMATS = ["bvh", "fbx", "json"]


def _get_video_info(video_path: str) -> str:
    """動画メタデータを文字列で返す."""
    extractor = VideoExtractor()
    meta = extractor.get_video_metadata(video_path)
    return (
        f"Resolution: {meta.width}x{meta.height}\n"
        f"FPS: {meta.fps}\n"
        f"Frames: {meta.total_frames}\n"
        f"Duration: {meta.duration:.2f}s\n"
        f"Codec: {meta.codec}"
    )


def process_video(
    video_path: str,
    fps: float,
    threshold: float,
    smoothing: int,
    remove_joints: str,
    output_format: str,
    batch_size: int,
    bvh_mode: str = "position",
    smooth_3d: float = 1.0,
    root_motion_scale: float = 2.5,
) -> Tuple[Optional[str], str]:
    """パイプライン実行してファイルパスとログを返す.

    Returns:
        (output_file_path or None, status_log)
    """
    logger.step("gui.process_video", context={"video_path": video_path}, ai_todo=["run_pipeline"])

    if not video_path:
        return None, "Error: 動画ファイルをアップロードしてください"

    log_lines = []

    try:
        # メタデータ表示
        info = _get_video_info(video_path)
        log_lines.append(f"=== Video Info ===\n{info}\n")

        # 1. フレーム抽出
        log_lines.append("Extracting frames...")
        extractor = VideoExtractor(ExtractorConfig(target_fps=fps))
        frames = extractor.extract_frames(video_path, target_fps=fps)
        log_lines.append(f"  {len(frames)} frames extracted")

        # 2. 2Dポーズ推定
        log_lines.append("Estimating 2D poses...")
        estimator = PoseEstimator(PoseModelConfig(batch_size=batch_size))
        pose_2d = estimator.estimate_2d_pose(frames, batch_size=batch_size)
        log_lines.append(f"  {len(pose_2d.frames)} poses ({len(pose_2d.joint_names)} joints)")

        # 3. データ処理
        log_lines.append("Processing data...")
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
            log_lines.append(f"  {len(pose_2d.joint_names)} joints remaining")

        # 4. 3D変換 & エクスポート
        log_lines.append("Converting to 3D...")
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

        log_lines.append(f"Done! Exported as {output_format}")
        return tmp.name, "\n".join(log_lines)

    except Exception as exc:
        logger.error("gui.process_video", what="Pipeline failed", why=str(exc), how="Check input and parameters")
        log_lines.append(f"\nError: {exc}")
        return None, "\n".join(log_lines)


def create_ui():
    """Gradio UIを構築."""
    import gradio as gr

    with gr.Blocks(title="Video Motion Extraction") as demo:
        gr.Markdown("# Video Motion Extraction\n動画から3Dモーションデータを抽出")

        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.Video(label="入力動画")

                with gr.Accordion("設定", open=True):
                    fps = gr.Slider(1, 120, value=30, step=1, label="FPS")
                    threshold = gr.Slider(0.0, 1.0, value=0.3, step=0.05, label="信頼度閾値")
                    smoothing = gr.Slider(1, 21, value=5, step=2, label="スムージング窓")
                    remove_joints = gr.Textbox(label="除外関節 (カンマ区切り)", placeholder="left_hand_*,right_hand_*")
                    output_format = gr.Dropdown(SUPPORTED_FORMATS, value="bvh", label="出力フォーマット")
                    batch_size = gr.Slider(1, 128, value=32, step=1, label="バッチサイズ")
                    bvh_mode = gr.Radio(
                        ["position", "rotation"], value="position",
                        label="BVHモード",
                    )
                    smooth_3d = gr.Slider(0.0, 5.0, value=1.0, step=0.1, label="3Dスムージングσ")
                    root_motion_scale = gr.Slider(0.1, 10.0, value=2.5, step=0.1, label="ルートモーション補正係数")

                run_btn = gr.Button("実行", variant="primary")

            with gr.Column(scale=1):
                output_file = gr.File(label="出力ファイル")
                status_log = gr.Textbox(label="ログ", lines=15, interactive=False)

        run_btn.click(
            fn=process_video,
            inputs=[video_input, fps, threshold, smoothing, remove_joints, output_format, batch_size, bvh_mode, smooth_3d, root_motion_scale],
            outputs=[output_file, status_log],
        )

    return demo


def main() -> None:
    """GUI起動エントリポイント."""
    logger.step("gui.main", context={}, ai_todo=["launch_gradio"])
    demo = create_ui()
    demo.launch()


if __name__ == "__main__":
    main()
