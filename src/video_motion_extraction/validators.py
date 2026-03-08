"""入力検証モジュール."""

import os
from pathlib import Path

from video_motion_extraction import logger
from video_motion_extraction.errors import ValidationError

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 * 1024  # 10GB
MAX_DURATION_SEC = 3600  # 1時間


def _check_path_traversal(path: str, label: str) -> Path:
    """パストラバーサル検証の共通処理."""
    resolved = Path(path).resolve()
    if ".." in Path(path).parts:
        raise ValidationError(f"Path traversal detected in {label}: {path}")
    # 機密ディレクトリへのアクセスを防止
    _DENIED_PREFIXES = ("/etc", "/var", "/usr", "/bin", "/sbin", "/boot", "/dev", "/proc", "/sys")
    resolved_str = str(resolved)
    for prefix in _DENIED_PREFIXES:
        if resolved_str.startswith(prefix):
            raise ValidationError(
                f"{label} targets restricted directory: {resolved_str}"
            )
    return resolved


def validate_video_path(path: str) -> Path:
    """入力ファイルパスの安全性を検証（パストラバーサル防止）."""
    logger.step(
        "validate_video_path",
        context={"path": path},
        ai_todo=["check_traversal", "resolve_path"],
    )
    return _check_path_traversal(path, "input path")


def validate_output_path(path: str) -> Path:
    """出力ファイルパスの安全性を検証（パストラバーサル防止）."""
    logger.step(
        "validate_output_path",
        context={"path": path},
        ai_todo=["check_traversal", "resolve_path"],
    )
    return _check_path_traversal(path, "output path")


def validate_video_format(path: str) -> None:
    """動画フォーマットの検証."""
    logger.step(
        "validate_video_format",
        context={"path": path},
        ai_todo=["check_extension", "verify_readable"],
    )
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"File does not exist: {path}")
    if p.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(f"Unsupported video format: {p.suffix}")


def enforce_resource_limits(
    file_size_bytes: int = 0,
    duration_sec: float = 0,
) -> None:
    """リソース使用量の上限チェック."""
    logger.step(
        "enforce_resource_limits",
        context={"file_size_bytes": file_size_bytes, "duration_sec": duration_sec},
        ai_todo=["check_file_size", "check_duration"],
    )
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"File size {file_size_bytes} exceeds limit {MAX_FILE_SIZE_BYTES}"
        )
    if duration_sec > MAX_DURATION_SEC:
        raise ValidationError(
            f"Duration {duration_sec}s exceeds limit {MAX_DURATION_SEC}s"
        )
