import importlib
import inspect
import json
import logging
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st


VIDEO_EXTRACTOR_MODULES = [
    "video_motion_extraction.video_extractor",
    "video_motion_extraction",
]
POSE_ESTIMATOR_MODULES = [
    "video_motion_extraction.pose_estimator",
    "video_motion_extraction",
]
DATA_PROCESSOR_MODULES = [
    "video_motion_extraction.data_processor",
    "video_motion_extraction",
]
CONVERTER_3D_MODULES = [
    "video_motion_extraction.converter_3d",
    "video_motion_extraction",
]
MODELS_MODULES = [
    "video_motion_extraction.models",
    "video_motion_extraction",
]
CONFIG_MODULES = [
    "video_motion_extraction.config",
    "video_motion_extraction",
]
VALIDATORS_MODULES = [
    "video_motion_extraction.validators",
    "video_motion_extraction",
]
EXCEPTIONS_MODULES = [
    "video_motion_extraction.errors",
    "video_motion_extraction.exceptions",
    "video_motion_extraction",
]


def try_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise


def resolve_symbol(module_names: Sequence[str], symbol: str):
    seen_module = False
    for module_name in module_names:
        module = try_import(module_name)
        if module is None:
            continue
        seen_module = True
        if hasattr(module, symbol):
            return getattr(module, symbol)
    if seen_module:
        pytest.fail(f"{symbol} not found in any of: {module_names}")
    pytest.skip(f"{symbol} is not available yet")


def optional_symbol(module_names: Sequence[str], symbol: str):
    for module_name in module_names:
        module = try_import(module_name)
        if module is None:
            continue
        if hasattr(module, symbol):
            return getattr(module, symbol)
    return None


def instantiate_with_optional_config(cls, config_names: Sequence[str]):
    for args in ((), (None,)):
        try:
            return cls(*args)
        except TypeError:
            continue
    for config_name in config_names:
        config_cls = optional_symbol(CONFIG_MODULES + MODELS_MODULES, config_name)
        if config_cls is None:
            continue
        try:
            return cls(config_cls())
        except Exception:
            continue
    pytest.skip(f"{cls.__name__} could not be instantiated without config")


def get_extract_frames_callable():
    func = optional_symbol(VIDEO_EXTRACTOR_MODULES, "extract_frames")
    if func is not None:
        return func
    video_extractor = resolve_symbol(VIDEO_EXTRACTOR_MODULES, "VideoExtractor")
    instance = instantiate_with_optional_config(video_extractor, ["ExtractorConfig"])
    return instance.extract_frames


def get_video_extractor_instance():
    video_extractor = resolve_symbol(VIDEO_EXTRACTOR_MODULES, "VideoExtractor")
    return instantiate_with_optional_config(video_extractor, ["ExtractorConfig"])


def get_estimate_pose_callable():
    func = optional_symbol(POSE_ESTIMATOR_MODULES, "estimate_2d_pose")
    if func is not None:
        return func
    estimator_cls = resolve_symbol(POSE_ESTIMATOR_MODULES, "PoseEstimator")
    estimator = instantiate_with_optional_config(estimator_cls, ["PoseModelConfig"])
    return estimator.estimate_2d_pose


def get_pose_estimator_instance():
    estimator_cls = resolve_symbol(POSE_ESTIMATOR_MODULES, "PoseEstimator")
    return instantiate_with_optional_config(estimator_cls, ["PoseModelConfig"])


def get_data_processor_instance(confidence_threshold: Optional[float] = None):
    processor_cls = resolve_symbol(DATA_PROCESSOR_MODULES, "DataProcessor")
    processing_config_cls = optional_symbol(MODELS_MODULES + CONFIG_MODULES, "ProcessingConfig")
    if processing_config_cls is not None:
        if confidence_threshold is None:
            config = processing_config_cls()
        else:
            try:
                config = processing_config_cls(confidence_threshold=confidence_threshold)
            except TypeError:
                config = processing_config_cls()
        try:
            return processor_cls(config)
        except TypeError:
            pass
    return instantiate_with_optional_config(processor_cls, ["ProcessingConfig"])


def get_converter_3d_instance():
    converter_cls = resolve_symbol(CONVERTER_3D_MODULES, "Converter3D")
    return instantiate_with_optional_config(converter_cls, ["Converter3DConfig"])


def build_pose_2d_sequence(
    num_frames: int,
    num_joints: int,
    fps: float = 30.0,
    keypoints: Optional[np.ndarray] = None,
    confidence: Optional[np.ndarray] = None,
):
    pose_sequence_cls = resolve_symbol(MODELS_MODULES, "Pose2DSequence")
    pose_frame_cls = resolve_symbol(MODELS_MODULES, "Pose2DFrame")
    joint_names = [f"joint_{idx}" for idx in range(num_joints)]
    frames = []
    for frame_id in range(num_frames):
        frame_keypoints = (
            keypoints[frame_id]
            if keypoints is not None
            else np.zeros((num_joints, 2), dtype=np.float32)
        )
        frame_confidence = (
            confidence[frame_id]
            if confidence is not None
            else np.ones((num_joints,), dtype=np.float32)
        )
        frames.append(
            pose_frame_cls(
                frame_id=frame_id,
                keypoints=np.asarray(frame_keypoints, dtype=np.float32),
                confidence=np.asarray(frame_confidence, dtype=np.float32),
                bounding_box=None,
            )
        )
    return pose_sequence_cls(frames=frames, joint_names=joint_names, fps=fps)


def build_motion_3d_data(
    num_frames: int,
    num_joints: int,
    fps: float = 30.0,
):
    motion_data_cls = resolve_symbol(MODELS_MODULES, "Motion3DData")
    motion_frame_cls = resolve_symbol(MODELS_MODULES, "Motion3DFrame")
    joint_names = [f"joint_{idx}" for idx in range(num_joints)]
    frames = []
    for frame_id in range(num_frames):
        positions = np.zeros((num_joints, 3), dtype=np.float32)
        rotations = np.zeros((num_joints, 4), dtype=np.float32)
        rotations[:, 0] = 1.0
        frames.append(
            motion_frame_cls(
                frame_id=frame_id,
                positions=positions,
                rotations=rotations,
            )
        )
    return motion_data_cls(
        frames=frames,
        joint_names=joint_names,
        joint_hierarchy={},
        fps=fps,
    )


def pose_keypoints_array(pose_sequence) -> np.ndarray:
    return np.stack([frame.keypoints for frame in pose_sequence.frames], axis=0)


def pose_confidence_array(pose_sequence) -> np.ndarray:
    return np.stack([frame.confidence for frame in pose_sequence.frames], axis=0)


def motion_positions_array(motion_data) -> np.ndarray:
    return np.stack([frame.positions for frame in motion_data.frames], axis=0)


def motion_rotations_array(motion_data) -> np.ndarray:
    return np.stack([frame.rotations for frame in motion_data.frames], axis=0)


def to_angular_velocity_array(angular_velocity_data) -> np.ndarray:
    if isinstance(angular_velocity_data, np.ndarray):
        return angular_velocity_data
    for attr in ("values", "data", "angular_velocities"):
        if hasattr(angular_velocity_data, attr):
            return np.asarray(getattr(angular_velocity_data, attr))
    pytest.fail("Angular velocity output is not array-like")


def create_test_video(
    tmp_path: Path,
    fps: float = 10.0,
    frame_count: int = 10,
    width: int = 64,
    height: int = 48,
) -> Path:
    cv2 = pytest.importorskip("cv2")
    video_path = tmp_path / "sample.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        pytest.skip("OpenCV VideoWriter is not available")
    for _ in range(frame_count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (200, 10, 30)
        writer.write(frame)
    writer.release()
    return video_path


def call_extract_frames(extract_frames, video_path: Path, target_fps: Optional[float] = None):
    signature = inspect.signature(extract_frames)
    if "target_fps" in signature.parameters:
        return extract_frames(str(video_path), target_fps=target_fps)
    return extract_frames(str(video_path))


def max_frame_delta(points: np.ndarray) -> float:
    if points.shape[0] < 2:
        return 0.0
    deltas = np.linalg.norm(np.diff(points, axis=0), axis=-1)
    return float(np.max(deltas))


@st.composite
def pose_sequence_strategy(draw):
    num_frames = draw(st.integers(min_value=2, max_value=10))
    num_joints = draw(st.integers(min_value=1, max_value=6))
    fps = draw(st.floats(min_value=1.0, max_value=60.0, allow_nan=False, allow_infinity=False))
    keypoints = draw(
        st.lists(
            st.lists(
                st.tuples(
                    st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
                    st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
                ),
                min_size=num_joints,
                max_size=num_joints,
            ),
            min_size=num_frames,
            max_size=num_frames,
        )
    )
    confidence = draw(
        st.lists(
            st.lists(
                st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
                min_size=num_joints,
                max_size=num_joints,
            ),
            min_size=num_frames,
            max_size=num_frames,
        )
    )
    return (
        num_frames,
        num_joints,
        fps,
        np.asarray(keypoints, dtype=np.float32),
        np.asarray(confidence, dtype=np.float32),
    )


def build_pose_sequence_from_tuple(data) -> Tuple:
    num_frames, num_joints, fps, keypoints, confidence = data
    pose_sequence = build_pose_2d_sequence(
        num_frames=num_frames,
        num_joints=num_joints,
        fps=float(fps),
        keypoints=keypoints,
        confidence=confidence,
    )
    return num_frames, num_joints, pose_sequence, keypoints, confidence


def resolve_exception(exception_name: str):
    return resolve_symbol(EXCEPTIONS_MODULES + VIDEO_EXTRACTOR_MODULES, exception_name)


def test_req_001_video_extractor_extracts_frames_and_metadata(tmp_path):
    """REQ-001: Video_Extractor extracts frames, metadata, and handles invalid inputs."""
    extract_frames = get_extract_frames_callable()
    video_path = create_test_video(tmp_path, fps=10.0, frame_count=10)

    frames = call_extract_frames(extract_frames, video_path, target_fps=5.0)
    assert isinstance(frames, list)
    assert len(frames) == 5
    frame = frames[0]
    assert frame.ndim == 3
    assert frame.shape[2] == 3
    assert frame.dtype == np.uint8
    channel_means = frame.mean(axis=(0, 1))
    assert channel_means[0] > channel_means[2]

    extractor = get_video_extractor_instance()
    metadata = extractor.get_video_metadata(str(video_path))
    assert metadata.width > 0
    assert metadata.height > 0
    assert metadata.fps > 0
    assert metadata.total_frames >= 1
    assert metadata.duration > 0
    assert isinstance(metadata.codec, str)

    video_load_error = resolve_exception("VideoLoadError")
    with pytest.raises(video_load_error):
        call_extract_frames(extract_frames, tmp_path / "missing.mp4")


def test_req_002_pose_estimator_outputs_pose_sequence():
    """REQ-002: Pose_Estimator returns Pose_2D_Sequence with valid shapes and confidence."""
    estimate_2d_pose = get_estimate_pose_callable()
    frames = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(3)]
    pose_sequence = estimate_2d_pose(frames)

    assert hasattr(pose_sequence, "frames")
    assert hasattr(pose_sequence, "joint_names")
    assert len(pose_sequence.frames) == len(frames)
    joint_count = len(pose_sequence.joint_names)
    assert joint_count > 0

    for frame in pose_sequence.frames:
        assert frame.keypoints.shape == (joint_count, 2)
        assert frame.confidence.shape == (joint_count,)
        assert np.all(frame.confidence >= 0.0)
        assert np.all(frame.confidence <= 1.0)


def test_req_002_pose_estimator_warns_on_missing_person(monkeypatch, caplog):
    """REQ-002/003: Missing person detection logs warning and consecutive failures error."""
    estimator = get_pose_estimator_instance()
    if not hasattr(estimator, "detect_person"):
        pytest.skip("detect_person is not implemented yet")

    def no_person(_frame):
        return []

    monkeypatch.setattr(estimator, "detect_person", no_person)
    frames = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(3)]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(Exception):
            estimator.estimate_2d_pose(frames)
    assert any(record.levelno >= logging.WARNING for record in caplog.records)


def test_req_003_interpolate_missing_preserves_valid_data():
    """REQ-003: interpolate_missing preserves valid data and marks interpolated points."""
    processor = get_data_processor_instance(confidence_threshold=0.5)

    keypoints = np.array(
        [
            [[0.0, 0.0], [1.0, 1.0]],
            [[0.1, 0.1], [1.1, 1.1]],
            [[0.2, 0.2], [1.2, 1.2]],
        ],
        dtype=np.float32,
    )
    confidence = np.array(
        [
            [0.9, 0.2],
            [0.8, 0.1],
            [0.95, 0.2],
        ],
        dtype=np.float32,
    )
    pose_sequence = build_pose_2d_sequence(
        num_frames=3,
        num_joints=2,
        keypoints=keypoints,
        confidence=confidence,
    )
    output = processor.interpolate_missing(pose_sequence)

    output_keypoints = pose_keypoints_array(output)
    output_confidence = pose_confidence_array(output)
    valid_mask = confidence >= 0.5
    assert np.allclose(output_keypoints[valid_mask], keypoints[valid_mask])

    interpolated_conf = optional_symbol(DATA_PROCESSOR_MODULES, "INTERPOLATED_CONFIDENCE")
    if interpolated_conf is not None:
        assert np.all(output_confidence[~valid_mask] == interpolated_conf)
    else:
        assert np.all(output_confidence[~valid_mask] >= confidence[~valid_mask])


def test_req_003_interpolate_missing_warns_on_insufficient_frames(caplog):
    """REQ-003: interpolation is skipped with warning if valid frames are insufficient."""
    processor = get_data_processor_instance(confidence_threshold=0.5)
    keypoints = np.array(
        [
            [[0.0, 0.0]],
            [[0.1, 0.1]],
            [[0.2, 0.2]],
        ],
        dtype=np.float32,
    )
    confidence = np.array([[0.9], [0.1], [0.1]], dtype=np.float32)
    pose_sequence = build_pose_2d_sequence(
        num_frames=3,
        num_joints=1,
        keypoints=keypoints,
        confidence=confidence,
    )
    with caplog.at_level(logging.WARNING):
        output = processor.interpolate_missing(pose_sequence)
    assert any(record.levelno >= logging.WARNING for record in caplog.records)
    assert np.allclose(pose_keypoints_array(output), keypoints)


def test_req_004_remove_joints_with_wildcard():
    """REQ-004: remove_joints supports explicit and wildcard joint removal."""
    processor = get_data_processor_instance()
    joint_names = ["left_hand_1", "left_hand_2", "right_hand_1", "spine"]
    keypoints = np.zeros((2, len(joint_names), 2), dtype=np.float32)
    confidence = np.ones((2, len(joint_names)), dtype=np.float32)
    pose_sequence = build_pose_2d_sequence(
        num_frames=2,
        num_joints=len(joint_names),
        keypoints=keypoints,
        confidence=confidence,
    )
    pose_sequence.joint_names = joint_names

    output = processor.remove_joints(pose_sequence, ["left_hand_*"])
    assert all("left_hand" not in name for name in output.joint_names)
    assert pose_keypoints_array(output).shape[1] == len(output.joint_names)
    assert pose_confidence_array(output).shape[1] == len(output.joint_names)


def test_req_005_smoothing_preserves_temporal_consistency():
    """REQ-005: smooth_trajectory keeps temporal consistency and frame count."""
    processor = get_data_processor_instance()
    keypoints = np.array(
        [
            [[0.0, 0.0]],
            [[10.0, 10.0]],
            [[0.0, 0.0]],
            [[10.0, 10.0]],
        ],
        dtype=np.float32,
    )
    confidence = np.ones((4, 1), dtype=np.float32)
    pose_sequence = build_pose_2d_sequence(
        num_frames=4,
        num_joints=1,
        keypoints=keypoints,
        confidence=confidence,
    )
    output = processor.smooth_trajectory(pose_sequence, window_size=3)
    assert len(output.frames) == len(pose_sequence.frames)
    assert max_frame_delta(pose_keypoints_array(output)) <= max_frame_delta(keypoints) + 1e-6


def test_req_006_angular_velocity_range_and_length():
    """REQ-006: calculate_angular_velocity outputs normalized finite values."""
    processor = get_data_processor_instance()
    keypoints = np.array(
        [
            [[0.0, 0.0], [1.0, 0.0]],
            [[0.0, 1.0], [1.0, 1.0]],
            [[0.0, 2.0], [1.0, 2.0]],
        ],
        dtype=np.float32,
    )
    confidence = np.ones((3, 2), dtype=np.float32)
    pose_sequence = build_pose_2d_sequence(
        num_frames=3,
        num_joints=2,
        keypoints=keypoints,
        confidence=confidence,
    )
    angular_velocity = processor.calculate_angular_velocity(pose_sequence)
    values = to_angular_velocity_array(angular_velocity)

    assert values.shape[0] == len(pose_sequence.frames) - 1
    assert np.all(np.isfinite(values))
    assert np.all(values >= -np.pi)
    assert np.all(values <= np.pi)


def test_req_007_convert_to_3d_output_shapes_and_quaternions():
    """REQ-007: convert_to_3d returns Motion_3D_Data with normalized quaternions."""
    converter = get_converter_3d_instance()
    pose_sequence = build_pose_2d_sequence(num_frames=3, num_joints=2)
    motion_data = converter.convert_to_3d(pose_sequence)

    assert len(motion_data.frames) == len(pose_sequence.frames)
    positions = motion_positions_array(motion_data)
    rotations = motion_rotations_array(motion_data)
    assert positions.shape[2] == 3
    assert rotations.shape[2] == 4
    norms = np.linalg.norm(rotations, axis=2)
    assert np.allclose(norms, 1.0, atol=1e-3)


def test_req_008_export_formats_create_files(tmp_path):
    """REQ-008: export outputs BVH/FBX/JSON formats."""
    converter = get_converter_3d_instance()
    motion_data = build_motion_3d_data(num_frames=2, num_joints=1)

    for fmt in ("bvh", "fbx", "json"):
        output_path = tmp_path / f"motion.{fmt}"
        converter.export(motion_data, str(output_path), fmt)
        assert output_path.exists()
        assert output_path.stat().st_size > 0


def test_req_009_gpu_memory_retry_and_error(monkeypatch):
    """REQ-009: GPU memory shortage triggers retry and GPUMemoryError at minimum."""
    estimator = get_pose_estimator_instance()
    gpu_memory_error = resolve_exception("GPUMemoryError")

    hook_name = None
    for candidate in ("_infer_batch", "_estimate_batch", "_predict_batch", "_run_inference"):
        if hasattr(estimator, candidate):
            hook_name = candidate
            break
    if hook_name is None:
        pytest.skip("No batch inference hook found for GPU retry test")

    frames = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(4)]
    calls = []

    def fake_infer(_frames, batch_size):
        calls.append(batch_size)
        if batch_size > 1:
            raise RuntimeError("CUDA out of memory")
        return build_pose_2d_sequence(num_frames=len(_frames), num_joints=1)

    monkeypatch.setattr(estimator, hook_name, fake_infer)
    result = estimator.estimate_2d_pose(frames, batch_size=4)
    assert hasattr(result, "frames")
    assert min(calls) == 1

    def always_oom(_frames, batch_size):
        calls.append(batch_size)
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(estimator, hook_name, always_oom)
    with pytest.raises(gpu_memory_error):
        estimator.estimate_2d_pose(frames, batch_size=2)


def test_req_010_input_validation_rejects_invalid_path_and_format(tmp_path):
    """REQ-010: invalid paths and formats are rejected."""
    validators = try_import("video_motion_extraction.validators")
    invalid_path = tmp_path / ".." / "evil.mp4"
    invalid_file = tmp_path / "not_video.txt"
    invalid_file.write_text("not a video")

    if validators and hasattr(validators, "validate_video_path"):
        with pytest.raises(Exception):
            validators.validate_video_path(str(invalid_path))
    else:
        extract_frames = get_extract_frames_callable()
        with pytest.raises(Exception):
            call_extract_frames(extract_frames, invalid_path)

    if validators and hasattr(validators, "validate_video_format"):
        with pytest.raises(Exception):
            validators.validate_video_format(str(invalid_file))
    else:
        extract_frames = get_extract_frames_callable()
        with pytest.raises(Exception):
            call_extract_frames(extract_frames, invalid_file)

    if validators and hasattr(validators, "enforce_resource_limits"):
        with pytest.raises(Exception):
            validators.enforce_resource_limits(file_size_bytes=10**12, duration_sec=10**6)


def test_req_011_output_data_integrity():
    """REQ-011: output motion data preserves frame count and finite values."""
    converter = get_converter_3d_instance()
    pose_sequence = build_pose_2d_sequence(num_frames=4, num_joints=2)
    motion_data = converter.convert_to_3d(pose_sequence)

    assert len(motion_data.frames) == len(pose_sequence.frames)
    positions = motion_positions_array(motion_data)
    assert np.all(np.isfinite(positions))
    deltas = np.linalg.norm(np.diff(positions, axis=0), axis=-1)
    assert np.all(np.isfinite(deltas))


@given(pose_sequence_strategy())
@settings(max_examples=20)
def test_prop_1_frame_count_preservation(data):
    """Property 1: frame count preservation."""
    num_frames, _, pose_sequence, _, _ = build_pose_sequence_from_tuple(data)
    converter = get_converter_3d_instance()
    motion_data = converter.convert_to_3d(pose_sequence)
    assert len(motion_data.frames) == num_frames


@given(pose_sequence_strategy())
@settings(max_examples=20)
def test_prop_2_joint_data_integrity(data):
    """Property 2: joint data integrity in Motion3DData."""
    _, num_joints, pose_sequence, _, _ = build_pose_sequence_from_tuple(data)
    converter = get_converter_3d_instance()
    motion_data = converter.convert_to_3d(pose_sequence)
    assert len(motion_data.joint_names) == num_joints
    positions = motion_positions_array(motion_data)
    assert positions.shape[1] == num_joints
    assert np.all(np.isfinite(positions))


@given(pose_sequence_strategy())
@settings(max_examples=20)
def test_prop_3_temporal_consistency(data):
    """Property 3: temporal consistency after smoothing."""
    _, _, pose_sequence, keypoints, _ = build_pose_sequence_from_tuple(data)
    processor = get_data_processor_instance()
    output = processor.smooth_trajectory(pose_sequence, window_size=3)
    output_delta = max_frame_delta(pose_keypoints_array(output))
    input_delta = max_frame_delta(keypoints)
    assert output_delta <= input_delta + 1e-6


@given(pose_sequence_strategy())
@settings(max_examples=20)
def test_prop_4_confidence_monotonicity(data):
    """Property 4: confidence monotonicity after interpolation."""
    _, _, pose_sequence, _, confidence = build_pose_sequence_from_tuple(data)
    processor = get_data_processor_instance(confidence_threshold=0.5)
    output = processor.interpolate_missing(pose_sequence)
    output_confidence = pose_confidence_array(output)
    valid_mask = confidence >= 0.5
    assert np.allclose(output_confidence[valid_mask], confidence[valid_mask])
    assert np.all(output_confidence[~valid_mask] >= confidence[~valid_mask])


def test_prop_5_coordinate_system_consistency_json_export(tmp_path):
    """Property 5: coordinate system consistency in exported data."""
    converter = get_converter_3d_instance()
    motion_data = build_motion_3d_data(num_frames=2, num_joints=1)
    output_path = tmp_path / "motion.json"
    converter.export(motion_data, str(output_path), "json")
    payload = json.loads(output_path.read_text())
    if any(key in payload for key in ("coordinate_system", "axis_order", "up_axis")):
        assert isinstance(
            payload.get("coordinate_system", payload.get("axis_order", payload.get("up_axis"))),
            str,
        )
    else:
        pytest.skip("Coordinate system metadata is not represented in JSON output yet")
