"""統合ワークフローのAPIエンドポイント."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from video_motion_extraction.integration.blender_runner import (
    retarget_bvh_to_vrm,
    rig_glb_to_vrm,
)
from video_motion_extraction.integration.config import MODELS_DIR, MOTIONS_DIR, OUTPUT_DIR
from video_motion_extraction.integration.schemas import (
    RetargetRequest,
    RigRequest,
    WorkflowRequest,
)
from video_motion_extraction.integration.workflow import get_workflow, start_workflow

# アップロード済みGLBの一時保持
_uploaded_glbs: Dict[str, Path] = {}

router = APIRouter(prefix="/api/integration")


@router.get("/health")
async def integration_health():
    """Integration APIヘルスチェック."""
    from video_motion_extraction.integration.config import BLENDER_PATH
    return {
        "status": "ok",
        "blender_available": Path(BLENDER_PATH).exists(),
    }


@router.post("/upload-glb")
async def upload_glb(file: UploadFile):
    """GLBファイルをアップロード."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".glb", ".gltf", ".vrm"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    glb_id = uuid.uuid4().hex[:12]
    dest = MODELS_DIR / f"{glb_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)
    _uploaded_glbs[glb_id] = dest
    return {"glb_id": glb_id, "filename": file.filename}


def get_uploaded_glb(glb_id: str) -> Optional[Path]:
    """アップロード済みGLBのパスを取得."""
    return _uploaded_glbs.get(glb_id)


@router.post("/workflow")
async def create_workflow(request: WorkflowRequest):
    """統合ワークフローを開始."""
    workflow_id = start_workflow(request)
    return {"workflow_id": workflow_id}


@router.get("/workflow/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """ワークフローの進捗を取得."""
    wf = get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.get("/workflow/{workflow_id}/status")
async def workflow_status_sse(workflow_id: str):
    """SSEでワークフロー進捗をストリーミング."""

    async def event_generator():
        while True:
            wf = get_workflow(workflow_id)
            if not wf:
                yield f"data: {json.dumps({'error': 'Workflow not found'})}\n\n"
                return

            data = wf.model_dump()
            yield f"data: {json.dumps(data)}\n\n"

            if wf.status in ("completed", "failed"):
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/rig")
async def rig_model(request: RigRequest):
    """GLB→VRM自動リギング（単体実行）."""
    glb_path = Path(request.glb_path)
    if not glb_path.exists():
        raise HTTPException(status_code=404, detail="GLB file not found")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    output_vrm = str(MODELS_DIR / f"{glb_path.stem}.vrm")

    try:
        result_path = rig_glb_to_vrm(str(glb_path), output_vrm)
        return {"vrm_path": result_path}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/retarget")
async def retarget_motion(request: RetargetRequest):
    """BVH→VRMリターゲティング（単体実行）."""
    bvh_path = Path(request.bvh_path)
    vrm_path = Path(request.vrm_path)

    if not bvh_path.exists():
        raise HTTPException(status_code=404, detail="BVH file not found")
    if not vrm_path.exists():
        raise HTTPException(status_code=404, detail="VRM file not found")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{bvh_path.stem}_{vrm_path.stem}"
    output_glb = str(OUTPUT_DIR / f"{stem}_animation.glb")
    output_blend = str(OUTPUT_DIR / f"{stem}_animation.blend")

    try:
        outputs = retarget_bvh_to_vrm(
            bvh_path=str(bvh_path),
            vrm_path=str(vrm_path),
            output_glb=output_glb,
            output_blend=output_blend,
        )
        return {
            "animation_glb": outputs.get("glb"),
            "blend_file": outputs.get("blend"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/files/{filename}")
async def serve_file(filename: str):
    """生成ファイルの配信."""
    # 複数ディレクトリを検索
    for directory in [OUTPUT_DIR, MODELS_DIR, MOTIONS_DIR]:
        file_path = directory / filename
        if file_path.is_file():
            # パストラバーサル防止
            try:
                file_path.resolve().relative_to(directory.resolve())
            except ValueError as exc:
                raise HTTPException(status_code=403, detail="Forbidden") from exc

            media_type = "application/octet-stream"
            suffix = file_path.suffix.lower()
            if suffix == ".glb":
                media_type = "model/gltf-binary"
            elif suffix == ".vrm":
                media_type = "application/octet-stream"
            elif suffix == ".blend":
                media_type = "application/x-blender"
            elif suffix == ".bvh":
                media_type = "text/plain"

            return FileResponse(str(file_path), media_type=media_type, filename=filename)

    raise HTTPException(status_code=404, detail="File not found")
