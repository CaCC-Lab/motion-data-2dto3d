"""DataProcessor: データ補完・加工コンポーネント."""

import copy
import fnmatch
from typing import List, Optional

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.ndimage import uniform_filter1d

from video_motion_extraction import logger
from video_motion_extraction.config import ProcessingConfig
from video_motion_extraction.models import Pose2DFrame, Pose2DSequence

INTERPOLATED_CONFIDENCE: float = 0.5


class DataProcessor:
    """ポーズデータの補完・フィルタリング・派生データ算出を行うクラス."""

    def __init__(self, config: Optional[ProcessingConfig] = None) -> None:
        self._config = config or ProcessingConfig()
        logger.step(
            "DataProcessor.__init__",
            context={"config": str(self._config)},
            ai_todo=["initialize_processor"],
        )

    def interpolate_missing(self, pose_data: Pose2DSequence) -> Pose2DSequence:
        """欠損データをスプライン補間で補完."""
        logger.step(
            "interpolate_missing",
            context={"num_frames": len(pose_data.frames), "threshold": self._config.confidence_threshold},
            ai_todo=["identify_missing", "interpolate", "mark_interpolated"],
        )
        threshold = self._config.confidence_threshold
        result = _deep_copy_pose_sequence(pose_data)
        num_frames = len(result.frames)
        num_joints = len(result.joint_names)

        for joint_idx in range(num_joints):
            confidences = np.array(
                [result.frames[f].confidence[joint_idx] for f in range(num_frames)]
            )
            keypoints_x = np.array(
                [result.frames[f].keypoints[joint_idx, 0] for f in range(num_frames)]
            )
            keypoints_y = np.array(
                [result.frames[f].keypoints[joint_idx, 1] for f in range(num_frames)]
            )

            valid_mask = confidences >= threshold
            valid_indices = np.where(valid_mask)[0]
            missing_indices = np.where(~valid_mask)[0]

            if len(missing_indices) == 0:
                continue

            if len(valid_indices) < 2:
                logger.warning(
                    "interpolate_missing",
                    context={
                        "joint_idx": joint_idx,
                        "joint_name": result.joint_names[joint_idx],
                        "valid_count": len(valid_indices),
                    },
                    ai_todo=["skip_interpolation", "preserve_original"],
                )
                for mi in missing_indices:
                    result.frames[mi].confidence[joint_idx] = INTERPOLATED_CONFIDENCE
                continue

            cs_x = CubicSpline(valid_indices, keypoints_x[valid_indices])
            cs_y = CubicSpline(valid_indices, keypoints_y[valid_indices])

            for mi in missing_indices:
                result.frames[mi].keypoints[joint_idx, 0] = float(cs_x(mi))
                result.frames[mi].keypoints[joint_idx, 1] = float(cs_y(mi))
                result.frames[mi].confidence[joint_idx] = INTERPOLATED_CONFIDENCE

        return result

    def remove_joints(
        self, pose_data: Pose2DSequence, joints_to_remove: List[str]
    ) -> Pose2DSequence:
        """不要な関節を削除."""
        logger.step(
            "remove_joints",
            context={"joints_to_remove": joints_to_remove, "current_joints": len(pose_data.joint_names)},
            ai_todo=["match_patterns", "remove_joints", "update_arrays"],
        )
        indices_to_remove = set()
        for pattern in joints_to_remove:
            for idx, name in enumerate(pose_data.joint_names):
                if fnmatch.fnmatch(name, pattern):
                    indices_to_remove.add(idx)

        keep_indices = [i for i in range(len(pose_data.joint_names)) if i not in indices_to_remove]
        new_joint_names = [pose_data.joint_names[i] for i in keep_indices]

        new_frames = []
        for frame in pose_data.frames:
            new_keypoints = frame.keypoints[keep_indices]
            new_confidence = frame.confidence[keep_indices]
            new_frames.append(
                Pose2DFrame(
                    frame_id=frame.frame_id,
                    keypoints=new_keypoints.copy(),
                    confidence=new_confidence.copy(),
                    bounding_box=frame.bounding_box,
                )
            )

        return Pose2DSequence(
            frames=new_frames,
            joint_names=new_joint_names,
            fps=pose_data.fps,
        )

    def smooth_trajectory(
        self, pose_data: Pose2DSequence, window_size: int = 5
    ) -> Pose2DSequence:
        """軌跡のスムージング（均一移動平均フィルタ）."""
        logger.step(
            "smooth_trajectory",
            context={"num_frames": len(pose_data.frames), "window_size": window_size},
            ai_todo=["apply_uniform_filter", "preserve_frame_count"],
        )
        result = _deep_copy_pose_sequence(pose_data)
        num_frames = len(result.frames)
        num_joints = len(result.joint_names)

        if num_frames < 2:
            return result

        for joint_idx in range(num_joints):
            coords_x = np.array(
                [result.frames[f].keypoints[joint_idx, 0] for f in range(num_frames)],
                dtype=np.float64,
            )
            coords_y = np.array(
                [result.frames[f].keypoints[joint_idx, 1] for f in range(num_frames)],
                dtype=np.float64,
            )

            smoothed_x = uniform_filter1d(coords_x, size=window_size, mode="nearest")
            smoothed_y = uniform_filter1d(coords_y, size=window_size, mode="nearest")

            for f in range(num_frames):
                result.frames[f].keypoints[joint_idx, 0] = float(smoothed_x[f])
                result.frames[f].keypoints[joint_idx, 1] = float(smoothed_y[f])

        return result

    def calculate_angular_velocity(
        self, pose_data: Pose2DSequence
    ) -> np.ndarray:
        """角速度の算出."""
        logger.step(
            "calculate_angular_velocity",
            context={"num_frames": len(pose_data.frames)},
            ai_todo=["compute_angles", "compute_velocity", "normalize"],
        )
        num_frames = len(pose_data.frames)
        num_joints = len(pose_data.joint_names)
        fps = pose_data.fps
        dt = 1.0 / fps if fps > 0 else 1.0

        angular_velocities = np.zeros((num_frames - 1, num_joints), dtype=np.float64)

        # 親関節マッピング（ルート関節は自身を親とする）
        parent_idx = list(range(num_joints))  # デフォルト: 自分自身
        # COCO/H36M共通: 関節0がルート。子→親の一般的接続を使用
        # joint_namesから動的にマッピングするのが理想だが、
        # 2Dデータでは親子関係が不明な場合があるため、
        # 隣接関節との相対角度で近似する
        for joint_idx in range(num_joints):
            for f in range(num_frames - 1):
                kp_curr = pose_data.frames[f].keypoints[joint_idx]
                kp_next = pose_data.frames[f + 1].keypoints[joint_idx]

                # ルート関節（parent_idx==自身）は原点基準、
                # それ以外は親関節からの相対角度
                p_idx = parent_idx[joint_idx]
                parent_curr = pose_data.frames[f].keypoints[p_idx]
                parent_next = pose_data.frames[f + 1].keypoints[p_idx]

                angle_curr = np.arctan2(
                    kp_curr[1] - parent_curr[1],
                    kp_curr[0] - parent_curr[0],
                )
                angle_next = np.arctan2(
                    kp_next[1] - parent_next[1],
                    kp_next[0] - parent_next[0],
                )

                diff = angle_next - angle_curr
                angular_velocities[f, joint_idx] = _normalize_angle(diff) / dt

        return angular_velocities


def _normalize_angle(angle: float) -> float:
    """角度を -π 〜 π の範囲に正規化."""
    return float(((angle + np.pi) % (2 * np.pi)) - np.pi)


def _deep_copy_pose_sequence(pose_data: Pose2DSequence) -> Pose2DSequence:
    """Pose2DSequenceのディープコピー."""
    new_frames = []
    for frame in pose_data.frames:
        new_frames.append(
            Pose2DFrame(
                frame_id=frame.frame_id,
                keypoints=frame.keypoints.copy(),
                confidence=frame.confidence.copy(),
                bounding_box=frame.bounding_box,
            )
        )
    return Pose2DSequence(
        frames=new_frames,
        joint_names=list(pose_data.joint_names),
        fps=pose_data.fps,
    )
