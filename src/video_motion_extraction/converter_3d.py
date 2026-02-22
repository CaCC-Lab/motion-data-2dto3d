"""Converter3D: 2D→3D変換コンポーネント."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from video_motion_extraction import logger
from video_motion_extraction.config import Converter3DConfig
from video_motion_extraction.models import (
    Motion3DData,
    Motion3DFrame,
    Pose2DSequence,
)


class Converter3D:
    """2Dポーズデータを3Dモーションデータに変換するクラス."""

    def __init__(self, config: Optional[Converter3DConfig] = None) -> None:
        self._config = config or Converter3DConfig()
        logger.step(
            "Converter3D.__init__",
            context={"config": str(self._config)},
            ai_todo=["initialize_converter"],
        )

    def convert_to_3d(self, pose_2d: Pose2DSequence) -> Motion3DData:
        """2Dポーズを3Dモーションに変換."""
        logger.step(
            "convert_to_3d",
            context={"num_frames": len(pose_2d.frames), "num_joints": len(pose_2d.joint_names)},
            ai_todo=["lift_2d_to_3d", "compute_rotations", "normalize_quaternions"],
        )
        num_joints = len(pose_2d.joint_names)
        motion_frames: List[Motion3DFrame] = []

        for frame_2d in pose_2d.frames:
            positions = np.zeros((num_joints, 3), dtype=np.float32)
            positions[:, 0] = frame_2d.keypoints[:, 0]
            positions[:, 1] = frame_2d.keypoints[:, 1]

            rotations = np.zeros((num_joints, 4), dtype=np.float32)
            rotations[:, 0] = 1.0  # identity quaternion [w, x, y, z]

            motion_frames.append(
                Motion3DFrame(
                    frame_id=frame_2d.frame_id,
                    positions=positions,
                    rotations=rotations,
                )
            )

        joint_hierarchy: Dict[str, str] = {}
        for i, name in enumerate(pose_2d.joint_names):
            if i > 0:
                joint_hierarchy[name] = pose_2d.joint_names[0]

        return Motion3DData(
            frames=motion_frames,
            joint_names=list(pose_2d.joint_names),
            joint_hierarchy=joint_hierarchy,
            fps=pose_2d.fps,
        )

    def export(
        self, motion_data: Motion3DData, output_path: str, format: str
    ) -> None:
        """指定フォーマットでエクスポート."""
        logger.step(
            "export",
            context={"output_path": output_path, "format": format},
            ai_todo=["select_format", "write_file"],
        )
        fmt = format.lower()
        if fmt == "json":
            self._export_json(motion_data, output_path)
        elif fmt == "bvh":
            self._export_bvh(motion_data, output_path)
        elif fmt == "fbx":
            self._export_fbx(motion_data, output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, motion_data: Motion3DData, output_path: str) -> None:
        payload = {
            "coordinate_system": "right-handed-y-up",
            "fps": motion_data.fps,
            "joint_names": motion_data.joint_names,
            "joint_hierarchy": motion_data.joint_hierarchy,
            "frames": [
                {
                    "frame_id": frame.frame_id,
                    "positions": frame.positions.tolist(),
                    "rotations": frame.rotations.tolist(),
                }
                for frame in motion_data.frames
            ],
        }
        Path(output_path).write_text(json.dumps(payload, indent=2))

    def _export_bvh(self, motion_data: Motion3DData, output_path: str) -> None:
        lines = ["HIERARCHY", f"ROOT {motion_data.joint_names[0] if motion_data.joint_names else 'root'}"]
        lines.append("{")
        lines.append("  OFFSET 0.0 0.0 0.0")
        channels = "CHANNELS 6 Xposition Yposition Zposition Xrotation Yrotation Zrotation"
        lines.append(f"  {channels}")

        for jname in motion_data.joint_names[1:]:
            lines.append(f"  JOINT {jname}")
            lines.append("  {")
            lines.append("    OFFSET 1.0 0.0 0.0")
            lines.append("    CHANNELS 3 Xrotation Yrotation Zrotation")
            lines.append("    End Site")
            lines.append("    {")
            lines.append("      OFFSET 0.5 0.0 0.0")
            lines.append("    }")
            lines.append("  }")

        if not motion_data.joint_names[1:]:
            lines.append("  End Site")
            lines.append("  {")
            lines.append("    OFFSET 0.5 0.0 0.0")
            lines.append("  }")

        lines.append("}")
        lines.append("MOTION")
        lines.append(f"Frames: {len(motion_data.frames)}")
        frame_time = 1.0 / motion_data.fps if motion_data.fps > 0 else 0.033
        lines.append(f"Frame Time: {frame_time:.6f}")

        for frame in motion_data.frames:
            pos = frame.positions[0] if frame.positions.shape[0] > 0 else np.zeros(3)
            values = [f"{pos[0]:.4f}", f"{pos[1]:.4f}", f"{pos[2]:.4f}"]
            for j in range(frame.rotations.shape[0]):
                values.extend(["0.0000", "0.0000", "0.0000"])
            lines.append(" ".join(values))

        Path(output_path).write_text("\n".join(lines))

    def _export_fbx(self, motion_data: Motion3DData, output_path: str) -> None:
        lines = ["; FBX ASCII 7.4"]
        lines.append(f"; Joints: {len(motion_data.joint_names)}")
        lines.append(f"; Frames: {len(motion_data.frames)}")
        lines.append(f"; FPS: {motion_data.fps}")
        lines.append("")
        lines.append("Objects: {")
        for jname in motion_data.joint_names:
            lines.append(f'  Model: "{jname}", "LimbNode" {{')
            lines.append("  }")
        lines.append("}")
        lines.append("")
        lines.append("AnimationStack: {")
        for frame in motion_data.frames:
            pos = frame.positions.tolist()
            lines.append(f"  Frame {frame.frame_id}: {pos}")
        lines.append("}")

        Path(output_path).write_text("\n".join(lines))
