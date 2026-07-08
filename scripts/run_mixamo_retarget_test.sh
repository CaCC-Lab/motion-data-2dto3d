#!/usr/bin/env bash
# Mixamo / ヒューマノイド FBX への BVH リターゲットスモークテスト
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TARGET_FBX="${1:-${MIXAMO_FBX:-data/benchmark/fixtures/mixamo_test_rig.fbx}}"
BVH="${2:-${BVH:-data/output/kitty_tshirt.bvh}}"
OUT_DIR="${OUT_DIR:-data/benchmark/output}"
OUT_FBX="$OUT_DIR/mixamo_retarget.fbx"
OUT_BLEND="$OUT_DIR/mixamo_retarget.blend"

mkdir -p "$OUT_DIR"

if [[ ! -f "$TARGET_FBX" ]]; then
  echo "Target FBX not found: $TARGET_FBX"
  echo ""
  echo "Mixamo から FBX を取得する手順: docs/mixamo-retarget-guide.md"
  echo "またはテストリグを生成:"
  echo "  blender --background --python blender_scripts/create_mixamo_test_rig.py -- \\"
  echo "    --output data/benchmark/fixtures/mixamo_test_rig.fbx"
  exit 1
fi

if [[ ! -f "$BVH" ]]; then
  echo "BVH not found: $BVH"
  echo "例: python -m video_motion_extraction.cli data/input/test_clip.mp4 -o /tmp/out.bvh -f bvh"
  exit 1
fi

BLENDER="${BLENDER_PATH:-$(command -v blender)}"
if [[ -z "$BLENDER" ]]; then
  echo "Blender not found. Set BLENDER_PATH."
  exit 1
fi

echo "=== Mixamo Retarget Test ==="
echo "BVH:    $BVH"
echo "Target: $TARGET_FBX"
echo "Blender: $BLENDER"
echo ""

"$BLENDER" --background --python blender_scripts/retarget_bvh_to_mixamo.py -- \
  --bvh "$BVH" \
  --target-fbx "$TARGET_FBX" \
  --output-fbx "$OUT_FBX" \
  --output-blend "$OUT_BLEND"

echo ""
echo "SUCCESS"
echo "  FBX:   $OUT_FBX ($(du -h "$OUT_FBX" | cut -f1))"
echo "  Blend: $OUT_BLEND ($(du -h "$OUT_BLEND" | cut -f1))"
echo ""
echo "Blender で確認: File > Import > FBX > $OUT_FBX"
