#!/usr/bin/env python3
"""clip_c 向けの生成AI歩行クリップを作成する.

Stable Diffusion で全身キーフレームを生成し、Stable Video Diffusion で
短い動画セグメントを作って連結する。ベンチ用に 8秒 / 1920x1080 / 30fps に正規化する。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

import torch
from diffusers import StableDiffusionPipeline, StableVideoDiffusionPipeline
from diffusers.utils import export_to_video
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT_ROOT / "data/benchmark/clips/clip_c_walk_ai.mp4"

KEYFRAME_PROMPTS = [
    (
        "full body person standing facing camera, plain white studio background, "
        "gray t-shirt black pants, feet visible on floor, professional photo, front view"
    ),
    (
        "full body person walking toward camera mid stride, plain white studio background, "
        "gray t-shirt black pants, feet visible, professional photo, front view"
    ),
    (
        "full body person walking closer to camera, plain white studio background, "
        "gray t-shirt black pants, feet visible, professional photo, front view"
    ),
]


def _run_ffmpeg(args: List[str]) -> None:
    cmd = ["ffmpeg", "-y", *args]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _generate_keyframes(
    device: str,
    dtype: torch.dtype,
    seed: int,
    width: int,
    height: int,
) -> List[Image.Image]:
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=dtype,
        safety_checker=None,
    )
    pipe = pipe.to(device)
    pipe.set_progress_bar_config(disable=True)

    images: List[Image.Image] = []
    for idx, prompt in enumerate(KEYFRAME_PROMPTS):
        generator = torch.Generator(device=device).manual_seed(seed + idx)
        result = pipe(
            prompt=prompt,
            negative_prompt="cropped, partial body, side view, back view, blurry, multiple people",
            num_inference_steps=28,
            guidance_scale=7.5,
            width=width,
            height=height,
            generator=generator,
        )
        images.append(result.images[0])
    del pipe
    torch.cuda.empty_cache()
    return images


def _generate_svd_segments(
    keyframes: List[Image.Image],
    device: str,
    dtype: torch.dtype,
    seed: int,
    frames_per_segment: int,
    motion_bucket_id: int,
) -> List[Path]:
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid",
        torch_dtype=dtype,
        variant="fp16",
    )
    pipe = pipe.to(device)
    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)

    segment_paths: List[Path] = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="clip_c_ai_"))

    for idx, image in enumerate(keyframes):
        # SVD は 1024x576 を推奨
        resized = image.resize((1024, 576), Image.Resampling.LANCZOS)
        generator = torch.Generator(device=device).manual_seed(seed + 100 + idx)
        frames = pipe(
            resized,
            decode_chunk_size=2,
            num_frames=frames_per_segment,
            motion_bucket_id=motion_bucket_id,
            noise_aug_strength=0.02,
            generator=generator,
        ).frames[0]
        out = tmp_dir / f"segment_{idx:02d}.mp4"
        export_to_video(frames, str(out), fps=7)
        segment_paths.append(out)

    del pipe
    torch.cuda.empty_cache()
    return segment_paths


def _concat_and_normalize(segment_paths: List[Path], output: Path, duration_sec: float) -> None:
    list_file = segment_paths[0].parent / "concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in segment_paths),
        encoding="utf-8",
    )
    merged = segment_paths[0].parent / "merged.mp4"
    _run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(merged),
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "-i",
            str(merged),
            "-t",
            str(duration_sec),
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            str(output),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate clip_c walk video with SD + SVD")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--frames-per-segment", type=int, default=25)
    parser.add_argument("--motion-bucket-id", type=int, default=127)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    dtype = torch.float16 if args.device.startswith("cuda") else torch.float32

    print("=== 1/3 keyframes (SD 1.5) ===")
    keyframes = _generate_keyframes(args.device, dtype, args.seed, 768, 512)
    for i, img in enumerate(keyframes):
        debug_path = args.output.parent / f"clip_c_ai_keyframe_{i}.png"
        img.save(debug_path)
        print(f"saved {debug_path}")

    print("=== 2/3 segments (SVD) ===")
    segments = _generate_svd_segments(
        keyframes,
        args.device,
        dtype,
        args.seed,
        args.frames_per_segment,
        args.motion_bucket_id,
    )
    for seg in segments:
        print(f"segment {seg}")

    print("=== 3/3 concat + normalize ===")
    _concat_and_normalize(segments, args.output, args.duration)
    print(f"done: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
