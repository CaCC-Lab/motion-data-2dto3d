"""VRM の humanoid を読み、リターゲットが探す VRoid 式の骨名へ付け替える表を作る（要件 19）.

`blender_scripts/retarget_bvh_to_vrm.py` は骨を VRoid Studio の名前（`J_Bip_C_Hips` など）で探す。
VRoid Studio 以外で作った VRM は骨名が違う（`hips`、`upper_arm.L` など）ので、
VRM に入っている humanoid（どの骨が hips か等の対応表）を使って名前を付け替える。
このモジュールは bpy に依存しない。
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# retarget_bvh_to_vrm.py が名前で探す骨（VRM の humanoid 名）
USED_BONES: Tuple[str, ...] = (
    "hips",
    "spine",
    "chest",
    "upperChest",
    "neck",
    "head",
    *(
        f"{side}{bone}"
        for side in ("left", "right")
        for bone in ("Shoulder", "UpperArm", "LowerArm", "UpperLeg", "LowerLeg", "Foot")
    ),
)


def read_gltf_json(path: Path) -> Dict[str, Any]:
    """.vrm（GLB）の JSON チャンクを読む.

    Args:
        path: VRM ファイルのパス。

    Returns:
        glTF の JSON を dict にしたもの。

    Raises:
        ValueError: GLB でないファイルのとき。
    """
    with open(path, "rb") as f:
        head = f.read(20)
        if len(head) < 20:
            raise ValueError(
                f"what: {path} is not a GLB / why: the file is shorter than a GLB header / how: pass a .vrm file"
            )
        magic, _version, _length = struct.unpack("<4sII", head[:12])
        chunk_length, chunk_type = struct.unpack("<I4s", head[12:])
        if magic != b"glTF" or chunk_type != b"JSON":
            raise ValueError(
                f"what: {path} is not a GLB / why: header is {magic!r} {chunk_type!r} / how: pass a .vrm file"
            )
        return json.loads(f.read(chunk_length))


def humanoid_bones(gltf: Dict[str, Any]) -> Dict[str, str]:
    """humanoid 名 → ノード名. VRM 1.0（`VRMC_vrm`）と 0.x（`VRM`）の両方を読む.

    Blender 上では、VRM アドオンが読み込み時に作る対応表を使うほうが確か
    （ノード名の省略・重複に左右されない）。これはアドオンが無いときの予備。

    Args:
        gltf: glTF の JSON。

    Returns:
        humanoid 名 → ノード名。

    Raises:
        ValueError: VRM の拡張が無い、または humanoid の骨が名前の無いノード・
            名前が重複するノード・存在しないノード番号を指すとき。
    """
    nodes = gltf.get("nodes", [])
    ext = gltf.get("extensions", {})
    if "VRMC_vrm" in ext:
        pairs = [(h, v["node"]) for h, v in ext["VRMC_vrm"]["humanoid"]["humanBones"].items()]
    elif "VRM" in ext:
        pairs = [(b["bone"], b["node"]) for b in ext["VRM"]["humanoid"]["humanBones"]]
    else:
        raise ValueError(
            "what: no VRM humanoid found / why: neither VRMC_vrm nor VRM extension / how: pass a VRM 0.x or 1.0 file"
        )
    names: List[Optional[str]] = [n.get("name") for n in nodes]
    out: Dict[str, str] = {}
    for humanoid, index in pairs:
        if not 0 <= index < len(names):
            raise ValueError(
                f"what: humanoid bone {humanoid} points to node {index} / why: the file has only {len(names)} nodes "
                "/ how: re-export the VRM, its humanoid map is broken"
            )
        name = names[index]
        if not name or names.count(name) > 1:
            raise ValueError(
                f"what: humanoid bone {humanoid} (node {index}) has no unique name "
                "/ why: glTF allows unnamed or duplicate node names "
                "/ how: import with the VRM add-on for Blender, or give the node a unique name"
            )
        out[humanoid] = name
    return out


def jbip_name(humanoid: str) -> Optional[str]:
    """humanoid 名 → VRoid 式の骨名.

    Args:
        humanoid: VRM の humanoid 名（例: `leftUpperArm`）。

    Returns:
        VRoid 式の骨名（例: `J_Bip_L_UpperArm`）。リターゲットが使わない骨は None。
    """
    if humanoid not in USED_BONES:
        return None
    for prefix, side in (("left", "L"), ("right", "R")):
        if humanoid.startswith(prefix):
            return f"J_Bip_{side}_{humanoid[len(prefix):]}"
    return f"J_Bip_C_{humanoid[0].upper()}{humanoid[1:]}"


def snake_name(humanoid: str) -> str:
    """humanoid 名 → VRM アドオンのプロパティ名（`leftUpperArm` → `left_upper_arm`）.

    Args:
        humanoid: VRM の humanoid 名。

    Returns:
        snake_case の名前。
    """
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in humanoid)


def rename_map(humanoid: Dict[str, str]) -> Dict[str, str]:
    """今の骨名 → 付け替え後の骨名.

    Args:
        humanoid: humanoid 名 → 今の骨名。

    Returns:
        リターゲットが使う骨だけの、今の骨名 → VRoid 式の骨名。すでに同じ名前の骨は含めない。
    """
    out: Dict[str, str] = {}
    for h, bone in humanoid.items():
        new = jbip_name(h)
        if new and bone != new:
            out[bone] = new
    return out


def plan_renames(
    renames: Dict[str, str], existing: List[str]
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """骨名を付け替える手順を、途中で名前がぶつからない順に並べる.

    Blender は使用中の名前を付けると末尾に `.001` を足すので、リターゲットが探す名前にならない。
    1. 付け替え先の名前を使っている対象外の骨を `<名前>_orig` へよける
    2. 付け替える骨をいったん仮の名前へ移す
    3. 仮の名前から最終の名前へ移す

    Args:
        renames: 今の骨名 → 新しい骨名（`rename_map` の結果）。
        existing: いまある骨名の一覧。

    Returns:
        (手順, よけた骨)。手順は (今の名前, 新しい名前) のリスト。よけた骨は (元の名前, よけた先) のリスト。
    """
    used = set(existing)
    targets = set(renames.values())
    moved: List[Tuple[str, str]] = []
    for name in existing:
        if name in targets and name not in renames:
            alt = f"{name}_orig"
            while alt in used or alt in targets:
                alt += "_"
            moved.append((name, alt))
            used.add(alt)
    temps: List[str] = []
    for i in range(len(renames)):
        tmp = f"__retarget_tmp_{i}"
        while tmp in used or tmp in targets:
            tmp += "_"
        used.add(tmp)
        temps.append(tmp)
    steps = list(moved)
    steps += [(old, tmp) for old, tmp in zip(renames, temps)]
    steps += [(tmp, new) for tmp, new in zip(temps, renames.values())]
    return steps, moved
