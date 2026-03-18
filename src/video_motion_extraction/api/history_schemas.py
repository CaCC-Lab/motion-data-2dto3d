"""処理履歴のPydanticモデル."""

from typing import Optional

from pydantic import BaseModel


class HistoryEntry(BaseModel):
    """履歴保存用エントリ."""

    job_id: str
    filename: str
    thumbnail_path: Optional[str] = None
    bvh_path: Optional[str] = None
    output_format: str
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    video_fps: Optional[float] = None
    video_duration: Optional[float] = None
    params_json: str
    status: str = "completed"
    processing_log: Optional[str] = None


class HistoryItem(BaseModel):
    """履歴一覧レスポンス用."""

    id: int
    job_id: str
    created_at: str
    filename: str
    thumbnail_path: Optional[str] = None
    bvh_path: Optional[str] = None
    output_format: str
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    video_fps: Optional[float] = None
    video_duration: Optional[float] = None
    params_json: str
    status: str
    processing_log: Optional[str] = None


class HistoryListResponse(BaseModel):
    """履歴一覧レスポンス."""

    items: list[HistoryItem]
    total: int
