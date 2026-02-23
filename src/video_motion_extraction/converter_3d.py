"""Converter3D: 2D→3D変換コンポーネント."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from video_motion_extraction import logger
from video_motion_extraction.config import Converter3DConfig
from video_motion_extraction.joint_mapping import (
    H36M_HIERARCHY,
    H36M_JOINT_NAMES,
    coco_to_h36m_keypoints,
)
from video_motion_extraction.models import (
    Motion3DData,
    Motion3DFrame,
    Pose2DSequence,
)
from video_motion_extraction.quaternion_utils import (
    normalize_quaternions,
    positions_to_quaternions,
)


class Converter3D:
    """2Dポーズデータを3Dモーションデータに変換するクラス."""

    def __init__(self, config: Optional[Converter3DConfig] = None) -> None:
        self._config = config or Converter3DConfig()
        self._model_available = False
        self._model = None
        self._try_load_model()
        logger.step(
            "Converter3D.__init__",
            context={"config": str(self._config), "model_available": self._model_available},
            ai_todo=["initialize_converter"],
        )

    def _try_load_model(self) -> None:
        """VideoPose3Dモデルの遅延ロードを試行."""
        weights_path = self._config.weights_path
        if weights_path is None:
            # デフォルトパス
            default_path = Path(__file__).parent / "weights" / "pretrained_h36m_cpn.bin"
            if default_path.exists():
                weights_path = str(default_path)

        if weights_path is None or not Path(weights_path).exists():
            self._model_available = False
            return

        try:
            from video_motion_extraction.videopose3d_model import load_videopose3d_model
            model = load_videopose3d_model(
                weights_path=weights_path,
                device=self._config.device,
                receptive_field=self._config.receptive_field,
            )
            if model is not None:
                self._model = model
                self._model_available = True
                logger.step(
                    "Converter3D._try_load_model",
                    context={"status": "loaded", "weights": weights_path},
                    ai_todo=[],
                )
            else:
                self._model_available = False
        except Exception as exc:
            self._model_available = False
            logger.step(
                "Converter3D._try_load_model",
                context={"status": "fallback_to_stub", "reason": str(exc)},
                ai_todo=[],
            )

    def convert_to_3d(self, pose_2d: Pose2DSequence) -> Motion3DData:
        """2Dポーズを3Dモーションに変換."""
        num_joints = len(pose_2d.joint_names)
        logger.step(
            "convert_to_3d",
            context={
                "num_frames": len(pose_2d.frames),
                "num_joints": num_joints,
                "model_available": self._model_available,
            },
            ai_todo=["lift_2d_to_3d", "compute_rotations", "normalize_quaternions"],
        )

        if self._model_available and num_joints == 17:
            return self._convert_real(pose_2d)
        return self._convert_stub(pose_2d)

    def _convert_real(self, pose_2d: Pose2DSequence) -> Motion3DData:
        """VideoPose3Dによる本物の2D→3D変換."""
        import torch

        logger.step(
            "_convert_real",
            context={"num_frames": len(pose_2d.frames)},
            ai_todo=["coco_to_h36m", "normalize", "infer_3d", "compute_rotations"],
        )

        # 1. 2Dキーポイントを(T,17,2)にスタック
        kps_2d = np.stack([f.keypoints for f in pose_2d.frames], axis=0)  # (T, 17, 2)

        # 2. COCO→H36M関節順に変換
        kps_h36m = coco_to_h36m_keypoints(kps_2d)  # (T, 17, 2)

        # 3. Hip中心化 + スケール正規化
        hip_center = kps_h36m[:, 0:1, :]  # (T, 1, 2)
        kps_centered = kps_h36m - hip_center

        # スケール正規化: 全体のバウンディングボックスの最大幅で割る
        scale = np.max(np.abs(kps_centered)) + 1e-6
        kps_normalized = kps_centered / scale

        # 4. VideoPose3D推論
        t = kps_normalized.shape[0]
        input_2d = kps_normalized.reshape(1, t, 17 * 2).astype(np.float32)
        input_tensor = torch.from_numpy(input_2d).to(self._config.device)

        with torch.no_grad():
            output_3d = self._model(input_tensor)  # (1, T, 17, 3)

        positions_3d = output_3d.cpu().numpy()[0]  # (T, 17, 3)

        # 5. mm→m変換（VideoPose3Dの出力はmmスケール）
        positions_3d = positions_3d / 1000.0

        # 6. クォータニオン回転計算
        motion_frames: List[Motion3DFrame] = []
        for frame_idx in range(t):
            pos = positions_3d[frame_idx]  # (17, 3)
            rot = positions_to_quaternions(pos, H36M_JOINT_NAMES, H36M_HIERARCHY)

            motion_frames.append(
                Motion3DFrame(
                    frame_id=frame_idx,
                    positions=pos.astype(np.float32),
                    rotations=rot.astype(np.float32),
                )
            )

        return Motion3DData(
            frames=motion_frames,
            joint_names=list(H36M_JOINT_NAMES),
            joint_hierarchy=dict(H36M_HIERARCHY),
            fps=pose_2d.fps,
        )

    def _convert_stub(self, pose_2d: Pose2DSequence) -> Motion3DData:
        """スタブ実装による2D→3D変換（フォールバック）."""
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
        hierarchy = motion_data.joint_hierarchy
        joint_names = motion_data.joint_names

        # 階層構造が存在するか判定
        has_hierarchy = bool(hierarchy) and any(
            parent != joint_names[0] for parent in hierarchy.values()
        )

        if has_hierarchy:
            self._export_bvh_hierarchical(motion_data, output_path)
        else:
            self._export_bvh_flat(motion_data, output_path)

    def _export_bvh_hierarchical(self, motion_data: Motion3DData, output_path: str) -> None:
        """階層構造付きBVH出力."""
        hierarchy = motion_data.joint_hierarchy
        joint_names = motion_data.joint_names

        # ルートを特定
        root = joint_names[0]

        # 子ノードのマッピングを構築
        children: Dict[str, List[str]] = {name: [] for name in joint_names}
        for child, parent in hierarchy.items():
            if parent in children:
                children[parent].append(child)

        # 関節の順序を定義（BVH出力用）
        ordered_joints: List[str] = []

        def _collect_order(joint: str) -> None:
            ordered_joints.append(joint)
            for child in children.get(joint, []):
                _collect_order(child)

        _collect_order(root)

        # ボーンオフセットを最初のフレームから計算
        first_frame = motion_data.frames[0]
        name_to_idx = {name: i for i, name in enumerate(joint_names)}

        def _bone_offset(child: str, parent: str) -> np.ndarray:
            ci = name_to_idx.get(child, 0)
            pi = name_to_idx.get(parent, 0)
            return first_frame.positions[ci] - first_frame.positions[pi]

        lines: List[str] = ["HIERARCHY"]

        def _write_joint(joint: str, depth: int, is_root: bool = False) -> None:
            indent = "  " * depth
            if is_root:
                lines.append(f"{indent}ROOT {joint}")
            else:
                lines.append(f"{indent}JOINT {joint}")
            lines.append(f"{indent}{{")

            if is_root:
                lines.append(f"{indent}  OFFSET 0.000000 0.000000 0.000000")
                lines.append(f"{indent}  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation")
            else:
                parent = hierarchy.get(joint, root)
                offset = _bone_offset(joint, parent)
                lines.append(f"{indent}  OFFSET {offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}")
                lines.append(f"{indent}  CHANNELS 3 Zrotation Xrotation Yrotation")

            kids = children.get(joint, [])
            if kids:
                for child in kids:
                    _write_joint(child, depth + 1)
            else:
                lines.append(f"{indent}  End Site")
                lines.append(f"{indent}  {{")
                lines.append(f"{indent}    OFFSET 0.000000 0.050000 0.000000")
                lines.append(f"{indent}  }}")

            lines.append(f"{indent}}}")

        _write_joint(root, 0, is_root=True)

        # MOTIONセクション
        lines.append("MOTION")
        lines.append(f"Frames: {len(motion_data.frames)}")
        frame_time = 1.0 / motion_data.fps if motion_data.fps > 0 else 0.033
        lines.append(f"Frame Time: {frame_time:.6f}")

        for frame in motion_data.frames:
            values: List[str] = []
            # ルートの位置
            root_idx = name_to_idx.get(root, 0)
            pos = frame.positions[root_idx]
            values.extend([f"{pos[0]:.6f}", f"{pos[1]:.6f}", f"{pos[2]:.6f}"])

            # 全関節の回転（ZXY Euler）
            for joint in ordered_joints:
                idx = name_to_idx.get(joint, 0)
                q = frame.rotations[idx]  # [w, x, y, z]
                euler = self._quaternion_to_euler_zxy(q)
                values.extend([f"{euler[0]:.6f}", f"{euler[1]:.6f}", f"{euler[2]:.6f}"])

            lines.append(" ".join(values))

        Path(output_path).write_text("\n".join(lines))

    def _export_bvh_flat(self, motion_data: Motion3DData, output_path: str) -> None:
        """フラット構造BVH出力（既存互換）."""
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

    @staticmethod
    def _quaternion_to_euler_zxy(q: np.ndarray) -> np.ndarray:
        """クォータニオン[w,x,y,z]をZXY Euler角（度）に変換."""
        w, x, y, z = q[0], q[1], q[2], q[3]

        # ZXY回転順序
        sinx = 2.0 * (w * x + y * z)
        cosx = 1.0 - 2.0 * (x * x + y * y)
        rx = np.arctan2(sinx, cosx)

        siny = 2.0 * (w * y - z * x)
        siny = np.clip(siny, -1.0, 1.0)
        ry = np.arcsin(siny)

        sinz = 2.0 * (w * z + x * y)
        cosz = 1.0 - 2.0 * (y * y + z * z)
        rz = np.arctan2(sinz, cosz)

        return np.degrees(np.array([rz, rx, ry]))

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
