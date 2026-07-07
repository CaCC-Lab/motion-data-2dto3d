"""GPUリソース管理: バッチサイズ自動調整とOOMリトライ.

REQ-009 (GPUリソース管理) に対応する共通モジュール。
GPU推論を行うコンポーネント（PoseEstimator, Converter3D）から利用され、
CUDA OOM発生時にバッチサイズを半減させて再試行し、
最小バッチサイズでも失敗する場合は GPUMemoryError を送出する。
"""

from typing import Callable, TypeVar

try:
    import torch

    _TORCH_AVAILABLE = True
except ImportError:  # torchはoptional依存（CPU環境ではインストールされない）
    torch = None  # type: ignore[assignment]
    _TORCH_AVAILABLE = False

from video_motion_extraction import logger
from video_motion_extraction.errors import GPUMemoryError

T = TypeVar("T")

MIN_BATCH_SIZE = 1


def is_gpu_oom_error(exc: BaseException) -> bool:
    """例外がGPUメモリ不足由来かどうかを判定."""
    message = str(exc).lower()
    return "cuda out of memory" in message or "out of memory" in message


def resolve_device(requested: str = "auto") -> str:
    """デバイス文字列を解決する.

    Args:
        requested: "auto" / "cpu" / "cuda" / "cuda:N"

    Returns:
        実際に使用するデバイス文字列。"auto" 指定時はCUDAが利用可能なら
        "cuda"、そうでなければ "cpu" を返す。
    """
    if requested != "auto":
        return requested
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def run_with_batch_retry(
    infer_fn: Callable[[int], T],
    batch_size: int,
) -> T:
    """バッチ推論をOOMリトライ付きで実行する.

    Args:
        infer_fn: batch_size を受け取り推論結果を返す呼び出し可能オブジェクト
        batch_size: 初期バッチサイズ

    Returns:
        infer_fn の戻り値

    Raises:
        GPUMemoryError: 最小バッチサイズでもOOMが発生した場合
    """
    current_batch_size = max(batch_size, MIN_BATCH_SIZE)
    while current_batch_size >= MIN_BATCH_SIZE:
        try:
            return infer_fn(current_batch_size)
        except RuntimeError as exc:
            if not is_gpu_oom_error(exc):
                raise
            logger.warning(
                "gpu_manager.run_with_batch_retry",
                context={"batch_size": current_batch_size, "error": str(exc)},
                ai_todo=["reduce_batch_size", "retry_inference"],
            )
            free_gpu_memory()
            current_batch_size //= 2
            if current_batch_size < MIN_BATCH_SIZE:
                raise GPUMemoryError(
                    f"GPU OOM even at minimum batch size: {exc}"
                ) from exc

    raise GPUMemoryError("GPU memory exhausted after all retry attempts")


def free_gpu_memory() -> None:
    """CUDAキャッシュを解放してリトライ成功率を上げる（torch未導入時は無視）."""
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        torch.cuda.empty_cache()
