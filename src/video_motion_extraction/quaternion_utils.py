"""3D位置→クォータニオン回転計算ユーティリティ."""

from typing import Dict, List

import numpy as np


def _rotation_between_vectors(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """2ベクトル間の回転を[w, x, y, z]クォータニオンとして計算.

    Args:
        v_from: 回転元ベクトル (3,)
        v_to: 回転先ベクトル (3,)

    Returns:
        クォータニオン [w, x, y, z] (4,)
    """
    v_from = v_from / (np.linalg.norm(v_from) + 1e-10)
    v_to = v_to / (np.linalg.norm(v_to) + 1e-10)

    dot = np.clip(np.dot(v_from, v_to), -1.0, 1.0)

    # ほぼ同方向
    if dot > 0.9999:
        return np.array([1.0, 0.0, 0.0, 0.0])

    # ほぼ逆方向
    if dot < -0.9999:
        # 任意の直交軸を見つける
        ortho = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(v_from, ortho)) > 0.9:
            ortho = np.array([0.0, 1.0, 0.0])
        axis = np.cross(v_from, ortho)
        axis = axis / (np.linalg.norm(axis) + 1e-10)
        return np.array([0.0, axis[0], axis[1], axis[2]])

    axis = np.cross(v_from, v_to)
    w = 1.0 + dot
    q = np.array([w, axis[0], axis[1], axis[2]])
    return q / (np.linalg.norm(q) + 1e-10)


def normalize_quaternions(q: np.ndarray) -> np.ndarray:
    """クォータニオンをノルム正規化.

    Args:
        q: (..., 4) クォータニオン配列

    Returns:
        ノルム正規化されたクォータニオン配列
    """
    norms = np.linalg.norm(q, axis=-1, keepdims=True)
    norms = np.where(norms < 1e-10, 1.0, norms)
    return q / norms


def positions_to_quaternions(
    positions: np.ndarray,
    joint_names: List[str],
    hierarchy: Dict[str, str],
) -> np.ndarray:
    """3D位置からクォータニオン回転を計算.

    親→子ベクトルからT-poseとの差分回転を求める。
    ルートジョイントはidentity quaternion。

    Args:
        positions: (N, 3) 1フレームの関節位置
        joint_names: 関節名リスト
        hierarchy: child→parent辞書

    Returns:
        (N, 4) クォータニオン回転 [w, x, y, z]
    """
    num_joints = len(joint_names)
    rotations = np.zeros((num_joints, 4), dtype=np.float32)
    rotations[:, 0] = 1.0  # identity

    # T-poseの参照方向（Y軸上向き）
    ref_dir = np.array([0.0, 1.0, 0.0])

    name_to_idx = {name: i for i, name in enumerate(joint_names)}

    for child_name, parent_name in hierarchy.items():
        if child_name not in name_to_idx or parent_name not in name_to_idx:
            continue
        child_idx = name_to_idx[child_name]
        parent_idx = name_to_idx[parent_name]

        bone_vec = positions[child_idx] - positions[parent_idx]
        bone_len = np.linalg.norm(bone_vec)
        if bone_len < 1e-6:
            continue

        rotations[child_idx] = _rotation_between_vectors(ref_dir, bone_vec)

    return normalize_quaternions(rotations)
