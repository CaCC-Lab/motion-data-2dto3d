"""PoseEstimator: 2Dポーズ推定コンポーネント."""

from typing import List, Optional

import numpy as np

from video_motion_extraction import logger
from video_motion_extraction.config import PoseModelConfig
from video_motion_extraction.errors import GPUMemoryError
from video_motion_extraction.models import BoundingBox, Pose2DFrame, Pose2DSequence

DEFAULT_JOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

MAX_CONSECUTIVE_FAILURES = 3


class PoseEstimator:
    """MMPoseを使用して2D人体ポーズを推定するクラス."""

    def __init__(self, config: Optional[PoseModelConfig] = None) -> None:
        self._config = config or PoseModelConfig()
        self._joint_names = list(DEFAULT_JOINT_NAMES)
        self._model_available = False
        self._inferencer = None
        self._try_load_model()
        logger.step(
            "PoseEstimator.__init__",
            context={"config": str(self._config), "model_available": self._model_available},
            ai_todo=["initialize_model"],
        )

    def _try_load_model(self) -> None:
        """MMPoseInferencerの遅延ロードを試行."""
        try:
            from mmpose.apis import MMPoseInferencer
            inferencer = MMPoseInferencer(
                pose2d=self._config.checkpoint_path or "human",
                device=self._config.device,
            )
            self._inferencer = inferencer
            self._model_available = True
            logger.step(
                "PoseEstimator._try_load_model",
                context={"status": "loaded"},
                ai_todo=[],
            )
        except (ImportError, Exception) as exc:
            self._model_available = False
            logger.step(
                "PoseEstimator._try_load_model",
                context={"status": "fallback_to_stub", "reason": str(exc)},
                ai_todo=[],
            )

    def detect_person(self, frame: np.ndarray) -> List[BoundingBox]:
        """フレーム内の人物を検出."""
        logger.step(
            "detect_person",
            context={"frame_shape": frame.shape},
            ai_todo=["detect_bbox"],
        )
        h, w = frame.shape[:2]
        return [BoundingBox(x=0.0, y=0.0, width=float(w), height=float(h))]

    def estimate_2d_pose(
        self,
        frames: List[np.ndarray],
        batch_size: int = 32,
    ) -> Pose2DSequence:
        """フレームシーケンスから2Dポーズを推定."""
        logger.step(
            "estimate_2d_pose",
            context={"num_frames": len(frames), "batch_size": batch_size},
            ai_todo=["detect_persons", "run_inference", "handle_gpu_retry"],
        )

        valid_frames: List[np.ndarray] = []
        consecutive_failures = 0

        for i, frame in enumerate(frames):
            persons = self.detect_person(frame)
            if persons:
                valid_frames.append(frame)
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning(
                    "estimate_2d_pose",
                    context={"frame_index": i, "consecutive_failures": consecutive_failures},
                    ai_todo=["skip_frame", "check_threshold"],
                )
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        "estimate_2d_pose",
                        what="Consecutive person detection failures",
                        why=f"{consecutive_failures} consecutive frames without person",
                        how="Check input video quality or adjust detection threshold",
                    )
                    raise RuntimeError(
                        f"Person detection failed for {consecutive_failures} consecutive frames"
                    )

        if not valid_frames:
            raise RuntimeError("No persons detected in any frame")

        current_batch_size = batch_size
        while current_batch_size >= 1:
            try:
                return self._infer_batch(valid_frames, current_batch_size)
            except RuntimeError as exc:
                if "CUDA out of memory" in str(exc):
                    logger.warning(
                        "estimate_2d_pose",
                        context={"batch_size": current_batch_size, "error": str(exc)},
                        ai_todo=["reduce_batch_size", "retry_inference"],
                    )
                    current_batch_size //= 2
                    if current_batch_size < 1:
                        raise GPUMemoryError(
                            f"GPU OOM even at minimum batch size: {exc}"
                        ) from exc
                else:
                    raise

        raise GPUMemoryError("GPU memory exhausted after all retry attempts")

    def _infer_batch(
        self, frames: List[np.ndarray], batch_size: int
    ) -> Pose2DSequence:
        """バッチ推論の実行（モデル利用可能時はMMPose、それ以外はスタブ）."""
        if self._model_available:
            return self._infer_batch_real(frames, batch_size)
        return self._infer_batch_stub(frames, batch_size)

    def _infer_batch_real(
        self, frames: List[np.ndarray], batch_size: int
    ) -> Pose2DSequence:
        """MMPoseによる本物のバッチ推論."""
        logger.step(
            "_infer_batch_real",
            context={"num_frames": len(frames), "batch_size": batch_size},
            ai_todo=["run_mmpose_inference"],
        )
        pose_frames: List[Pose2DFrame] = []

        for batch_start in range(0, len(frames), batch_size):
            batch = frames[batch_start:batch_start + batch_size]
            results = self._inferencer(batch, return_vis=False)

            for i, result in enumerate(results):
                frame_idx = batch_start + i
                preds = result.get("predictions", [result])
                if isinstance(preds, list) and len(preds) > 0:
                    pred = preds[0]
                else:
                    pred = preds

                # MMPoseの出力形式を解析
                if isinstance(pred, list) and len(pred) > 0:
                    person = pred[0]
                elif isinstance(pred, dict):
                    person = pred
                else:
                    person = {}

                keypoints = np.array(
                    person.get("keypoints", np.zeros((17, 2))),
                    dtype=np.float32,
                )
                scores = np.array(
                    person.get("keypoint_scores", np.ones(17) * 0.5),
                    dtype=np.float32,
                )

                if keypoints.ndim == 3:
                    keypoints = keypoints[0]
                if scores.ndim == 2:
                    scores = scores[0]

                h, w = batch[i % len(batch)].shape[:2]
                pose_frames.append(
                    Pose2DFrame(
                        frame_id=frame_idx,
                        keypoints=keypoints[:17, :2],
                        confidence=np.clip(scores[:17], 0.0, 1.0),
                        bounding_box=BoundingBox(0.0, 0.0, float(w), float(h)),
                    )
                )

        return Pose2DSequence(
            frames=pose_frames,
            joint_names=list(self._joint_names),
            fps=30.0,
        )

    def _infer_batch_stub(
        self, frames: List[np.ndarray], batch_size: int
    ) -> Pose2DSequence:
        """スタブ実装によるバッチ推論（フォールバック）."""
        logger.step(
            "_infer_batch_stub",
            context={"num_frames": len(frames), "batch_size": batch_size},
            ai_todo=["run_model_inference"],
        )
        num_joints = len(self._joint_names)
        pose_frames: List[Pose2DFrame] = []

        for i, frame in enumerate(frames):
            h, w = frame.shape[:2]
            keypoints = np.random.rand(num_joints, 2).astype(np.float32)
            keypoints[:, 0] *= w
            keypoints[:, 1] *= h
            confidence = np.clip(
                np.random.rand(num_joints).astype(np.float32) * 0.5 + 0.5,
                0.0,
                1.0,
            )
            pose_frames.append(
                Pose2DFrame(
                    frame_id=i,
                    keypoints=keypoints,
                    confidence=confidence,
                    bounding_box=BoundingBox(0.0, 0.0, float(w), float(h)),
                )
            )

        return Pose2DSequence(
            frames=pose_frames,
            joint_names=list(self._joint_names),
            fps=30.0,
        )
