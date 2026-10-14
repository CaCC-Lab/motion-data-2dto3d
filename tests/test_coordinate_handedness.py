"""座標系の右手系（要件 8.3〜8.5）のテスト.

カメラ座標（X=右、Y=下、Z=奥）から世界座標（右手系・Y-up、正対時の前方=+Z、
人物の左=+X）への変換は X 軸まわり 180° の回転 ``(x, y, z) → (x, -y, -z)``。
行列式は +1 で、1 軸だけの鏡映ではない。BVH は位置チャンネルと OFFSET を
世界座標のまま書く。
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

# 既定の weights があると Converter3D がモデルを読む。export だけを試す。
_MISSING_WEIGHTS = "__missing_videopose3d_weights__.bin"
_UP = np.array([0.0, 1.0, 0.0], dtype=np.float64)


def _idx(name: str) -> int:
    return H36M_JOINT_NAMES.index(name)


def _camera_to_world(positions: np.ndarray) -> np.ndarray:
    """未実装ならこの呼び出しだけが失敗し、モジュール収集は通す."""
    from video_motion_extraction.converter_3d import camera_to_world

    return camera_to_world(positions)


def _camera_facing_stance() -> np.ndarray:
    """カメラに正対する H36M 立ち姿勢（X=右、Y=下、Z=奥）.

    人物の左（LHip, LShoulder など）は画像の右なので +X。
    頭は上なので Y は Hip より小さい。鼻はカメラ側なので Thorax より Z が小さい。
    骨盤（Hip / LHip / RHip / Thorax）は軸に沿わせ、変換後に identity になるようにする。
    """
    pos = np.zeros((len(H36M_JOINT_NAMES), 3), dtype=np.float64)
    pos[_idx("Hip")] = [0.20, 0.00, 3.00]
    pos[_idx("RHip")] = [0.05, 0.00, 3.00]
    pos[_idx("RKnee")] = [0.05, 0.45, 3.00]
    pos[_idx("RFoot")] = [0.05, 0.90, 3.02]
    pos[_idx("LHip")] = [0.40, 0.00, 3.00]
    pos[_idx("LKnee")] = [0.40, 0.45, 3.00]
    pos[_idx("LFoot")] = [0.40, 0.90, 3.02]
    pos[_idx("Spine")] = [0.20, -0.25, 3.00]
    pos[_idx("Thorax")] = [0.20, -0.50, 3.00]
    pos[_idx("Nose")] = [0.20, -0.58, 2.75]
    pos[_idx("Head")] = [0.20, -0.72, 2.90]
    pos[_idx("LShoulder")] = [0.45, -0.50, 3.00]
    pos[_idx("LElbow")] = [0.65, -0.25, 3.00]
    pos[_idx("LWrist")] = [0.85, 0.00, 3.00]
    pos[_idx("RShoulder")] = [-0.05, -0.50, 3.00]
    pos[_idx("RElbow")] = [-0.25, -0.25, 3.00]
    pos[_idx("RWrist")] = [-0.45, 0.00, 3.00]
    return pos


def _assert_camera_facing(pos: np.ndarray) -> None:
    """フィクスチャがカメラ座標の正対姿勢であること."""
    assert pos[_idx("LHip"), 0] > pos[_idx("RHip"), 0]
    assert pos[_idx("LShoulder"), 0] > pos[_idx("RShoulder"), 0]
    assert pos[_idx("Head"), 1] < pos[_idx("Hip"), 1]
    assert pos[_idx("Nose"), 2] < pos[_idx("Thorax"), 2]


def _world_stance() -> np.ndarray:
    """世界座標の立ち姿勢.

    全関節の X、Hip からの相対 X、親子の OFFSET の X がいずれも 0 ではない。
    0 だと BVH の X 反転を検出できない。
    """
    spec = {
        "Hip": (0.20, 1.00, 0.30),
        "RHip": (0.05, 1.00, 0.28),
        "RKnee": (-0.02, 0.55, 0.34),
        "RFoot": (0.08, 0.10, 0.40),
        "LHip": (0.40, 1.00, 0.32),
        "LKnee": (0.55, 0.55, 0.36),
        "LFoot": (0.48, 0.10, 0.42),
        "Spine": (0.22, 1.25, 0.31),
        "Thorax": (0.18, 1.50, 0.29),
        "Nose": (0.21, 1.62, 0.50),
        "Head": (0.16, 1.75, 0.38),
        "LShoulder": (0.45, 1.48, 0.27),
        "LElbow": (0.70, 1.20, 0.33),
        "LWrist": (0.90, 0.95, 0.37),
        "RShoulder": (-0.06, 1.48, 0.26),
        "RElbow": (-0.28, 1.20, 0.35),
        "RWrist": (-0.50, 0.95, 0.39),
    }
    pos = np.zeros((len(H36M_JOINT_NAMES), 3), dtype=np.float64)
    for name, xyz in spec.items():
        pos[_idx(name)] = xyz
    return pos


def _assert_x_can_detect_flip(frames: list[np.ndarray], hierarchy: dict[str, str]) -> None:
    """絶対 X・Hip 相対 X・親子差分 X が 0 でないことをフィクスチャ側で保証する."""
    hip = _idx("Hip")
    for frame in frames:
        assert np.all(np.abs(frame[:, 0]) > 1e-3)
        if hierarchy is H36M_HIERARCHY or any(
            parent != H36M_JOINT_NAMES[0] for parent in hierarchy.values()
        ):
            relative_x = frame[:, 0] - frame[hip, 0]
            assert np.all(np.abs(relative_x[1:]) > 1e-3)
        for child, parent in hierarchy.items():
            delta_x = frame[_idx(child), 0] - frame[_idx(parent), 0]
            assert abs(delta_x) > 1e-3


def _identity_rotations(num_joints: int) -> np.ndarray:
    rotations = np.zeros((num_joints, 4), dtype=np.float32)
    rotations[:, 0] = 1.0
    return rotations


def _build_motion(
    frames: list[np.ndarray],
    hierarchy: dict[str, str],
) -> Motion3DData:
    motion_frames = [
        Motion3DFrame(
            frame_id=i,
            positions=np.asarray(pos, dtype=np.float64),
            rotations=_identity_rotations(pos.shape[0]),
        )
        for i, pos in enumerate(frames)
    ]
    return Motion3DData(
        frames=motion_frames,
        joint_names=list(H36M_JOINT_NAMES),
        joint_hierarchy=dict(hierarchy),
        fps=30.0,
    )


def _export_bvh(data: Motion3DData, path: Path, bvh_mode: str) -> str:
    converter = Converter3D(
        config=Converter3DConfig(
            bvh_mode=bvh_mode,
            device="cpu",
            weights_path=_MISSING_WEIGHTS,
        )
    )
    converter.export(data, str(path), "bvh")
    return path.read_text(encoding="utf-8")


def _motion_rows(text: str) -> list[list[float]]:
    lines = text.splitlines()
    motion_at = lines.index("MOTION")
    rows: list[list[float]] = []
    for line in lines[motion_at + 3 :]:
        stripped = line.strip()
        if not stripped:
            continue
        rows.append([float(token) for token in stripped.split()])
    return rows


def _channel_layout(text: str) -> list[tuple[str, list[str]]]:
    """HIERARCHY の出現順に (関節名, チャンネル名) を返す."""
    layout: list[tuple[str, list[str]]] = []
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "MOTION":
            break
        if stripped.startswith("ROOT ") or stripped.startswith("JOINT "):
            current = stripped.split(maxsplit=1)[1]
        elif stripped.startswith("CHANNELS ") and current is not None:
            parts = stripped.split()
            count = int(parts[1])
            layout.append((current, parts[2 : 2 + count]))
            current = None
    return layout


def _xyz_by_joint(
    layout: list[tuple[str, list[str]]],
    row: list[float],
) -> dict[str, np.ndarray]:
    """位置チャンネルを持つ関節の XYZ を MOTION 行から取り出す."""
    cursor = 0
    found: dict[str, np.ndarray] = {}
    for name, channels in layout:
        values = row[cursor : cursor + len(channels)]
        cursor += len(channels)
        if {"Xposition", "Yposition", "Zposition"} <= set(channels):
            found[name] = np.array(
                [
                    values[channels.index("Xposition")],
                    values[channels.index("Yposition")],
                    values[channels.index("Zposition")],
                ],
                dtype=np.float64,
            )
    assert cursor == len(row), f"MOTION 列数 {len(row)} がチャンネル定義 {cursor} と一致しない"
    return found


def _offsets(text: str) -> dict[str, np.ndarray]:
    """関節の OFFSET（End Site は除く）を名前で返す."""
    offsets: dict[str, np.ndarray] = {}
    pending: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "MOTION":
            break
        if stripped.startswith("ROOT ") or stripped.startswith("JOINT "):
            pending = stripped.split(maxsplit=1)[1]
        elif stripped.startswith("OFFSET ") and pending is not None:
            _keyword, x_text, y_text, z_text = stripped.split()
            offsets[pending] = np.array(
                [float(x_text), float(y_text), float(z_text)],
                dtype=np.float64,
            )
            pending = None
    return offsets


def _unit(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    assert length > 1e-8
    return vector / length


@pytest.mark.parametrize(
    "positions",
    [
        np.array(
            [
                [1.5, -2.0, 3.25],
                [-4.0, 0.5, -6.0],
                [0.25, 4.0, 0.5],
            ],
            dtype=np.float64,
        ),
        np.array(
            [
                [[1.5, -2.0, 3.25], [-0.5, 0.75, 1.25]],
                [[2.0, 2.0, -3.0], [0.125, -4.5, 8.0]],
            ],
            dtype=np.float64,
        ),
    ],
    ids=["N3", "TN3"],
)
def test_camera_to_world_maps_xyz_to_x_negy_negz(positions: np.ndarray) -> None:
    """(x, y, z) → (x, -y, -z)。(N, 3) と (T, N, 3) で形状を保ち、入力は変えない."""
    source = np.array(positions, dtype=np.float64, copy=True)
    original = source.copy()

    transformed = _camera_to_world(source)

    assert transformed.shape == source.shape
    np.testing.assert_array_equal(source, original)
    expected = original.copy()
    expected[..., 1] *= -1.0
    expected[..., 2] *= -1.0
    np.testing.assert_allclose(transformed, expected, atol=1e-8)


def test_camera_to_world_linear_map_has_determinant_plus_one() -> None:
    """単位ベクトル 3 本の像を並べた行列の行列式は +1（鏡映ではない）."""
    basis = np.eye(3, dtype=np.float64)
    images = _camera_to_world(basis)
    assert images.shape == (3, 3)

    # images[i] = M @ e_i なので、列に並べると線形写像 M になる。
    linear_map = np.column_stack([images[0], images[1], images[2]])
    determinant = float(np.linalg.det(linear_map))
    assert determinant == pytest.approx(1.0, abs=1e-8), (
        f"camera_to_world は鏡映ではなく回転であるべき（det={determinant}, 期待 +1）"
    )
    np.testing.assert_allclose(
        linear_map,
        np.diag([1.0, -1.0, -1.0]),
        atol=1e-8,
    )


def test_facing_camera_keeps_handedness_after_camera_to_world() -> None:
    """正対姿勢は世界座標で前方 +Z・左 +X になり、腰の前方と鼻の向きが一致する."""
    camera = _camera_facing_stance()
    _assert_camera_facing(camera)

    world = _camera_to_world(camera)

    assert world[_idx("LHip"), 0] > world[_idx("RHip"), 0]
    assert world[_idx("LShoulder"), 0] > world[_idx("RShoulder"), 0]
    assert world[_idx("Head"), 1] > world[_idx("Hip"), 1]

    lateral = world[_idx("LHip")] - world[_idx("RHip")]
    forward_from_hips = _unit(np.cross(lateral, _UP))
    assert forward_from_hips[2] > 0.99
    assert abs(forward_from_hips[0]) < 1e-6
    assert abs(forward_from_hips[1]) < 1e-6

    nose_delta = world[_idx("Nose")] - world[_idx("Thorax")]
    nose_horizontal = _unit(np.array([nose_delta[0], 0.0, nose_delta[2]]))
    assert nose_horizontal[2] > 0.99

    agreement = float(np.dot(forward_from_hips, nose_horizontal))
    assert agreement > 0.99, (
        f"腰から出した前方と鼻の水平成分が一致しない（dot={agreement}）"
    )


def test_pelvis_rotation_is_identity_after_camera_to_world() -> None:
    """変換後の正対姿勢を estimate_pelvis_rotation に渡すと identity に近い."""
    from video_motion_extraction.quaternion_utils import estimate_pelvis_rotation

    camera = _camera_facing_stance()
    _assert_camera_facing(camera)
    world = _camera_to_world(camera)

    quaternion = estimate_pelvis_rotation(world, list(H36M_JOINT_NAMES))
    assert quaternion is not None
    assert quaternion.shape == (4,)
    assert np.allclose(quaternion[0], 1.0, atol=1e-4)
    assert np.allclose(quaternion[1:], 0.0, atol=1e-4)


def test_bvh_position_mode_writes_world_positions_without_x_flip(tmp_path: Path) -> None:
    """position モードはルートが Hip、子が (関節 - Hip)。符号まで一致し X は反転しない."""
    base = _world_stance()
    shifted = base + np.array([0.15, -0.05, 0.08], dtype=np.float64)
    frames = [base, shifted]
    _assert_x_can_detect_flip(frames, H36M_HIERARCHY)

    text = _export_bvh(
        _build_motion(frames, dict(H36M_HIERARCHY)),
        tmp_path / "position.bvh",
        bvh_mode="position",
    )
    assert "CHANNELS 3 Xposition Yposition Zposition" in text

    layout = _channel_layout(text)
    rows = _motion_rows(text)
    assert len(rows) == len(frames)
    hip_name = H36M_JOINT_NAMES[0]

    for frame, row in zip(frames, rows):
        written = _xyz_by_joint(layout, row)
        np.testing.assert_allclose(
            written[hip_name],
            frame[_idx(hip_name)],
            atol=1e-5,
            err_msg="ルート位置が positions[Hip] と一致しない",
        )
        for name in H36M_JOINT_NAMES[1:]:
            expected = frame[_idx(name)] - frame[_idx(hip_name)]
            np.testing.assert_allclose(
                written[name],
                expected,
                atol=1e-5,
                err_msg=f"{name} の位置が (関節 - Hip) と一致しない",
            )


def test_bvh_rotation_mode_writes_root_and_offsets_without_x_flip(tmp_path: Path) -> None:
    """rotation モードのルート位置と OFFSET（子 - 親）が世界座標と符号まで一致する."""
    base = _world_stance()
    shifted = base + np.array([0.15, -0.05, 0.08], dtype=np.float64)
    frames = [base, shifted]
    _assert_x_can_detect_flip(frames, H36M_HIERARCHY)

    text = _export_bvh(
        _build_motion(frames, dict(H36M_HIERARCHY)),
        tmp_path / "rotation.bvh",
        bvh_mode="rotation",
    )
    assert "CHANNELS 3 Zrotation Xrotation Yrotation" in text

    layout = _channel_layout(text)
    rows = _motion_rows(text)
    assert len(rows) == len(frames)
    hip_name = H36M_JOINT_NAMES[0]
    for frame, row in zip(frames, rows):
        written = _xyz_by_joint(layout, row)
        np.testing.assert_allclose(
            written[hip_name],
            frame[_idx(hip_name)],
            atol=1e-5,
            err_msg="ルート位置が positions[Hip] と一致しない",
        )

    offsets = _offsets(text)
    rest = frames[0]
    for child, parent in H36M_HIERARCHY.items():
        expected = rest[_idx(child)] - rest[_idx(parent)]
        np.testing.assert_allclose(
            offsets[child],
            expected,
            atol=1e-5,
            err_msg=f"{child} の OFFSET が (子 - 親) と一致しない",
        )


def test_bvh_flat_writes_joint_positions_without_x_flip(tmp_path: Path) -> None:
    """親がすべてルートの flat 出力は、位置が positions と符号まで一致する.

    flat はルートだけが Xposition/Yposition/Zposition を持ち、子は回転チャンネルのみ。
    位置チャンネルがある各関節の MOTION 値が、その関節の positions と符号まで一致する。
    """
    root = H36M_JOINT_NAMES[0]
    hierarchy = {name: root for name in H36M_JOINT_NAMES[1:]}
    base = _world_stance()
    shifted = base + np.array([0.15, -0.05, 0.08], dtype=np.float64)
    frames = [base, shifted]
    _assert_x_can_detect_flip(frames, hierarchy)

    text = _export_bvh(
        _build_motion(frames, hierarchy),
        tmp_path / "flat.bvh",
        bvh_mode="position",
    )
    # 親がすべてルートなので position モードではなく flat ライターになる。
    assert "CHANNELS 3 Xrotation Yrotation Zrotation" in text
    assert "CHANNELS 3 Xposition Yposition Zposition" not in text

    layout = _channel_layout(text)
    rows = _motion_rows(text)
    assert len(rows) == len(frames)

    for frame, row in zip(frames, rows):
        written = _xyz_by_joint(layout, row)
        assert root in written, "flat BVH のルートに位置チャンネルがない"
        for name, xyz in written.items():
            np.testing.assert_allclose(
                xyz,
                frame[_idx(name)],
                atol=1e-4,
                err_msg=f"{name} の位置が positions と一致しない",
            )
