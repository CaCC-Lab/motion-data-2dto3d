"""FastAPIアプリファクトリ."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from video_motion_extraction.api.routes import router


def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成."""
    app = FastAPI(
        title="Video Motion Extraction",
        description="動画から3Dモーションデータを抽出するAPI",
        version="0.1.0",
    )

    # CORS（開発時Viteプロキシ用）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # APIルーター登録
    app.include_router(router)

    # フロントエンドの静的ファイル配信（本番用）
    frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        # index.htmlフォールバック用のSPA対応
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """SPAフォールバック: APIパス以外は全てindex.htmlを返す."""
            from fastapi.responses import FileResponse

            file_path = frontend_dist / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(frontend_dist / "index.html"))

    return app
