#!/usr/bin/env bash
# clip_c 実写撮影ヘルパー（ガイド準拠・8秒）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/data/benchmark/clips/clip_c_walk.mp4}"
DEVICE="${DEVICE:-/dev/video0}"
DURATION="${DURATION:-8}"
FPS="${FPS:-30}"
SIZE="${SIZE:-1920x1080}"

mkdir -p "$(dirname "$OUT")"

if [[ ! -e "$DEVICE" ]]; then
  echo "ERROR: Camera not found: $DEVICE"
  echo ""
  echo "利用可能なデバイス:"
  ls /dev/video* 2>/dev/null || echo "  (なし — WSL では USB カメラのパススルー設定が必要)"
  echo ""
  echo "代替: スマホ撮影後に配置"
  echo "  cp your_walk.mp4 $OUT"
  echo "  python scripts/validate_benchmark_clip.py $OUT --deep"
  exit 1
fi

echo "=== clip_c 撮影 ==="
echo "device=$DEVICE duration=${DURATION}s fps=$FPS size=$SIZE"
echo "出力: $OUT"
echo ""
echo "演技: 2秒立ち → 4〜6歩で前進 → 立ち止まり（docs/benchmark-clips-guide.md）"
echo "録画開始まで 3 秒..."
sleep 3

ffmpeg -y \
  -f v4l2 -framerate "$FPS" -video_size "$SIZE" -i "$DEVICE" \
  -t "$DURATION" \
  -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
  "$OUT"

echo ""
echo "Done: $OUT"
echo "検証: python scripts/validate_benchmark_clip.py $OUT --deep"
echo "ベンチ: python scripts/benchmark_motion.py $OUT --bvh-mode rotation"
