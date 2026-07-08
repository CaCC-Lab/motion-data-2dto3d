"""統合ワークフローのオーケストレーション."""

import threading
import uuid
from pathlib import Path
from typing import Dict, Optional

import httpx

from video_motion_extraction import logger
from video_motion_extraction.integration.blender_runner import (
    retarget_bvh_to_vrm,
    rig_glb_to_vrm,
)
from video_motion_extraction.integration.config import (
    MODELS_DIR,
    MOTIONS_DIR,
    OUTPUT_DIR,
    T2I3D_API_URL,
    VME_API_URL,
)
from video_motion_extraction.integration.schemas import WorkflowRequest, WorkflowStatus

# ワークフロー状態の保持
_workflows: Dict[str, WorkflowStatus] = {}
_workflows_lock = threading.Lock()


def get_workflow(workflow_id: str) -> Optional[WorkflowStatus]:
    """ワークフロー状態を取得."""
    with _workflows_lock:
        wf = _workflows.get(workflow_id)
        return wf.model_copy() if wf else None


def _update_workflow(workflow_id: str, **kwargs) -> None:
    with _workflows_lock:
        if workflow_id in _workflows:
            for k, v in kwargs.items():
                setattr(_workflows[workflow_id], k, v)


def start_workflow(request: WorkflowRequest) -> str:
    """統合ワークフローをバックグラウンドで開始."""
    workflow_id = uuid.uuid4().hex[:12]

    with _workflows_lock:
        _workflows[workflow_id] = WorkflowStatus(
            workflow_id=workflow_id,
            status="pending",
            current_step="initializing",
        )

    # ディレクトリ作成
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MOTIONS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    thread = threading.Thread(
        target=_run_workflow,
        args=(workflow_id, request),
        daemon=True,
    )
    thread.start()
    return workflow_id


def _run_workflow(workflow_id: str, req: WorkflowRequest) -> None:
    """ワークフロー全体を順次実行."""
    logger.step("integration.workflow", context={"workflow_id": workflow_id}, ai_todo=["run"])

    try:
        # === Step 1: 3Dモデル取得 ===
        if req.glb_file_id:
            # GLB直接指定モード
            from video_motion_extraction.integration.routes import get_uploaded_glb
            _update_workflow(workflow_id, status="generating_model", progress=0.0, current_step="GLBファイル読み込み中...")
            uploaded = get_uploaded_glb(req.glb_file_id)
            if not uploaded or not uploaded.exists():
                raise FileNotFoundError(f"Uploaded GLB not found: {req.glb_file_id}")
            glb_path = str(uploaded)
            _update_workflow(workflow_id, progress=0.20, model_glb_url=f"/api/integration/files/{Path(glb_path).name}")
        else:
            # text2image2model APIで生成
            _update_workflow(workflow_id, status="generating_model", progress=0.0, current_step="3Dモデル生成中...")
            glb_path = _generate_3d_model(workflow_id, req)
            _update_workflow(workflow_id, progress=0.25, model_glb_url=f"/api/integration/files/{Path(glb_path).name}")

        # === Step 2: 自動リギング（GLB→VRM） ===
        glb_ext = Path(glb_path).suffix.lower()
        if glb_ext == ".vrm":
            # VRMはリギング済みなのでスキップ
            _update_workflow(workflow_id, status="rigging", progress=0.30, current_step="VRM検出: リギングスキップ")
            vrm_path = glb_path
            _update_workflow(workflow_id, progress=0.45, vrm_path=vrm_path)
        else:
            _update_workflow(workflow_id, status="rigging", progress=0.30, current_step="自動リギング中...")
            vrm_output = MODELS_DIR / f"{workflow_id}.vrm"
            vrm_path = rig_glb_to_vrm(str(glb_path), str(vrm_output))
            _update_workflow(workflow_id, progress=0.45, vrm_path=vrm_path)

        # === Step 3: モーション抽出（motion-data-2dto3d） ===
        _update_workflow(workflow_id, status="extracting_motion", progress=0.50, current_step="モーション抽出中...")

        bvh_path = _extract_motion(workflow_id, req)
        _update_workflow(workflow_id, progress=0.70, bvh_path=bvh_path)

        # === Step 4: リターゲティング（BVH→VRM） ===
        _update_workflow(workflow_id, status="retargeting", progress=0.75, current_step="リターゲティング中...")

        output_glb = str(OUTPUT_DIR / f"{workflow_id}_animation.glb")
        output_blend = str(OUTPUT_DIR / f"{workflow_id}_animation.blend")
        outputs = retarget_bvh_to_vrm(
            bvh_path=bvh_path,
            vrm_path=vrm_path,
            output_glb=output_glb,
            output_blend=output_blend,
        )

        # === Step 5: 完了 ===
        _update_workflow(
            workflow_id,
            status="completed",
            progress=1.0,
            current_step="完了",
            animation_glb_url=f"/api/integration/files/{Path(outputs.get('glb', '')).name}" if "glb" in outputs else None,
            blend_path=outputs.get("blend"),
        )

    except Exception as exc:
        logger.error(
            "integration.workflow",
            what="Workflow failed",
            why=str(exc),
            how="Check logs and external service status",
        )
        _update_workflow(
            workflow_id,
            status="failed",
            current_step="エラー",
            error=str(exc),
        )


def _generate_3d_model(workflow_id: str, req: WorkflowRequest) -> str:
    """text2image2model APIを呼び出して3Dモデルを生成."""
    with httpx.Client(timeout=1800) as client:
        # フルパイプライン: テキスト→画像→3D
        response = client.post(
            f"{T2I3D_API_URL}/api/generate",
            json={
                "prompt": req.prompt,
                "engine_3d": req.engine_3d,
                "checkpoint": "2-Step",
                "remove_background": True,
                "foreground_ratio": 0.85,
                "mc_resolution": 256,
            },
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise RuntimeError(f"3D generation failed: {data.get('error', 'Unknown error')}")

        # GLBファイルをダウンロード
        mesh_glb_url = data.get("mesh_glb_url", "")
        if not mesh_glb_url:
            raise RuntimeError("No GLB URL in response")

        # 相対URLの場合はベースURLを付加
        if mesh_glb_url.startswith("/"):
            mesh_glb_url = f"{T2I3D_API_URL}{mesh_glb_url}"

        glb_response = client.get(mesh_glb_url)
        glb_response.raise_for_status()

        glb_path = MODELS_DIR / f"{workflow_id}.glb"
        glb_path.write_bytes(glb_response.content)
        return str(glb_path)


def _extract_motion(workflow_id: str, req: WorkflowRequest) -> str:
    """motion-data-2dto3d APIを呼び出してBVHモーションを抽出."""
    with httpx.Client(timeout=600) as client:
        # video_idが指定されている場合はそのまま使用
        video_id = req.video_id

        if not video_id and req.video_path:
            # 動画ファイルをアップロード
            video_path = Path(req.video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video not found: {req.video_path}")

            with open(video_path, "rb") as f:
                upload_resp = client.post(
                    f"{VME_API_URL}/api/upload",
                    files={"file": (video_path.name, f, "video/mp4")},
                )
                upload_resp.raise_for_status()
                video_id = upload_resp.json()["video_id"]

        if not video_id:
            raise ValueError("video_id or video_path is required")

        # 処理開始
        process_resp = client.post(
            f"{VME_API_URL}/api/process",
            json={
                "video_id": video_id,
                "fps": req.motion_fps,
                "threshold": 0.3,
                "smoothing": 5,
                "output_format": "bvh",
                "batch_size": 32,
                "bvh_mode": "position",
                "smooth_3d": 1.0,
                "root_motion_scale": 2.5,
            },
        )
        process_resp.raise_for_status()
        job_id = process_resp.json()["job_id"]

        # SSEで完了を待つ（ポーリング方式）
        import time
        while True:
            # SSEではなくポーリングで状態確認
            # （httpxでSSEを扱うのは複雑なため）
            time.sleep(2)
            try:
                bvh_resp = client.get(f"{VME_API_URL}/api/bvh/{job_id}")
                if bvh_resp.status_code == 200:
                    bvh_text = bvh_resp.json()["bvh"]
                    bvh_path = MOTIONS_DIR / f"{workflow_id}.bvh"
                    bvh_path.write_text(bvh_text, encoding="utf-8")
                    return str(bvh_path)
                elif bvh_resp.status_code == 400:
                    # まだ完了していない可能性
                    detail = bvh_resp.json().get("detail", "")
                    if "not completed" in detail.lower():
                        continue
                    raise RuntimeError(f"BVH retrieval failed: {detail}")
            except httpx.HTTPError:
                continue
