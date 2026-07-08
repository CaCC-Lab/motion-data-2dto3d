#!/usr/bin/env bash
# ベンチマーク用クリップを一括計測（存在するファイルのみ実行）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BVH_MODE="${BVH_MODE:-rotation}"
FPS="${FPS:-30}"
OUTPUT_DIR="${OUTPUT_DIR:-data/benchmark/reports}"

CLIPS=(
  "data/input/test_clip.mp4"
  "data/benchmark/clips/clip_b_turn_90deg.mp4"
  "data/benchmark/clips/clip_c_walk.mp4"
  "data/benchmark/clips/clip_c_jump.mp4"
)

FOUND=()
MISSING=()

for clip in "${CLIPS[@]}"; do
  if [[ -f "$clip" ]]; then
    FOUND+=("$clip")
  else
    MISSING+=("$clip")
  fi
done

echo "=== Motion Benchmark Suite ==="
echo "bvh_mode=$BVH_MODE fps=$FPS output=$OUTPUT_DIR"
echo ""

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "SKIP (not found):"
  for m in "${MISSING[@]}"; do
    echo "  - $m"
  done
  echo ""
  echo "clip_b/c の撮影ガイド: docs/benchmark-clips-guide.md"
  echo ""
fi

if [[ ${#FOUND[@]} -eq 0 ]]; then
  echo "ERROR: No clips found."
  exit 1
fi

python3 scripts/benchmark_motion.py \
  "${FOUND[@]}" \
  --bvh-mode "$BVH_MODE" \
  --fps "$FPS" \
  --output-dir "$OUTPUT_DIR"

echo ""
echo "Done. Reports in $OUTPUT_DIR"
echo "比較表テンプレート: data/benchmark/comparison_template.md"
