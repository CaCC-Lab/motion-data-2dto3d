"""FastAPI APIエンドポイント."""

import asyncio
import json
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from video_motion_extraction.api.pipeline_runner import (
    get_job,
    get_video_path,
    register_video,
    start_processing,
)
from video_motion_extraction.api.schemas import (
    ProcessingRequest,
    ProcessResponse,
    UploadResponse,
    VideoInfoResponse,
)
from video_motion_extraction.validators import ALLOWED_VIDEO_EXTENSIONS
from video_motion_extraction.video_extractor import VideoExtractor

router = APIRouter(prefix="/api")

# アップロード先ディレクトリ
_upload_dir = Path(tempfile.mkdtemp(prefix="vme_uploads_"))

# VideoExtractorはステートレスなのでモジュールレベルで再利用
_video_extractor = VideoExtractor()

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
CHUNK_SIZE = 8192


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile):
    """動画アップロード → video_id 返却."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}",
        )

    # アップロードごとに一意なファイル名を生成（同名上書き防止）
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).name}"
    dest = _upload_dir / safe_name

    # ストリーミング書き込み＋サイズチェック（メモリ枯渇防止）
    size = 0
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large (max 500MB)")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")

    video_id = register_video(dest)
    return UploadResponse(video_id=video_id, filename=safe_name)


@router.get("/video/{video_id}/info", response_model=VideoInfoResponse)
async def get_video_info(video_id: str):
    """動画メタデータ取得."""
    video_path = get_video_path(video_id)
    if not video_path or not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        meta = _video_extractor.get_video_metadata(str(video_path))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to read video metadata: {exc}",
        )

    return VideoInfoResponse(
        video_id=video_id,
        width=meta.width,
        height=meta.height,
        fps=meta.fps,
        total_frames=meta.total_frames,
        duration=meta.duration,
        codec=meta.codec,
    )


@router.post("/process", response_model=ProcessResponse)
async def process_video(request: ProcessingRequest):
    """パイプライン実行開始 → job_id 返却."""
    video_path = get_video_path(request.video_id)
    if not video_path or not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    job_id = start_processing(video_path=str(video_path), request=request)
    return ProcessResponse(job_id=job_id)


@router.get("/jobs/{job_id}/status")
async def job_status_sse(job_id: str):
    """SSEで進捗ストリーミング."""

    async def event_generator():
        while True:
            job = get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return

            data = job.model_dump(exclude={"result_file"})
            yield f"data: {json.dumps(data)}\n\n"

            if job.status in ("completed", "failed"):
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs/{job_id}/result")
async def download_result(job_id: str):
    """結果ファイルダウンロード."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.result_file:
        raise HTTPException(status_code=400, detail="Job not completed")

    result_path = Path(job.result_file)
    if not result_path.is_file():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        path=str(result_path),
        filename=result_path.name,
        media_type="application/octet-stream",
    )


@router.get("/bvh/{job_id}")
async def get_bvh_text(job_id: str):
    """BVHテキスト取得（Three.js用）."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.result_file:
        raise HTTPException(status_code=400, detail="Job not completed")

    result_path = Path(job.result_file)
    if result_path.suffix.lower() != ".bvh":
        raise HTTPException(status_code=400, detail="Result is not BVH format")

    try:
        text = result_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="BVH file not found")
    return {"bvh": text}
