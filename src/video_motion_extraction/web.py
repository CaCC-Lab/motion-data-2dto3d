"""vme-web エントリポイント: FastAPI + フロントエンド配信."""

import os

from video_motion_extraction import logger


def main() -> None:
    """Web UI起動."""
    import uvicorn

    from video_motion_extraction.api.app import create_app

    logger.step("web.main", context={}, ai_todo=["launch_fastapi"])

    host = os.environ.get("VME_HOST", "127.0.0.1")
    port = int(os.environ.get("VME_PORT", "7860"))

    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
