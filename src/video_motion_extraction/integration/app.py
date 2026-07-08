"""Integration API アプリケーション."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from video_motion_extraction.integration.config import (
    MODELS_DIR,
    MOTIONS_DIR,
    OUTPUT_DIR,
)
from video_motion_extraction.integration.routes import router


def create_integration_app() -> FastAPI:
    """Integration APIアプリケーションを作成."""
    app = FastAPI(
        title="Motion Lab Integration API",
        description="text2image2model × motion-data-2dto3d 統合ワークフロー",
        version="0.1.0",
    )

    # CORS
    origins_str = os.environ.get(
        "INTEGRATION_CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
    )
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 作業ディレクトリ作成
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MOTIONS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ルーター登録
    app.include_router(router)

    @app.get("/health")
    async def health():
        """ヘルスチェック."""
        from pathlib import Path

        from video_motion_extraction.integration.config import BLENDER_PATH
        return {
            "status": "ok",
            "blender_available": Path(BLENDER_PATH).exists(),
            "blender_path": BLENDER_PATH,
        }

    return app
