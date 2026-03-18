"""SQLiteベースの処理履歴管理."""

import sqlite3
from pathlib import Path
from typing import Optional

from video_motion_extraction.api.history_schemas import HistoryEntry, HistoryItem

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS processing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    filename TEXT NOT NULL,
    thumbnail_path TEXT,
    bvh_path TEXT,
    output_format TEXT NOT NULL,
    video_width INTEGER,
    video_height INTEGER,
    video_fps REAL,
    video_duration REAL,
    params_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    processing_log TEXT
);
"""


def init_db(db_path: str) -> None:
    """テーブルを作成（存在しなければ）."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_CREATE_TABLE)
        conn.commit()
    finally:
        conn.close()


def save_history(db_path: str, entry: HistoryEntry) -> None:
    """履歴エントリを挿入."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO processing_history
            (job_id, filename, thumbnail_path, bvh_path, output_format,
             video_width, video_height, video_fps, video_duration,
             params_json, status, processing_log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.job_id,
                entry.filename,
                entry.thumbnail_path,
                entry.bvh_path,
                entry.output_format,
                entry.video_width,
                entry.video_height,
                entry.video_fps,
                entry.video_duration,
                entry.params_json,
                entry.status,
                entry.processing_log,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_history(db_path: str, limit: int = 50, offset: int = 0) -> tuple[list[HistoryItem], int]:
    """履歴一覧を新しい順で取得. (items, total) を返す."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) FROM processing_history").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM processing_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        items = [HistoryItem(**dict(row)) for row in rows]
        return items, total
    finally:
        conn.close()


def get_history(db_path: str, job_id: str) -> Optional[HistoryItem]:
    """job_idで単一の履歴を取得."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM processing_history WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        return HistoryItem(**dict(row))
    finally:
        conn.close()


def delete_history(db_path: str, job_id: str) -> bool:
    """履歴を削除. 削除できたらTrue."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "DELETE FROM processing_history WHERE job_id = ?", (job_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
