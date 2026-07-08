"""Hip/root ボーンの回転推定テスト.

背景:
- BVH rotation モードでは ROOT "Hip" が 6ch (position 3 + rotation 3) を持つ。
- 従来 root rotation は identity 固定で、yaw が動いても全フレーム0だった。
- LHip/RHip + Hip→Thorax から骨盤 yaw を推定するよう修正したため、
  非ゼロの root rotation が出力されることを検証する。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from video_motion_extraction.config import Converter3DConfig  # noqa: E402
from video_motion_extraction.converter_3d import Converter3D  # noqa: E402
from video_motion_extraction.joint_mapping import (  # noqa: E402
    H36M_HIERARCHY,
    H36M_JOINT_NAMES,
)
from video_motion_extraction.models import Motion3DData, Motion3DFrame  # noqa: E402
from video_motion_extraction.quaternion_utils import (  # noqa: E402
    estimate_pelvis_rotation,
    positions_to_quaternions,
)


def _build_h36m_tpose() -> np.ndarray:
    """簡易 H36M T-pose（Y-up）."""
    pos = np.zeros((17, 3), dtype=np.float32)
    pos[0] = [0.0, 0.0, 0.0]    # Hip
    pos[1] = [-0.1, 0.0, 0.0]   # RHip
    pos[2] = [-0.1, -0.4, 0.0]  # RKnee
    pos[3] = [-0.1, -0.8, 0.0]  # RFoot
    pos[4] = [0.1, 0.0, 0.0]    # LHip
    pos[5] = [0.1, -0.4, 0.0]   # LKnee
    pos[6] = [0.1, -0.8, 0.0]   # LFoot
    pos[7] = [0.0, 0.25, 0.0]   # Spine
    pos[8] = [0.0, 0.5, 0.0]    # Thorax
    pos[9] = [0.0, 0.58, 0.0]   # Nose
    pos[10] = [0.0, 0.65, 0.0]  # Head
    pos[11] = [0.2, 0.5, 0.0]   # LShoulder
    pos[12] = [0.4, 0.5, 0.0]   # LElbow
    pos[13] = [0.6, 0.5, 0.0]   # LWrist
    pos[14] = [-0.2, 0.5, 0.0]  # RShoulder
    pos[15] = [-0.4, 0.5, 0.0]  # RElbow
    pos[16] = [-0.6, 0.5, 0.0]  # RWrist
    return pos


def _yaw_matrix(deg: float) -> np.ndarray:
    theta = np.radians(deg)
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)


def test_estimate_pelvis_rotation_identity_at_rest():
    """T-pose では骨盤回転は identity に近い."""
    pos = _build_h36m_tpose()
    q = estimate_pelvis_rotation(pos, H36M_JOINT_NAMES)

    assert q is not None
    assert q.shape == (4,)
    assert np.allclose(q[0], 1.0, atol=1e-5)
    assert np.allclose(q[1:], 0.0, atol=1e-5)


@pytest.mark.parametrize("yaw_deg", [30.0, 45.0, -60.0, 90.0, -135.0])
def test_estimate_pelvis_rotation_recovers_yaw(yaw_deg: float):
    """Y軸回りの yaw を正しく復元する（角度の大きさ一致）."""
    pos = _build_h36m_tpose()
    R = _yaw_matrix(yaw_deg)
    pos_rot = (R @ pos.T).T.astype(np.float32)

    q = estimate_pelvis_rotation(pos_rot, H36M_JOINT_NAMES)
    assert q is not None

    expected_half = np.radians(yaw_deg) / 2.0
    # quaternion sign ambiguity を吸収して比較
    expected_w = abs(np.cos(expected_half))
    expected_y = abs(np.sin(expected_half))

    assert np.isclose(abs(q[0]), expected_w, atol=1e-3)
    assert np.isclose(abs(q[2]), expected_y, atol=1e-3)
    assert abs(q[1]) < 1e-2
    assert abs(q[3]) < 1e-2


def test_positions_to_quaternions_hip_rotation_non_identity():
    """positions_to_quaternions が rotations[0] を identity から更新する."""
    pos = _build_h36m_tpose()
    pos_rot = (_yaw_matrix(60.0) @ pos.T).T.astype(np.float32)

    rots = positions_to_quaternions(pos_rot, H36M_JOINT_NAMES, H36M_HIERARCHY)

    hip_q = rots[0]
    identity = np.array([1.0, 0.0, 0.0, 0.0])
    assert not np.allclose(hip_q, identity, atol=1e-2), (
        f"Hip rotation remained identity: {hip_q}"
    )


def test_estimate_pelvis_rotation_missing_joints_returns_none():
    """LHip/RHip が揃わないケースでは None を返し、例外を出さない."""
    joint_names = ["Hip", "Thorax", "Other"]
    positions = np.array(
        [[0.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.1, 0.1, 0.0]], dtype=np.float32
    )
    assert estimate_pelvis_rotation(positions, joint_names) is None


def _build_yawing_motion(n_frames: int = 10) -> Motion3DData:
    """n_frames かけて骨盤を 0→(n-1)*9° 回転させる合成モーション."""
    frames = []
    for i in range(n_frames):
        R = _yaw_matrix(i * 9.0)
        pos = (R @ _build_h36m_tpose().T).T.astype(np.float32)
        rot = positions_to_quaternions(pos, H36M_JOINT_NAMES, H36M_HIERARCHY)
        frames.append(
            Motion3DFrame(
                frame_id=i,
                positions=pos,
                rotations=rot.astype(np.float32),
            )
        )
    return Motion3DData(
        frames=frames,
        joint_names=list(H36M_JOINT_NAMES),
        joint_hierarchy=dict(H36M_HIERARCHY),
        fps=30.0,
    )


def _parse_bvh_root_rotations(bvh_path: Path) -> np.ndarray:
    """BVH ファイルから ROOT の [Zrot, Xrot, Yrot] 列を抽出 (T, 3)."""
    lines = bvh_path.read_text().splitlines()
    motion_idx = lines.index("MOTION")
    # MOTION, Frames:, Frame Time: の3行の次からがデータ
    data_lines = lines[motion_idx + 3 :]
    rows = []
    for row in data_lines:
        row = row.strip()
        if not row:
            continue
        vals = row.split()
        # CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
        rows.append([float(vals[3]), float(vals[4]), float(vals[5])])
    return np.array(rows)


def test_bvh_rotation_mode_root_rotation_non_zero(tmp_path: Path):
    """rotation モードの BVH で ROOT 回転列が全フレーム0にならない."""
    data = _build_yawing_motion(n_frames=10)
    config = Converter3DConfig(bvh_mode="rotation")
    converter = Converter3D(config=config)

    out_path = tmp_path / "motion_rotation.bvh"
    converter.export(data, str(out_path), "bvh")

    assert out_path.exists()
    root_rots = _parse_bvh_root_rotations(out_path)

    assert root_rots.shape == (10, 3)
    assert not np.allclose(root_rots, 0.0), "All root rotation channels are zero"

    yrot_range = float(np.max(root_rots[:, 2]) - np.min(root_rots[:, 2]))
    assert yrot_range > 30.0, (
        f"Expected root yaw to span >30°, got {yrot_range:.2f}°"
    )


def test_bvh_position_mode_unaffected_by_hip_rotation(tmp_path: Path):
    """position モードは根本的に root rotation を "0 0 0" 固定で出力するため、
    この変更の影響を受けないことを保証する（互換性維持）."""
    data = _build_yawing_motion(n_frames=5)
    config = Converter3DConfig(bvh_mode="position")
    converter = Converter3D(config=config)

    out_path = tmp_path / "motion_position.bvh"
    converter.export(data, str(out_path), "bvh")

    root_rots = _parse_bvh_root_rotations(out_path)
    assert np.allclose(root_rots, 0.0), (
        "position モードでは root rotation は 0 固定であるべき"
    )
