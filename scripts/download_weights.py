#!/usr/bin/env python3
"""VideoPose3D事前学習済みモデル重みのダウンロードスクリプト."""

import hashlib
import sys
import urllib.request
from pathlib import Path

WEIGHTS_URL = "https://dl.fbaipublicfiles.com/video-pose-3d/pretrained_h36m_cpn.bin"
WEIGHTS_DIR = Path(__file__).resolve().parent.parent / "src" / "video_motion_extraction" / "weights"
WEIGHTS_FILE = WEIGHTS_DIR / "pretrained_h36m_cpn.bin"


def download_with_progress(url: str, dest: Path) -> None:
    """プログレス表示付きダウンロード."""
    print(f"Downloading: {url}")
    print(f"Destination: {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)

    response = urllib.request.urlopen(url)
    total = int(response.headers.get("Content-Length", 0))
    downloaded = 0
    block_size = 8192

    with open(dest, "wb") as f:
        while True:
            chunk = response.read(block_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded * 100 / total
                mb = downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                print(f"\r  {mb:.1f}/{total_mb:.1f} MB ({pct:.1f}%)", end="", flush=True)

    print(f"\nDone. File size: {dest.stat().st_size / (1024*1024):.1f} MB")


def main() -> None:
    if WEIGHTS_FILE.exists():
        size_mb = WEIGHTS_FILE.stat().st_size / (1024 * 1024)
        print(f"Weights already exist: {WEIGHTS_FILE} ({size_mb:.1f} MB)")
        print("Delete the file and re-run to download again.")
        return

    download_with_progress(WEIGHTS_URL, WEIGHTS_FILE)

    # 基本的な検証
    size = WEIGHTS_FILE.stat().st_size
    if size < 1_000_000:  # 1MB未満は異常
        print(f"WARNING: Downloaded file is suspiciously small ({size} bytes)")
        sys.exit(1)

    print("Download complete. Weights are ready for use.")


if __name__ == "__main__":
    main()
