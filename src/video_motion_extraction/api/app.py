"""FastAPIアプリファクトリ."""

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from video_motion_extraction.api.history_db import init_db
from video_motion_extraction.api.pipeline_runner import (
    _history_base,
    _history_bvh_dir,
    _history_db_path,
    _history_thumb_dir,
)
from video_motion_extraction.api.routes import router


def _is_relative_to(path: Path, base: Path) -> bool:
    """Path.is_relative_to の Python 3.8 互換ラッパー."""
    if sys.version_info >= (3, 9):
        return path.is_relative_to(base)
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成."""
    app = FastAPI(
        title="Video Motion Extraction",
        description="動画から3Dモーションデータを抽出するAPI",
        version="0.1.0",
    )

    # CORS（環境変数で設定可能）
    origins_str = os.environ.get(
        "VME_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 履歴ディレクトリとDB初期化
    _history_base.mkdir(parents=True, exist_ok=True)
    _history_bvh_dir.mkdir(parents=True, exist_ok=True)
    _history_thumb_dir.mkdir(parents=True, exist_ok=True)
    init_db(_history_db_path)

    # APIルーター登録
    app.include_router(router)

    # フロントエンドの静的ファイル配信（本番用）
    frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        frontend_dist_resolved = frontend_dist.resolve()

        # /assets を StaticFiles でマウント
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """SPAフォールバック: /api以外をindex.htmlで返す（パストラバーサル対策付き）."""
            # /apiパスはSPAではなくAPIルーターが処理すべき（未定義APIは404に）
            if full_path.startswith("api/") or full_path == "api":
                raise HTTPException(status_code=404, detail="Not found")

            file_path = (frontend_dist / full_path).resolve()
            # パストラバーサル防止: is_relative_toで厳密にチェック
            if not _is_relative_to(file_path, frontend_dist_resolved):
                raise HTTPException(status_code=403, detail="Forbidden")
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(frontend_dist / "index.html"))

    return app
