"""Integration API サーバー起動."""

import os

import uvicorn

from video_motion_extraction.integration.app import create_integration_app
from video_motion_extraction.integration.config import INTEGRATION_PORT

app = create_integration_app()


def main() -> None:
    """Integration API サーバー起動エントリポイント."""
    host = os.environ.get("INTEGRATION_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=INTEGRATION_PORT)


if __name__ == "__main__":
    main()
