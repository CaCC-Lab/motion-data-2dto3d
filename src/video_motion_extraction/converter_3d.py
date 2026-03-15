"""Converter3D: 2D→3D変換コンポーネント."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy.ndimage import gaussian_filter

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

        # 1.5. 信頼度ベースフィルタリング: 低信頼度関節を前フレームで補間
        if self._config.confidence_filter:
            for t in range(len(pose_2d.frames)):
                conf = pose_2d.frames[t].confidence  # (17,)
                low_conf = conf < 0.3
                if t > 0 and np.any(low_conf):
                    kps_2d[t, low_conf] = kps_2d[t - 1, low_conf]

        # 2. COCO→H36M関節順に変換
        kps_h36m = coco_to_h36m_keypoints(kps_2d)  # (T, 17, 2)

        # 3. 正規化: VideoPose3D公式方式（等方スケーリング）
        # 解像度はbounding_boxから取得（フレームサイズ）
        res_w = pose_2d.frames[0].bounding_box.width if pose_2d.frames[0].bounding_box else 1920.0
        res_h = pose_2d.frames[0].bounding_box.height if pose_2d.frames[0].bounding_box else 1080.0

        # 等方スケーリング: 長辺基準で正規化しアスペクト比を保持
        # VideoPose3Dは歪みのない入力を前提としている
        scale = max(res_w, res_h)
        kps_normalized = kps_h36m.copy()
        kps_normalized[:, :, 0] = kps_h36m[:, :, 0] / scale - res_w / (2.0 * scale)
        kps_normalized[:, :, 1] = kps_h36m[:, :, 1] / scale - res_h / (2.0 * scale)

        # Hip中心化（ルートモーション用に2D Hip軌跡を保存）
        hip_center = kps_normalized[:, 0:1, :]  # (T, 1, 2)
        hip_2d_trajectory = hip_center[:, 0, :].copy()  # (T, 2) ルートモーション復元用
        kps_normalized = kps_normalized - hip_center

        # 4. VideoPose3D推論
        t = kps_normalized.shape[0]
        input_2d = kps_normalized.reshape(1, t, 17 * 2).astype(np.float32)
        input_tensor = torch.from_numpy(input_2d).to(self._config.device)

        with torch.no_grad():
            output_3d = self._model(input_tensor)  # (1, T, 17, 3)

        positions_3d = output_3d.cpu().numpy()[0]  # (T, 17, 3)

        # 5. 人体スケールに正規化
        # VideoPose3D出力は正規化入力に対する相対座標。
        # Hip(idx=0)→Head(idx=10)距離で身長を推定し、目標スケールに変換。
        # IQRで外れ値を除外し、安定フレームの中央値を使用。
        # ※ルートモーション加算前に行う（平行移動量を身長に含めないため）
        hip_head_dist = np.linalg.norm(
            positions_3d[:, 10, :] - positions_3d[:, 0, :], axis=1
        )
        q1, q3 = np.percentile(hip_head_dist, [25, 75])
        iqr = q3 - q1
        inlier_mask = (hip_head_dist >= q1 - 1.5 * iqr) & (hip_head_dist <= q3 + 1.5 * iqr)
        inlier_dist = hip_head_dist[inlier_mask]
        body_range = np.median(inlier_dist) if len(inlier_dist) > 0 else np.median(hip_head_dist)
        if body_range > 1e-6:
            target_torso = 0.85  # Hip-Head ≈ 身長の半分
            scale_factor = target_torso / body_range
            positions_3d *= scale_factor

        # 5.1. ルートモーション復元
        # VideoPose3DはHip中心化入力のため、出力はHip相対座標。
        # 保存した2D Hip軌跡を3D出力に再注入して絶対位置を復元する。
        # 単眼カメラの視差圧縮を補正するためスケール係数を適用。
        # 2D X → 3D X（横方向移動）、2D Y → 3D Y（上下移動、Y-down）
        rms = self._config.root_motion_scale
        positions_3d[:, :, 0] += hip_2d_trajectory[:, 0:1] * rms
        positions_3d[:, :, 1] += hip_2d_trajectory[:, 1:2] * rms

        # Y軸反転: VideoPose3Dは Y-down（画像座標系）→ Y-up
        positions_3d[:, :, 1] = -positions_3d[:, :, 1]

        # Y軸を上方向に補正: 最小Y=0（足が地面に接地）
        y_min = np.min(positions_3d[:, :, 1])
        positions_3d[:, :, 1] -= y_min

        # 5.3. グローバル傾き補正
        # VideoPose3Dの単眼深度推定はスパイン方向を正確に復元できず、
        # 全身が垂直から大きく傾くことがある。
        # 全フレーム平均のスパイン方向を計算し、垂直に近づける回転を適用する。
        # Hip(idx=0)とThorax(idx=8)の方向ベクトルで判定。
        hip_positions = positions_3d[:, 0, :]      # (T, 3)
        thorax_positions = positions_3d[:, 8, :]   # (T, 3)
        spine_vectors = thorax_positions - hip_positions  # (T, 3)
        avg_spine = spine_vectors.mean(axis=0)
        avg_spine_norm = avg_spine / (np.linalg.norm(avg_spine) + 1e-8)

        vertical = np.array([0.0, 1.0, 0.0])  # Y-up
        cos_tilt = np.dot(avg_spine_norm, vertical)
        tilt_angle = np.arccos(np.clip(cos_tilt, -1.0, 1.0))
        tilt_deg = np.degrees(tilt_angle)

        if tilt_deg > 8.0:
            # 自然傾斜（8°）を超える場合のみ補正
            natural_lean_rad = np.radians(8.0)
            correction_angle = tilt_angle - natural_lean_rad

            # 回転軸 = spine × vertical
            rot_axis = np.cross(avg_spine_norm, vertical)
            rot_axis_norm = np.linalg.norm(rot_axis)
            if rot_axis_norm <= 1e-6:
                logger.step(
                    "global_tilt_correction",
                    context={
                        "skipped": "antiparallel_spine",
                        "tilt_deg": round(tilt_deg, 1),
                    },
                    ai_todo=["investigate_inverted_skeleton"],
                )
            else:
                rot_axis = rot_axis / rot_axis_norm

                # ロドリゲスの回転公式で全関節を回転
                cos_c = np.cos(correction_angle)
                sin_c = np.sin(correction_angle)
                K = np.array([
                    [0, -rot_axis[2], rot_axis[1]],
                    [rot_axis[2], 0, -rot_axis[0]],
                    [-rot_axis[1], rot_axis[0], 0]
                ])
                R = np.eye(3) + sin_c * K + (1 - cos_c) * (K @ K)

                # Hip中心で回転（ベクトル化）
                hip_pos = positions_3d[:, 0:1, :]  # (T, 1, 3)
                rel = positions_3d - hip_pos
                positions_3d = hip_pos + np.einsum('ij,tkj->tki', R, rel)

                # 接地再調整
                y_min2 = np.min(positions_3d[:, :, 1])
                positions_3d[:, :, 1] -= y_min2

                logger.step(
                    "global_tilt_correction",
                    context={
                        "tilt_deg": round(tilt_deg, 1),
                        "correction_deg": round(np.degrees(correction_angle), 1),
                        "remaining_deg": 8.0,
                    },
                    ai_todo=["verify_visual_quality"],
                )

        # 5.5. 3Dテンポラルスムージング（時間軸のみにガウシアンフィルタ適用）
        if self._config.smooth_3d_sigma > 0:
            positions_3d = gaussian_filter(
                positions_3d, sigma=[self._config.smooth_3d_sigma, 0, 0]
            )
            # スムージングで境界フレームのY座標が負値になる場合があるため再接地
            y_min_post = np.min(positions_3d[:, :, 1])
            if y_min_post < 0:
                positions_3d[:, :, 1] -= y_min_post

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
            ai_todo=["validate_path", "select_format", "write_file"],
        )
        # 出力パスのパストラバーサル検証
        from video_motion_extraction.validators import validate_output_path
        validate_output_path(output_path)

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
            if self._config.bvh_mode == "position":
                self._export_bvh_position(motion_data, output_path)
            else:
                self._export_bvh_hierarchical(motion_data, output_path)
        else:
            self._export_bvh_flat(motion_data, output_path)

    def _export_bvh_position(self, motion_data: Motion3DData, output_path: str) -> None:
        """ポジションベースBVH出力（フラット階層）.

        Blenderのimport_bvhは位置チャンネルを以下のように処理する:
          pose_bone.location = bone_rest_matrix_inv @ (bvh_loc - rest_head_local)
        rest_head_local=OFFSET, bone_rest_matrix=ボーンのレスト回転行列。
        全関節をルート直下にOFFSET=0で配置し、End SiteをY方向に統一すれば
        bone_rest_matrix≈単位行列となり、bvh_locがワールド位置として使える。
        """
        joint_names = motion_data.joint_names
        root = joint_names[0]
        name_to_idx = {name: i for i, name in enumerate(joint_names)}
        root_idx = name_to_idx[root]

        lines: List[str] = ["HIERARCHY", f"ROOT {root}", "{"]
        lines.append("  OFFSET 0.000000 0.000000 0.000000")
        lines.append("  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation")

        # 全子関節をルート直下にOFFSET=0でフラット配置
        for jname in joint_names[1:]:
            lines.append(f"  JOINT {jname}")
            lines.append("  {")
            lines.append("    OFFSET 0.000000 0.000000 0.000000")
            lines.append("    CHANNELS 3 Xposition Yposition Zposition")
            lines.append("    End Site")
            lines.append("    {")
            lines.append("      OFFSET 0.000000 0.100000 0.000000")
            lines.append("    }")
            lines.append("  }")

        lines.append("}")

        # MOTIONセクション
        lines.append("MOTION")
        lines.append(f"Frames: {len(motion_data.frames)}")
        frame_time = 1.0 / motion_data.fps if motion_data.fps > 0 else 0.033
        lines.append(f"Frame Time: {frame_time:.6f}")

        # OFFSET=0, End Site Y方向 → bone_rest_matrix ≈ I
        # Blender処理: pose_loc = bone_rest_matrix_inv @ (bvh_loc - rest_head_local)
        # → pose_loc = bvh_loc (OFFSET=0, matrix=I)
        # 子ボーンはルートにペアレントされるため:
        #   child_world = root_world + pose_loc = root_world + bvh_loc
        # よって: bvh_loc = child_world - root_world（ルート相対位置）
        for frame in motion_data.frames:
            values: List[str] = []
            # ルート: 絶対位置 + 回転(0固定)
            # X反転: BVHインポータのY-up→Z-up変換がXを反転するため補正
            root_pos = frame.positions[root_idx]
            values.extend([f"{-root_pos[0]:.6f}", f"{root_pos[1]:.6f}", f"{root_pos[2]:.6f}"])
            values.extend(["0.000000", "0.000000", "0.000000"])

            # 子関節: ルートからの相対位置
            for jname in joint_names[1:]:
                idx = name_to_idx[jname]
                rel = frame.positions[idx] - root_pos
                values.extend([f"{-rel[0]:.6f}", f"{rel[1]:.6f}", f"{rel[2]:.6f}"])

            lines.append(" ".join(values))

        Path(output_path).write_text("\n".join(lines))

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
            offset = first_frame.positions[ci] - first_frame.positions[pi]
            # X反転: BVHインポータのY-up→Z-up変換がXを反転するため補正
            offset[0] = -offset[0]
            return offset

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
            # ルートの位置（X反転: BVH補正）
            root_idx = name_to_idx.get(root, 0)
            pos = frame.positions[root_idx]
            values.extend([f"{-pos[0]:.6f}", f"{pos[1]:.6f}", f"{pos[2]:.6f}"])

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
            # X反転: BVHインポータのY-up→Z-up変換がXを反転するため補正
            values = [f"{-pos[0]:.4f}", f"{pos[1]:.4f}", f"{pos[2]:.4f}"]
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
