#!/usr/bin/env bash
# ComfyUI GVHMR ベンチ（pixi Python 3.11 経由）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMFYUI_ROOT="${COMFYUI_ROOT:-$HOME/ComfyUI}"
V2MC_PY="${V2MC_PY:-$HOME/.ce/envs/video2motioncapture-nodes/.pixi/envs/default/bin/python}"
FRAME_CAP="${FRAME_CAP:-120}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/data/benchmark/reports}"

if [[ ! -x "$V2MC_PY" ]]; then
  echo "V2MC pixi Python not found: $V2MC_PY"
  echo "Run: ./scripts/setup_comfyui_v2mc.sh"
  exit 1
fi

if [[ $# -eq 0 ]]; then
  set -- "$ROOT/data/input/test_clip.mp4"
fi

echo "=== ComfyUI-V2MC Benchmark ==="
echo "python=$V2MC_PY"
echo "frame_cap=$FRAME_CAP"
echo ""

"$V2MC_PY" "$ROOT/scripts/benchmark_comfyui_v2mc.py" \
  "$@" \
  --comfyui-root "$COMFYUI_ROOT" \
  --frame-cap "$FRAME_CAP" \
  --output-dir "$OUTPUT_DIR"
