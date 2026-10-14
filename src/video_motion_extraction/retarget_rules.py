"""リターゲットで骨を合わせる向きの決め方（要件 20）.

Blender スクリプト（`blender_scripts/retarget_bvh_to_*.py`）から使う。bpy・mathutils に依存しない。
"""

from __future__ import annotations

import math
from typing import Mapping, Optional, Sequence, Tuple

# 首の骨を合わせる向き。上ほど優先する。
# Nose は首の付け根より前にあり、前を向いていても体幹より大きく前に倒れるので予備に回す
NECK_DIRECTION_JOINTS: Tuple[Tuple[str, str], ...] = (("Thorax", "Head"), ("Thorax", "Nose"))

_EPS = 1e-8


def _unit(start: Sequence[float], end: Sequence[float]) -> Optional[Tuple[float, float, float]]:
    d = [float(end[i]) - float(start[i]) for i in range(3)]
    length = math.sqrt(sum(v * v for v in d))
    if length <= _EPS:
        return None
    return (d[0] / length, d[1] / length, d[2] / length)


def neck_direction(positions: Mapping[str, Sequence[float]]) -> Optional[Tuple[float, float, float]]:
    """首の骨を合わせる向き.

    Args:
        positions: 関節名 → 長さ 3 の座標。

    Returns:
        Thorax → Head の単位ベクトル。Head が無い・Thorax と同じ位置なら Thorax → Nose。
        どちらも使えなければ None。
    """
    for start, end in NECK_DIRECTION_JOINTS:
        if start in positions and end in positions:
            d = _unit(positions[start], positions[end])
            if d is not None:
                return d
    return None
