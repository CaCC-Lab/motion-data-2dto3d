"""VibeLogger互換のPythonロギングラッパー."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, List, Optional

_logger = logging.getLogger("video_motion_extraction")
_configured = False

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DEFAULT_LOG_DIR = "logs"
MAX_LOG_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 3


def configure(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """アプリケーションエントリポイント用のロギング初期化（冪等）.

    Args:
        level: ログレベル名。省略時は環境変数 VME_LOG_LEVEL（デフォルト INFO）
        log_file: ログファイルパス。省略時は環境変数 VME_LOG_FILE
            （デフォルト logs/vme.log、空文字でファイル出力無効）
    """
    global _configured
    if _configured:
        return
    _configured = True

    # 再初期化時のハンドラ累積を防止
    _logger.handlers.clear()

    level_name = (level or os.environ.get("VME_LOG_LEVEL", "INFO")).upper()
    _logger.setLevel(getattr(logging, level_name, logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    _logger.addHandler(stream_handler)

    file_path = log_file if log_file is not None else os.environ.get(
        "VME_LOG_FILE", os.path.join(DEFAULT_LOG_DIR, "vme.log")
    )
    if file_path:
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                file_path, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(formatter)
            _logger.addHandler(file_handler)
        except OSError as exc:
            _logger.warning("[logger.configure] file handler unavailable: %s", exc)


def _build_message(operation: str, **kwargs: Any) -> str:
    parts = [f"[{operation}]"]
    for key, value in kwargs.items():
        if value is not None:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def step(
    operation: str,
    *,
    context: Any = None,
    ai_todo: Optional[List[str]] = None,
    **kwargs: Any,
) -> None:
    _logger.info(
        _build_message(operation, context=context, ai_todo=ai_todo, **kwargs)
    )


def warning(
    operation: str,
    *,
    context: Any = None,
    ai_todo: Optional[List[str]] = None,
    **kwargs: Any,
) -> None:
    _logger.warning(
        _build_message(operation, context=context, ai_todo=ai_todo, **kwargs)
    )


def error(
    operation: str,
    *,
    what: Optional[str] = None,
    why: Optional[str] = None,
    how: Optional[str] = None,
    context: Any = None,
    ai_todo: Optional[List[str]] = None,
    **kwargs: Any,
) -> None:
    _logger.error(
        _build_message(
            operation, what=what, why=why, how=how, context=context, ai_todo=ai_todo, **kwargs
        )
    )
