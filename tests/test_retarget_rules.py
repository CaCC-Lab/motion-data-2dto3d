"""要件 20: リターゲット後の首の向き.

首の骨を合わせる向きは Thorax → Head の単位ベクトル。
Head が無い、または Thorax と同じ位置なら Thorax → Nose。
Thorax が無い、または使える向きが無いときは None。例外は出さない。
Blender（bpy・mathutils）は使わない。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from video_motion_extraction import retarget_rules as rr  # noqa: E402

# Nose の Z は Head より前。Head があるときは Nose を使わないことの確認に使う。
_THORAX = (0.0, 1.4, 0.0)
_NOSE = (0.0, 1.5, 0.15)
_HEAD = (0.0, 1.65, 0.02)
_ATOL = 1e-9
_KINDS = ("tuple", "list", "ndarray")


def _coord(kind: str, point: tuple) -> tuple | list | np.ndarray:
    """同じ座標を tuple・list・numpy 配列のいずれかで返す."""
    values = (float(point[0]), float(point[1]), float(point[2]))
    if kind == "tuple":
        return values
    if kind == "list":
        return [values[0], values[1], values[2]]
    if kind == "ndarray":
        return np.array(values, dtype=np.float64)
    raise AssertionError(kind)


def _positions(kind: str, joints: dict) -> dict:
    return {name: _coord(kind, point) for name, point in joints.items()}


def _unit(start: tuple, end: tuple) -> tuple:
    delta = np.asarray(end, dtype=np.float64) - np.asarray(start, dtype=np.float64)
    return tuple(float(v) for v in (delta / np.linalg.norm(delta)))


def _assert_unit_direction(actual: object, expected: tuple) -> None:
    assert isinstance(actual, tuple)
    assert len(actual) == 3
    assert np.allclose(actual, expected, rtol=0.0, atol=_ATOL)
    norm = float(np.linalg.norm(np.asarray(actual, dtype=np.float64)))
    assert abs(norm - 1.0) <= _ATOL


@pytest.mark.parametrize("kind", _KINDS)
def test_neck_direction_prefers_thorax_to_head(kind: str) -> None:
    """Thorax・Nose・Head がそろっていれば Thorax → Head（20.1）."""
    positions = _positions(kind, {"Thorax": _THORAX, "Nose": _NOSE, "Head": _HEAD})
    direction = rr.neck_direction(positions)

    _assert_unit_direction(direction, _unit(_THORAX, _HEAD))
    assert not np.allclose(direction, _unit(_THORAX, _NOSE), rtol=0.0, atol=1e-3)


@pytest.mark.parametrize("kind", _KINDS)
def test_neck_direction_uses_nose_when_head_is_missing(kind: str) -> None:
    """Head が無いときは Thorax → Nose（20.2）."""
    positions = _positions(kind, {"Thorax": _THORAX, "Nose": _NOSE})
    direction = rr.neck_direction(positions)

    _assert_unit_direction(direction, _unit(_THORAX, _NOSE))


@pytest.mark.parametrize("kind", _KINDS)
def test_neck_direction_uses_nose_when_head_coincides_with_thorax(kind: str) -> None:
    """Head が Thorax と同じ位置のときは Thorax → Nose（20.2）."""
    positions = _positions(kind, {"Thorax": _THORAX, "Nose": _NOSE, "Head": _THORAX})
    direction = rr.neck_direction(positions)

    _assert_unit_direction(direction, _unit(_THORAX, _NOSE))


@pytest.mark.parametrize("kind", _KINDS)
@pytest.mark.parametrize(
    "joints",
    [
        pytest.param({"Nose": _NOSE, "Head": _HEAD}, id="no-thorax"),
        pytest.param({"Thorax": _THORAX}, id="no-head-no-nose"),
        pytest.param(
            {"Thorax": _THORAX, "Nose": _THORAX, "Head": _THORAX},
            id="head-and-nose-coincide-with-thorax",
        ),
    ],
)
def test_neck_direction_returns_none_without_raising(kind: str, joints: dict) -> None:
    """使える向きが無いときは None。例外は出さない（20.3）."""
    assert rr.neck_direction(_positions(kind, joints)) is None


def test_neck_direction_same_result_for_tuple_list_and_ndarray() -> None:
    """座標が tuple・list・numpy 配列のどれでも同じ単位ベクトルになる."""
    joints = {"Thorax": _THORAX, "Nose": _NOSE, "Head": _HEAD}
    results = [rr.neck_direction(_positions(kind, joints)) for kind in _KINDS]
    expected = _unit(_THORAX, _HEAD)

    for direction in results:
        _assert_unit_direction(direction, expected)
    assert results[0] == pytest.approx(results[1], abs=_ATOL, rel=0)
    assert results[1] == pytest.approx(results[2], abs=_ATOL, rel=0)
