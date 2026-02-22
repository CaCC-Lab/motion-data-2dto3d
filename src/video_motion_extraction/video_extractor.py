"""VideoExtractor: 動画フレーム抽出コンポーネント."""

import math
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from video_motion_extraction import logger
from video_motion_extraction.config import ExtractorConfig
from video_motion_extraction.errors import VideoLoadError
from video_motion_extraction.models import VideoMetadata
from video_motion_extraction.validators import validate_video_format, validate_video_path


class VideoExtractor:
    """動画からフレームを抽出するクラス."""

    def __init__(self, config: Optional[ExtractorConfig] = None) -> None:
        self._config = config or ExtractorConfig()
        logger.step(
            "VideoExtractor.__init__",
            context={"config": str(self._config)},
            ai_todo=["initialize_extractor"],
        )

    def extract_frames(
        self, video_path: str, target_fps: Optional[float] = None
    ) -> List[np.ndarray]:
        """動画からフレームを抽出."""
        logger.step(
            "extract_frames",
            context={"video_path": video_path, "target_fps": target_fps},
            ai_todo=["validate_input", "open_video", "extract_at_fps"],
        )
        validated_path = validate_video_path(video_path)
        if not validated_path.exists():
            raise VideoLoadError(f"File not found: {video_path}")

        validate_video_format(video_path)

        cap = cv2.VideoCapture(str(validated_path))
        if not cap.isOpened():
            raise VideoLoadError(f"Cannot open video: {video_path}")

        try:
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if video_fps <= 0 or total_frames <= 0:
                raise VideoLoadError(f"Invalid video metadata: fps={video_fps}, frames={total_frames}")

            effective_fps = target_fps if target_fps and target_fps > 0 else video_fps
            duration = total_frames / video_fps
            expected_frame_count = int(math.floor(duration * effective_fps))

            frame_interval = video_fps / effective_fps
            frames: List[np.ndarray] = []

            for i in range(expected_frame_count):
                frame_idx = int(round(i * frame_interval))
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)

            if not frames:
                raise VideoLoadError(f"No frames extracted from: {video_path}")

            logger.step(
                "extract_frames_done",
                context={"num_frames": len(frames), "target_fps": effective_fps},
                ai_todo=["return_frames"],
            )
            return frames
        finally:
            cap.release()

    def get_video_metadata(self, video_path: str) -> VideoMetadata:
        """動画のメタデータを取得."""
        logger.step(
            "get_video_metadata",
            context={"video_path": video_path},
            ai_todo=["open_video", "read_properties"],
        )
        validated_path = validate_video_path(video_path)
        if not validated_path.exists():
            raise VideoLoadError(f"File not found: {video_path}")

        cap = cv2.VideoCapture(str(validated_path))
        if not cap.isOpened():
            raise VideoLoadError(f"Cannot open video: {video_path}")

        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join(chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4))
            duration = total_frames / fps if fps > 0 else 0.0

            return VideoMetadata(
                width=width,
                height=height,
                fps=fps,
                total_frames=total_frames,
                duration=duration,
                codec=codec,
            )
        finally:
            cap.release()
