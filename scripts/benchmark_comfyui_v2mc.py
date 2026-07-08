#!/usr/bin/env python3
"""ComfyUI-Video2MotionCapture (GVHMR) のベンチマーク.

SAM3 なしで全画面マスクを使い GVHMR 推論のみ計測する（比較用スモーク）。
実行は scripts/run_comfyui_v2mc_benchmark.sh 経由を推奨（pixi Python 3.11）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

DEFAULT_COMFYUI = Path.home() / "ComfyUI"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "benchmark" / "reports"


def _load_video_frames(
    video_path: Path,
    *,
    fps_target: float,
    frame_cap: int,
    skip_first: int,
) -> tuple[np.ndarray, float]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / fps_target))) if fps_target > 0 else 1
    frames: List[np.ndarray] = []
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx >= skip_first and idx % step == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(rgb)
            if frame_cap > 0 and len(frames) >= frame_cap:
                break
        idx += 1
    cap.release()

    if not frames:
        raise RuntimeError("No frames decoded from video")

    tensor = np.stack(frames, axis=0).astype(np.float32) / 255.0
    return tensor, float(src_fps)


def benchmark_video(
    video_path: Path,
    *,
    comfyui_root: Path,
    frame_cap: int,
    fps_target: float,
    skip_first: int,
    static_camera: bool,
) -> Dict[str, Any]:
    video_path = video_path.resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")

    comfyui_root = comfyui_root.resolve()
    nodes_dir = comfyui_root / "custom_nodes" / "ComfyUI-Video2MotionCapture" / "nodes"
    if not nodes_dir.is_dir():
        raise FileNotFoundError(f"V2MC nodes not found: {nodes_dir}")

    os.chdir(comfyui_root)
    if str(comfyui_root) not in sys.path:
        sys.path.insert(0, str(comfyui_root))
    if str(nodes_dir) not in sys.path:
        sys.path.insert(0, str(nodes_dir))

    import torch  # noqa: WPS433
    import folder_paths  # noqa: WPS433
    from loader_node import LoadGVHMRModels  # noqa: WPS433
    from inference_node import GVHMRInference  # noqa: WPS433

    frames_np, src_fps = _load_video_frames(
        video_path,
        fps_target=fps_target,
        frame_cap=frame_cap,
        skip_first=skip_first,
    )
    num_frames = frames_np.shape[0]
    height, width = frames_np.shape[1:3]

    images = torch.from_numpy(frames_np)
    masks = torch.ones((num_frames, height, width), dtype=torch.float32)

    t0 = time.perf_counter()
    loader = LoadGVHMRModels()
    (config,) = loader.load_models()
    load_elapsed = time.perf_counter() - t0

    infer = GVHMRInference()
    t1 = time.perf_counter()
    npz_path, _viz, info = infer.run_inference(
        images,
        masks,
        config,
        static_camera=static_camera,
    )
    infer_elapsed = time.perf_counter() - t1
    total_elapsed = time.perf_counter() - t0

    smpl_export = bool(npz_path) and Path(npz_path).is_file()
    fbx_path = ""
    if smpl_export:
        try:
            from save_smpl_as_fbx_node import SaveSMPLAsRiggedFBX  # noqa: WPS433

            out_dir = Path(folder_paths.get_output_directory())
            fbx_out = out_dir / f"bench_{video_path.stem}.fbx"
            saver = SaveSMPLAsRiggedFBX()
            (fbx_path,) = saver.export(
                str(npz_path),
                "SMPL_MALE.pkl",
                30,
                fbx_out.stem,
                str(fbx_out),
                "Y",
                "-Z",
            )
        except Exception as exc:
            fbx_path = f"ERROR: {exc}"

    return {
        "engine": "ComfyUI-Video2MotionCapture",
        "video": str(video_path.resolve()),
        "video_stem": video_path.stem,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "processing_time_sec": round(total_elapsed, 3),
        "model_load_sec": round(load_elapsed, 3),
        "inference_sec": round(infer_elapsed, 3),
        "frame_count": num_frames,
        "source_fps": src_fps,
        "target_fps": fps_target,
        "frame_cap": frame_cap,
        "static_camera": static_camera,
        "smpl_npz": str(npz_path) if npz_path else "",
        "smpl_export": smpl_export,
        "fbx_path": str(fbx_path),
        "info": info,
        "note": "full-frame mask proxy (SAM3 未使用)",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark ComfyUI GVHMR inference")
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--comfyui-root", type=Path, default=DEFAULT_COMFYUI)
    parser.add_argument("--frame-cap", type=int, default=120, help="Max frames (0=all)")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--skip-first", type=int, default=0)
    parser.add_argument("--static-camera", action="store_true", default=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    reports: List[Dict[str, Any]] = []

    for video in args.videos:
        video = video.resolve()
        print(f"ComfyUI-V2MC benchmark: {video}")
        try:
            report = benchmark_video(
                video,
                comfyui_root=args.comfyui_root,
                frame_cap=args.frame_cap,
                fps_target=args.fps,
                skip_first=args.skip_first,
                static_camera=args.static_camera,
            )
        except Exception as exc:
            report = {
                "engine": "ComfyUI-Video2MotionCapture",
                "video": str(video),
                "error": str(exc),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  ERROR: {exc}")
        else:
            print(
                f"  frames={report.get('frame_count')} "
                f"time={report.get('processing_time_sec')}s "
                f"smpl={report.get('smpl_export')}"
            )

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stem = video.stem if video.exists() else "unknown"
        out_path = args.output_dir / f"comfyui_{stem}_{ts}.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {out_path}")
        reports.append(report)

    summary_path = args.output_dir / (
        f"comfyui_summary_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    summary_path.write_text(
        json.dumps({"runs": reports}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Summary: {summary_path}")
    return 0 if all("error" not in r for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
