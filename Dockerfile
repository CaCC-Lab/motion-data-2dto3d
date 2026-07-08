# Stage 1: フロントエンドビルド
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Pythonランタイム（GPU対応）
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-pip \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 \
    ffmpeg git curl \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python

WORKDIR /app

# PyTorch (CUDA 11.8)
RUN python -m pip install --no-cache-dir \
    torch==2.1.0 torchvision==0.16.0 \
    --index-url https://download.pytorch.org/whl/cu118

# MMPose ecosystem + dependencies
RUN python -m pip install --no-cache-dir openmim && \
    mim install mmengine mmcv==2.1.0 mmdet mmpose && \
    python -m pip install --no-cache-dir xtcocotools chumpy json-tricks munkres

# Application
COPY pyproject.toml .
COPY src/ src/
COPY scripts/ scripts/

# VideoPose3D重みのダウンロード（ローカルに同梱済みならスキップされる）
# DOWNLOAD_WEIGHTS=0 でスキップ可能（オフラインビルド用）
ARG DOWNLOAD_WEIGHTS=1
RUN if [ "$DOWNLOAD_WEIGHTS" = "1" ]; then \
        python scripts/download_weights.py || echo "WARN: VideoPose3D weights download failed"; \
    fi

# フロントエンドビルド結果をコピー
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# PEP 660 editable install対応のためpip/setuptoolsを更新
# （chumpy等の旧式パッケージのインストール後に実行する必要がある）
# numpy<2: torch 2.1.0 / mmcv 2.1.0 はNumPy 1.xビルドのため2.x非互換
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir -e ".[gui,web]" "numpy<2"

# Pre-download MMPose model so first run is fast
RUN python -c "from mmpose.apis import MMPoseInferencer; MMPoseInferencer(pose2d='human', device='cpu')" \
    || echo "WARN: MMPose model pre-download failed, will download on first run"

EXPOSE 7860

ENV VME_HOST=0.0.0.0
ENV VME_PORT=7860

# 本番デフォルト: 推論モデル未ロード時はエラー（スタブへのサイレントフォールバック禁止）
ENV VME_STRICT=1

# ヘルスチェック（gui: Gradioルート / web: /health エンドポイント）
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD sh -c 'if [ "${VME_UI:-gui}" = "web" ]; then curl -fsS "http://localhost:${VME_PORT:-7860}/health" >/dev/null; else curl -fsS "http://localhost:${VME_PORT:-7860}/" >/dev/null; fi' || exit 1

# VME_UI: "gui" (Gradio, default per REQ 15.3/15.5) or "web" (FastAPI+React)
ENV VME_UI=gui
ENTRYPOINT ["sh", "-c", "if [ \"${VME_UI:-gui}\" = \"gui\" ]; then exec python -m video_motion_extraction.gui; elif [ \"${VME_UI:-gui}\" = \"web\" ]; then exec python -m video_motion_extraction.web; else echo \"Invalid VME_UI: ${VME_UI}\"; exit 1; fi"]
