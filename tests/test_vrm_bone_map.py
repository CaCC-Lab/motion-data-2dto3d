"""要件 19: VRoid Studio 以外で作った VRM の骨名対応.

Blender (bpy) は使わない。humanoid は小さな glTF の dict、
GLB はヘッダと JSON チャンクをテストの中で書く。
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from typing import Sequence

import pytest

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from video_motion_extraction import vrm_bone_map as vb  # noqa: E402

# リターゲットが使う 18 本と、VRoid 式の骨名。
_USED = {
    "hips",
    "spine",
    "chest",
    "upperChest",
    "neck",
    "head",
    "leftShoulder",
    "rightShoulder",
    "leftUpperArm",
    "rightUpperArm",
    "leftLowerArm",
    "rightLowerArm",
    "leftUpperLeg",
    "rightUpperLeg",
    "leftLowerLeg",
    "rightLowerLeg",
    "leftFoot",
    "rightFoot",
}

_JBIP = {
    "hips": "J_Bip_C_Hips",
    "spine": "J_Bip_C_Spine",
    "chest": "J_Bip_C_Chest",
    "upperChest": "J_Bip_C_UpperChest",
    "neck": "J_Bip_C_Neck",
    "head": "J_Bip_C_Head",
    "leftShoulder": "J_Bip_L_Shoulder",
    "leftUpperArm": "J_Bip_L_UpperArm",
    "leftLowerArm": "J_Bip_L_LowerArm",
    "leftUpperLeg": "J_Bip_L_UpperLeg",
    "leftLowerLeg": "J_Bip_L_LowerLeg",
    "leftFoot": "J_Bip_L_Foot",
    "rightShoulder": "J_Bip_R_Shoulder",
    "rightUpperArm": "J_Bip_R_UpperArm",
    "rightLowerArm": "J_Bip_R_LowerArm",
    "rightUpperLeg": "J_Bip_R_UpperLeg",
    "rightLowerLeg": "J_Bip_R_LowerLeg",
    "rightFoot": "J_Bip_R_Foot",
}


def _assert_what_why_how(exc: BaseException) -> None:
    """ValueError の文面に what: why: how: が全部ある."""
    message = str(exc)
    missing = [label for label in ("what:", "why:", "how:") if label not in message]
    assert not missing, message


def _write_glb(path: Path, gltf: dict) -> None:
    """glTF 版 2 のヘッダと JSON チャンクだけを持つ GLB を書く."""
    payload = json.dumps(gltf).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    json_chunk = struct.pack("<I", len(payload)) + b"JSON" + payload
    total = 12 + len(json_chunk)
    header = struct.pack("<4sII", b"glTF", 2, total)
    path.write_bytes(header + json_chunk)


def _vrm10(nodes: list, human_bones: dict) -> dict:
    """VRM 1.0。humanBones は {humanoid 名: {"node": 番号}}."""
    return {
        "nodes": nodes,
        "extensions": {"VRMC_vrm": {"humanoid": {"humanBones": human_bones}}},
    }


def _vrm0(nodes: list, human_bones: list) -> dict:
    """VRM 0.x。humanBones は [{"bone": humanoid 名, "node": 番号}]."""
    return {
        "nodes": nodes,
        "extensions": {"VRM": {"humanoid": {"humanBones": human_bones}}},
    }


def _apply_rename_steps(names: Sequence[str], steps: Sequence[tuple]) -> set[str]:
    """名前の集合に steps を順に当て、各手順で衝突が無いことを確かめる.

    各手順の「今の名前」は集合にあり、「新しい名前」は集合に無い。
    """
    current = set(names)
    for step in steps:
        old, new = step
        assert old in current, step
        assert new not in current, step
        current.remove(old)
        current.add(new)
    return current


def test_used_bones_are_the_eighteen_retarget_bones():
    """受け入れ基準 19.1: 対象は体幹 6 本と左右の肩・腕・脚・足の 18 本."""
    assert set(vb.USED_BONES) == _USED
    assert len(list(vb.USED_BONES)) == 18


@pytest.mark.parametrize(("humanoid", "expected"), list(_JBIP.items()))
def test_jbip_name_maps_used_bones(humanoid: str, expected: str):
    """受け入れ基準 19.1: 対象の humanoid 名を VRoid 式の骨名にする."""
    assert vb.jbip_name(humanoid) == expected


@pytest.mark.parametrize("humanoid", ["leftThumbProximal", "leftEye", "jaw"])
def test_jbip_name_ignores_bones_outside_the_eighteen(humanoid: str):
    """受け入れ基準 19.1: 指・目・顎など対象外は対応させない."""
    assert vb.jbip_name(humanoid) is None


@pytest.mark.parametrize(
    ("humanoid", "expected"),
    [
        ("hips", "hips"),
        ("upperChest", "upper_chest"),
        ("leftUpperArm", "left_upper_arm"),
    ],
)
def test_snake_name(humanoid: str, expected: str):
    """VRM アドオンのプロパティ名は snake_case."""
    assert vb.snake_name(humanoid) == expected


def test_humanoid_bones_reads_vrm_1():
    """受け入れ基準 19.2: VRM 1.0 の humanoid 名 → ノード名."""
    gltf = _vrm10(
        [{"name": "hips"}, {"name": "upper_arm.L"}, {"name": "thumb.L"}],
        {
            "hips": {"node": 0},
            "leftUpperArm": {"node": 1},
            "leftThumbProximal": {"node": 2},
        },
    )
    assert vb.humanoid_bones(gltf) == {
        "hips": "hips",
        "leftUpperArm": "upper_arm.L",
        "leftThumbProximal": "thumb.L",
    }


def test_humanoid_bones_reads_vrm_0():
    """受け入れ基準 19.2: VRM 0.x の humanoid 名 → ノード名."""
    gltf = _vrm0(
        [{"name": "hips"}, {"name": "upper_arm.L"}, {"name": "thumb.L"}],
        [
            {"bone": "hips", "node": 0},
            {"bone": "leftUpperArm", "node": 1},
            {"bone": "leftThumbProximal", "node": 2},
        ],
    )
    assert vb.humanoid_bones(gltf) == {
        "hips": "hips",
        "leftUpperArm": "upper_arm.L",
        "leftThumbProximal": "thumb.L",
    }


def test_humanoid_bones_rejects_missing_vrm_extension():
    """受け入れ基準 19.3: VRM の拡張が無い."""
    gltf = {"nodes": [{"name": "hips"}]}
    with pytest.raises(ValueError) as exc_info:
        vb.humanoid_bones(gltf)
    _assert_what_why_how(exc_info.value)


def test_humanoid_bones_rejects_node_without_name():
    """受け入れ基準 19.3: humanoid の骨が、名前の無いノードを指す."""
    gltf = _vrm10([{"name": "spine"}, {}], {"hips": {"node": 1}})
    with pytest.raises(ValueError) as exc_info:
        vb.humanoid_bones(gltf)
    _assert_what_why_how(exc_info.value)


def test_humanoid_bones_rejects_duplicate_node_name():
    """受け入れ基準 19.3: 同名ノードの一方を humanoid の骨が指す."""
    gltf = _vrm10(
        [{"name": "Bone"}, {"name": "Bone"}],
        {"hips": {"node": 0}},
    )
    with pytest.raises(ValueError) as exc_info:
        vb.humanoid_bones(gltf)
    _assert_what_why_how(exc_info.value)


def test_humanoid_bones_rejects_node_index_out_of_range():
    """受け入れ基準 19.3: ノード番号が nodes の範囲外."""
    gltf = _vrm10([{"name": "hips"}], {"hips": {"node": 1}})
    with pytest.raises(ValueError) as exc_info:
        vb.humanoid_bones(gltf)
    _assert_what_why_how(exc_info.value)


def test_read_gltf_json_reads_glb(tmp_path: Path):
    """受け入れ基準 19.4: GLB の JSON チャンクを dict で返す."""
    gltf = {
        "asset": {"version": "2.0"},
        "nodes": [{"name": "hips"}, {"name": "spine"}],
    }
    path = tmp_path / "avatar.vrm"
    _write_glb(path, gltf)
    assert vb.read_gltf_json(path) == gltf


def test_read_gltf_json_rejects_non_glb(tmp_path: Path):
    """受け入れ基準 19.4: 先頭が glTF でないファイル."""
    path = tmp_path / "not-a-model.vrm"
    path.write_bytes(b'{"nodes": [{"name": "hips"}]}')
    with pytest.raises(ValueError) as exc_info:
        vb.read_gltf_json(path)
    _assert_what_why_how(exc_info.value)


def test_rename_map_maps_current_names_and_skips_unused_bones():
    """受け入れ基準 19.1 と 19.5: 今の骨名 → J_Bip_*。対象外は含めない."""
    humanoid = {
        "hips": "hips",
        "upperChest": "chest_upper",
        "leftUpperArm": "upper_arm.L",
        "rightFoot": "foot.R",
        "leftThumbProximal": "thumb.L",
        "leftEye": "eye.L",
        "jaw": "jaw",
    }
    assert vb.rename_map(humanoid) == {
        "hips": "J_Bip_C_Hips",
        "chest_upper": "J_Bip_C_UpperChest",
        "upper_arm.L": "J_Bip_L_UpperArm",
        "foot.R": "J_Bip_R_Foot",
    }


def test_rename_map_skips_bones_already_using_jbip_names():
    """受け入れ基準 19.6: すでに J_Bip_* の骨は付け替えない."""
    humanoid = {
        "hips": "J_Bip_C_Hips",
        "leftUpperArm": "upper_arm.L",
        "jaw": "jaw",
    }
    assert vb.rename_map(humanoid) == {"upper_arm.L": "J_Bip_L_UpperArm"}


def test_rename_map_is_empty_for_vroid_studio_names():
    """受け入れ基準 19.6: VRoid Studio 製（全部が J_Bip_*）では空."""
    humanoid = dict(_JBIP)
    humanoid["leftThumbProximal"] = "J_Bip_L_Thumb1"
    assert vb.rename_map(humanoid) == {}


def test_plan_renames_plain_case():
    """受け入れ基準 19.5: ぶつからない付け替えは、その骨だけが変わる."""
    existing = ["hips", "spine"]
    steps, moved = vb.plan_renames({"hips": "J_Bip_C_Hips"}, existing)
    assert _apply_rename_steps(existing, steps) == {"J_Bip_C_Hips", "spine"}
    assert list(moved) == []


def test_plan_renames_when_destination_is_another_rename_target():
    """受け入れ基準 19.5: 付け替え先を、別の付け替え対象が使っている."""
    existing = ["hips", "J_Bip_C_Hips"]
    renames = {"hips": "J_Bip_C_Hips", "J_Bip_C_Hips": "J_Bip_C_Spine"}
    steps, moved = vb.plan_renames(renames, existing)
    assert _apply_rename_steps(existing, steps) == {"J_Bip_C_Hips", "J_Bip_C_Spine"}
    assert list(moved) == []


def test_plan_renames_when_destination_is_an_unrelated_bone():
    """受け入れ基準 19.5: 付け替え先を対象外の骨が使っているときは、先に _orig へよける."""
    existing = ["hips", "J_Bip_C_Hips"]
    steps, moved = vb.plan_renames({"hips": "J_Bip_C_Hips"}, existing)
    names = _apply_rename_steps(existing, steps)
    assert names == {"J_Bip_C_Hips", "J_Bip_C_Hips_orig"}
    assert [(old, new) for old, new in moved] == [
        ("J_Bip_C_Hips", "J_Bip_C_Hips_orig")
    ]


def test_plan_renames_empty_map_does_nothing():
    """付け替え表が空なら、手順もよけた骨も空."""
    steps, moved = vb.plan_renames({}, ["hips", "spine"])
    assert list(steps) == []
    assert list(moved) == []
