"""統合ワークフローの設定."""

import os
from pathlib import Path

# 外部サービスのURL
T2I3D_API_URL = os.environ.get("T2I3D_API_URL", "http://localhost:8080")
VME_API_URL = os.environ.get("VME_API_URL", "http://localhost:7860")

# Blender実行パス（Windows側）
BLENDER_PATH = os.environ.get(
    "BLENDER_PATH",
    "/mnt/c/Program Files/Blender Foundation/Blender 4.3/blender.exe",
)

# 作業ディレクトリ
WORK_DIR = Path("data/integration")
MODELS_DIR = WORK_DIR / "models"    # GLB/VRMファイル
MOTIONS_DIR = WORK_DIR / "motions"  # BVHファイル
OUTPUT_DIR = WORK_DIR / "output"    # アニメーションGLB/.blend

# Blenderスクリプトディレクトリ
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "blender_scripts"

# Integration APIポート
INTEGRATION_PORT = int(os.environ.get("INTEGRATION_PORT", "8090"))
