#!/usr/bin/env python3
"""動画モーション抽出のベンチマークスクリプト.

motion-data-2dto3d パイプラインで動画を処理し、品質・速度メトリクスを JSON に出力する。
ComfyUI-Video2MotionCapture 等との比較は docs/motion-benchmark.md を参照。
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from video_motion_extraction.joint_mapping import H36M_JOINT_NAMES  # noqa: E402
from video_motion_extraction.pipeline import MotionExtractor, PipelineOptions  # noqa: E402


def _parse_bvh_root_y_rotations(bvh_path: Path) -> np.ndarray:
    """BVH の ROOT Y 回転列（度）を抽出."""
    lines = bvh_path.read_text(encoding="utf-8").splitlines()
    motion_idx = lines.index("MOTION")
    data_lines = lines[motion_idx + 3 :]
    y_rots: List[float] = []
    for row in data_lines:
        row = row.strip()
        if not row:
            continue
        vals = row.split()
        # CHANNELS 6: Xpos Ypos Zpos Zrot Xrot Yrot
        if len(vals) >= 6:
            y_rots.append(float(vals[5]))
    return np.array(y_rots, dtype=np.float64)


def _foot_slide_proxy(positions: np.ndarray, foot_indices: List[int]) -> float:
    """足首高さのフレーム間差分の平均（小さいほど良い目安）."""
    if positions.shape[0] < 2:
        return 0.0
    foot_y = positions[:, foot_indices, 1]  # Y-up
    min_y = foot_y.min(axis=1)
    deltas = np.abs(np.diff(min_y))
    return float(np.mean(deltas))


def _joint_jitter(positions: np.ndarray, joint_indices: List[int]) -> float:
    """主要関節の速度変動（加速度ノルムの平均）."""
    if positions.shape[0] < 3:
        return 0.0
    subset = positions[:, joint_indices, :]
    vel = np.diff(subset, axis=0)
    acc = np.diff(vel, axis=0)
    return float(np.mean(np.linalg.norm(acc, axis=2)))


def benchmark_video(
    video_path: Path,
    *,
    fps: float,
    bvh_mode: str,
    root_motion_scale: float,
) -> Dict[str, Any]:
    """1本の動画を処理してメトリクス辞書を返す."""
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")

    name_to_idx = {n: i for i, n in enumerate(H36M_JOINT_NAMES)}
    foot_indices = [name_to_idx[j] for j in ("LFoot", "RFoot") if j in name_to_idx]
    key_indices = [
        name_to_idx[j]
        for j in ("Hip", "Thorax", "LShoulder", "RShoulder", "LKnee", "RKnee")
        if j in name_to_idx
    ]

    options = PipelineOptions(
        fps=fps,
        bvh_mode=bvh_mode,
        root_motion_scale=root_motion_scale,
    )
    extractor = MotionExtractor(options)

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="vme_bench_") as tmpdir:
        bvh_path = Path(tmpdir) / f"{video_path.stem}.bvh"
        result = extractor.process(str(video_path))
        extractor.export(result.motion_3d, str(bvh_path), "bvh")

        root_yaw_range: Optional[float] = None
        root_yaw_nonzero: Optional[bool] = None
        if bvh_mode == "rotation":
            root_y = _parse_bvh_root_y_rotations(bvh_path)
            if root_y.size > 0:
                root_yaw_range = round(float(np.max(root_y) - np.min(root_y)), 3)
                root_yaw_nonzero = bool(np.max(np.abs(root_y)) > 1e-3)
            else:
                root_yaw_range = 0.0
                root_yaw_nonzero = False
    elapsed = time.perf_counter() - t0

    positions = np.stack(
        [f.positions for f in result.motion_3d.frames],
        axis=0,
    )

    metrics: Dict[str, Any] = {
        "engine": "motion-data-2dto3d",
        "video": str(video_path.resolve()),
        "video_stem": video_path.stem,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "processing_time_sec": round(elapsed, 3),
        "frame_count": len(result.motion_3d.frames),
        "fps": result.motion_3d.fps,
        "quality_score": round(result.motion_3d.quality_score or 0.0, 4),
        "bvh_mode": bvh_mode,
        "foot_slide_proxy": round(_foot_slide_proxy(positions, foot_indices), 6),
        "joint_jitter": round(_joint_jitter(positions, key_indices), 6),
    }

    if root_yaw_range is not None:
        metrics["root_yaw_range_deg"] = root_yaw_range
        metrics["root_yaw_nonzero"] = root_yaw_nonzero

    return metrics


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark motion-data-2dto3d extraction")
    parser.add_argument("videos", nargs="+", type=Path, help="Input video file(s)")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument(
        "--bvh-mode",
        choices=("position", "rotation"),
        default="rotation",
        help="BVH export mode (rotation enables root yaw metrics)",
    )
    parser.add_argument("--root-motion-scale", type=float, default=2.5)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "benchmark" / "reports",
    )
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    reports: List[Dict[str, Any]] = []

    for video in args.videos:
        print(f"Benchmarking: {video}")
        try:
            report = benchmark_video(
                video,
                fps=args.fps,
                bvh_mode=args.bvh_mode,
                root_motion_scale=args.root_motion_scale,
            )
        except Exception as exc:
            report = {
                "engine": "motion-data-2dto3d",
                "video": str(video),
                "error": str(exc),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  ERROR: {exc}")
        else:
            print(
                f"  frames={report.get('frame_count')} "
                f"time={report.get('processing_time_sec')}s "
                f"quality={report.get('quality_score')}"
            )

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stem = video.stem if video.exists() else "unknown"
        out_path = args.output_dir / f"{stem}_{ts}.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {out_path}")
        reports.append(report)

    summary_path = args.output_dir / f"summary_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    summary_path.write_text(
        json.dumps({"runs": reports}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
