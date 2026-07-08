#!/usr/bin/env python3
"""ベンチマーク用クリップの事前検証.

docs/benchmark-clips-guide.md の撮影条件をメタデータと簡易ポーズ検出で確認する。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _ffprobe(path: Path) -> Dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,nb_frames",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    raw = subprocess.check_output(cmd, text=True)
    data = json.loads(raw)
    stream = data.get("streams", [{}])[0]
    fmt = data.get("format", {})
    fps_parts = stream.get("r_frame_rate", "0/1").split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1] or 1)
    return {
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": round(fps, 3),
        "duration_sec": float(fmt.get("duration", 0)),
        "nb_frames": int(stream.get("nb_frames", 0) or 0),
    }


def _quick_pose_check(path: Path, sample_frames: int) -> Dict[str, Any]:
    import cv2  # noqa: WPS433

    from video_motion_extraction.pose_estimator import PoseEstimator  # noqa: E402

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    step = max(1, total // sample_frames) if total > 0 else 1
    sampled: List[Any] = []
    idx = 0
    while len(sampled) < sample_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            sampled.append(frame)
        idx += 1
    cap.release()

    if not sampled:
        return {"sample_frames": 0, "detection_rate": 0.0, "avg_confidence": 0.0}

    estimator = PoseEstimator()
    sequence = estimator.estimate_2d_pose(sampled, batch_size=min(8, len(sampled)))
    detected = 0
    conf_sum = 0.0
    for frame in sequence.frames:
        mean_conf = float(frame.confidence.mean())
        if mean_conf > 0.05:
            detected += 1
            conf_sum += mean_conf
    checked = len(sequence.frames)
    detection_rate = detected / checked if checked else 0.0
    return {
        "sample_frames": checked,
        "detection_rate": round(detection_rate, 3),
        "avg_confidence": round(conf_sum / detected, 3) if detected else 0.0,
    }


def validate_clip(path: Path, *, deep: bool, sample_frames: int) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)

    meta = _ffprobe(path)
    issues: List[str] = []
    warnings: List[str] = []

    min_side = min(meta["width"], meta["height"])
    if min_side < 720:
        issues.append(f"解像度が低い: {meta['width']}x{meta['height']} (720p 以上推奨)")
    if meta["fps"] < 25:
        warnings.append(f"FPS が低い: {meta['fps']} (30fps 以上推奨)")
    if meta["duration_sec"] > 10:
        warnings.append(f"長すぎる: {meta['duration_sec']:.1f}s (10秒以内推奨)")
    elif meta["duration_sec"] < 3:
        warnings.append(f"短すぎる: {meta['duration_sec']:.1f}s (5〜8秒推奨)")

    report: Dict[str, Any] = {
        "video": str(path.resolve()),
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        **meta,
    }

    if deep:
        pose = _quick_pose_check(path, sample_frames)
        report["pose_check"] = pose
        if pose["detection_rate"] < 0.8:
            issues.append(
                f"ポーズ検出率が低い: {pose['detection_rate']:.0%} "
                f"(80% 以上推奨)"
            )
        if pose["avg_confidence"] < 0.3 and pose["detection_rate"] > 0:
            warnings.append(
                f"平均信頼度が低い: {pose['avg_confidence']:.2f}"
            )
        report["ok"] = len(issues) == 0

    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate benchmark clip suitability")
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Run lightweight pose detection on sampled frames (GPU)",
    )
    parser.add_argument("--sample-frames", type=int, default=12)
    args = parser.parse_args(argv)

    exit_code = 0
    for video in args.videos:
        print(f"Validating: {video}")
        try:
            report = validate_clip(video, deep=args.deep, sample_frames=args.sample_frames)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            exit_code = 1
            continue

        status = "OK" if report["ok"] else "NG"
        print(f"  [{status}] {report['width']}x{report['height']} "
              f"{report['fps']}fps {report['duration_sec']:.1f}s")
        if report.get("pose_check"):
            pc = report["pose_check"]
            print(f"  pose: detection={pc['detection_rate']:.0%} "
                  f"conf={pc['avg_confidence']:.2f}")
        for w in report["warnings"]:
            print(f"  WARN: {w}")
        for i in report["issues"]:
            print(f"  ISSUE: {i}")
        if not report["ok"]:
            exit_code = 1
        print()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
