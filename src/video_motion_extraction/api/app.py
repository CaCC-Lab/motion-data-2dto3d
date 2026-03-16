"""FastAPIアプリファクトリ."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from video_motion_extraction.api.routes import router


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

    # APIルーター登録
    app.include_router(router)

    # フロントエンドの静的ファイル配信（本番用）
    # パッケージルートからの相対パス
    frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        frontend_dist_resolved = frontend_dist.resolve()

        # /assets を StaticFiles でマウント
        assets_dir = frontend_dist / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """SPAフォールバック: APIパス以外は全てindex.htmlを返す（パストラバーサル対策付き）."""
            file_path = (frontend_dist / full_path).resolve()
            # パストラバーサル防止: 解決後のパスがfrontend_dist以下であることを確認
            if not str(file_path).startswith(str(frontend_dist_resolved)):
                raise HTTPException(status_code=403, detail="Forbidden")
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(frontend_dist / "index.html"))

    return app
