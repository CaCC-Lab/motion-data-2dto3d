"""カスタム例外定義."""


class VideoLoadError(Exception):
    """動画ファイル読み込みエラー."""


class GPUMemoryError(Exception):
    """GPUメモリ不足エラー."""


class ValidationError(Exception):
    """入力検証エラー."""
