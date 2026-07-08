"""3D位置→クォータニオン回転計算ユーティリティ."""

from typing import Dict, List, Optional

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


def _matrix_to_quaternion(m: np.ndarray) -> np.ndarray:
    """3x3 回転行列を [w, x, y, z] クォータニオンに変換（Shepperd 法）."""
    m00, m01, m02 = m[0, 0], m[0, 1], m[0, 2]
    m10, m11, m12 = m[1, 0], m[1, 1], m[1, 2]
    m20, m21, m22 = m[2, 0], m[2, 1], m[2, 2]
    trace = m00 + m11 + m22

    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m21 - m12) / s
        y = (m02 - m20) / s
        z = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = np.sqrt(1.0 + m00 - m11 - m22) * 2.0
        w = (m21 - m12) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m02 + m20) / s
    elif m11 > m22:
        s = np.sqrt(1.0 + m11 - m00 - m22) * 2.0
        w = (m02 - m20) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = np.sqrt(1.0 + m22 - m00 - m11) * 2.0
        w = (m10 - m01) / s
        x = (m02 + m20) / s
        y = (m12 + m21) / s
        z = 0.25 * s

    q = np.array([w, x, y, z], dtype=np.float64)
    return q / (np.linalg.norm(q) + 1e-10)


def estimate_pelvis_rotation(
    positions: np.ndarray,
    joint_names: List[str],
) -> Optional[np.ndarray]:
    """H36M 17関節の位置から骨盤(ルート)の回転クォータニオンを推定.

    yaw を最優先で復元する。LHip-RHip ベクトル(X軸)と Hip→Thorax ベクトル(Y軸)から
    直交基底を作り、世界座標系におけるペルビスのレスト姿勢 (X=left, Y=up, Z=forward)
    からの回転を求める。

    T-pose では LHip/RHip が +X/-X、Thorax が +Y に並ぶことを前提とする。
    Thorax が欠けている場合は Spine で代替。LHip/RHip が揃わない場合は None。

    Args:
        positions: (N, 3) 1フレームの関節位置
        joint_names: 関節名リスト

    Returns:
        [w, x, y, z] クォータニオン (4,)、推定不能なら None
    """
    name_to_idx = {name: i for i, name in enumerate(joint_names)}
    if "LHip" not in name_to_idx or "RHip" not in name_to_idx:
        return None
    if "Hip" not in name_to_idx:
        return None

    lhip = positions[name_to_idx["LHip"]]
    rhip = positions[name_to_idx["RHip"]]
    hip = positions[name_to_idx["Hip"]]

    lateral = lhip - rhip
    lateral_len = float(np.linalg.norm(lateral))
    if lateral_len < 1e-6:
        return None
    x_axis = lateral / lateral_len

    up_source = None
    for candidate in ("Thorax", "Spine", "Neck"):
        if candidate in name_to_idx:
            vec = positions[name_to_idx[candidate]] - hip
            if np.linalg.norm(vec) >= 1e-6:
                up_source = vec
                break
    if up_source is None:
        up_source = np.array([0.0, 1.0, 0.0])

    z_axis = np.cross(x_axis, up_source)
    z_len = float(np.linalg.norm(z_axis))
    if z_len < 1e-6:
        return None
    z_axis = z_axis / z_len

    y_axis = np.cross(z_axis, x_axis)
    y_axis = y_axis / (np.linalg.norm(y_axis) + 1e-10)

    rot_matrix = np.stack([x_axis, y_axis, z_axis], axis=1).astype(np.float64)
    return _matrix_to_quaternion(rot_matrix).astype(np.float32)


def positions_to_quaternions(
    positions: np.ndarray,
    joint_names: List[str],
    hierarchy: Dict[str, str],
) -> np.ndarray:
    """3D位置からクォータニオン回転を計算.

    親→子ベクトルからT-poseとの差分回転を求める。
    ルート(階層に親を持たない関節)はH36M形式なら骨盤向きを推定、
    取れなければidentity quaternion。

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

    # ルート関節の回転推定（H36M 形式のみ）
    # BVH rotation モードでは root の 3ch 回転が欠けるため、骨盤 yaw を復元する
    children_in_hierarchy = set(hierarchy.keys())
    for name, idx in name_to_idx.items():
        if name in children_in_hierarchy:
            continue
        pelvis_q = estimate_pelvis_rotation(positions, joint_names)
        if pelvis_q is not None and name in ("Hip", "hip", "pelvis", "Pelvis"):
            rotations[idx] = pelvis_q

    return normalize_quaternions(rotations)
