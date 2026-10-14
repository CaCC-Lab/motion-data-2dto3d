#!/usr/bin/env bash
# ComfyUI-Video2MotionCapture のセットアップ（ベンチ比較用）
set -euo pipefail

COMFYUI_ROOT="${COMFYUI_ROOT:-$HOME/ComfyUI}"
NODE_DIR="$COMFYUI_ROOT/custom_nodes/ComfyUI-Video2MotionCapture"
REPO_URL="https://github.com/AKASubaz/ComfyUI-Video2MotionCapture.git"

echo "=== ComfyUI-Video2MotionCapture Setup ==="
echo "ComfyUI: $COMFYUI_ROOT"
echo "Node:    $NODE_DIR"
echo ""

if [[ ! -d "$COMFYUI_ROOT" ]]; then
  echo "ERROR: ComfyUI not found at $COMFYUI_ROOT"
  echo "Set COMFYUI_ROOT or install ComfyUI first."
  exit 1
fi

if [[ ! -d "$NODE_DIR/.git" ]]; then
  echo "Cloning..."
  git clone --depth 1 "$REPO_URL" "$NODE_DIR"
else
  echo "Already cloned: $NODE_DIR"
fi

echo ""
echo "Installing Python dependencies..."
# requirements.txt の comfy-env==0.1.79 は PyPI 非公開のため新しめを使用
pip install "comfy-env>=0.3.0"
pip install -r "$NODE_DIR/requirements.txt" || true

echo ""
echo "Downloading models (~3.5GB)..."
cd "$NODE_DIR"
python install.py

echo ""
echo "Done."
echo ""
echo "Next steps (manual benchmark):"
echo "  1. Start ComfyUI: cd $COMFYUI_ROOT && python main.py"
echo "  2. Load workflow: $NODE_DIR/workflows/Video to Animation.json"
echo "  3. Input clips: data/input/test_clip.mp4, data/benchmark/clips/*.mp4"
echo "  4. Record results: data/benchmark/reports/comfyui_<clip>_<date>.md"
echo ""
echo "See docs/motion-benchmark.md section '手動ベンチ（ComfyUI-Video2MotionCapture）'"
