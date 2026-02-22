"""VibeLogger互換のPythonロギングラッパー."""

import json
import logging
from typing import Any, Dict, List, Optional


_logger = logging.getLogger("video_motion_extraction")


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
