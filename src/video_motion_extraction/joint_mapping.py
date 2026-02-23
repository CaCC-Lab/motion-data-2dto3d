"""COCO↔H36M関節マッピング・変換."""

import numpy as np

# COCO 17関節名（MMPose出力順序）
COCO_JOINT_NAMES = [
    "nose",            # 0
    "left_eye",        # 1
    "right_eye",       # 2
    "left_ear",        # 3
    "right_ear",       # 4
    "left_shoulder",   # 5
    "right_shoulder",  # 6
    "left_elbow",      # 7
    "right_elbow",     # 8
    "left_wrist",      # 9
    "right_wrist",     # 10
    "left_hip",        # 11
    "right_hip",       # 12
    "left_knee",       # 13
    "right_knee",      # 14
    "left_ankle",      # 15
    "right_ankle",     # 16
]

# Human3.6M 17関節名（VideoPose3D入出力順序）
H36M_JOINT_NAMES = [
    "Hip",         # 0
    "RHip",        # 1
    "RKnee",       # 2
    "RFoot",       # 3
    "LHip",        # 4
    "LKnee",       # 5
    "LFoot",       # 6
    "Spine",       # 7
    "Thorax",      # 8
    "Nose",        # 9
    "Head",        # 10
    "LShoulder",   # 11
    "LElbow",      # 12
    "LWrist",      # 13
    "RShoulder",   # 14
    "RElbow",      # 15
    "RWrist",      # 16
]

# H36Mスケルトン階層（child → parent）
H36M_HIERARCHY = {
    "RHip": "Hip",
    "RKnee": "RHip",
    "RFoot": "RKnee",
    "LHip": "Hip",
    "LKnee": "LHip",
    "LFoot": "LKnee",
    "Spine": "Hip",
    "Thorax": "Spine",
    "Nose": "Thorax",
    "Head": "Nose",
    "LShoulder": "Thorax",
    "LElbow": "LShoulder",
    "LWrist": "LElbow",
    "RShoulder": "Thorax",
    "RElbow": "RShoulder",
    "RWrist": "RElbow",
}

# COCO→H36M 直接マッピング（H36Mインデックス → COCOインデックス）
_DIRECT_MAP = {
    1: 12,   # RHip ← right_hip
    2: 14,   # RKnee ← right_knee
    3: 16,   # RFoot ← right_ankle
    4: 11,   # LHip ← left_hip
    5: 13,   # LKnee ← left_knee
    6: 15,   # LFoot ← left_ankle
    9: 0,    # Nose ← nose
    11: 5,   # LShoulder ← left_shoulder
    12: 7,   # LElbow ← left_elbow
    13: 9,   # LWrist ← left_wrist
    14: 6,   # RShoulder ← right_shoulder
    15: 8,   # RElbow ← right_elbow
    16: 10,  # RWrist ← right_wrist
}

# COCO→H36M ミッドポイント合成（H36Mインデックス → COCOインデックスのタプル）
_MIDPOINT_MAP = {
    0: (11, 12),      # Hip ← (left_hip + right_hip) / 2
    7: (5, 6, 11, 12),  # Spine ← (shoulders + hips) / 4
    8: (5, 6),         # Thorax ← (left_shoulder + right_shoulder) / 2
    10: (3, 4),        # Head ← (left_ear + right_ear) / 2
}


def coco_to_h36m_keypoints(kps: np.ndarray) -> np.ndarray:
    """COCO 17関節のキーポイントをH36M 17関節に変換.

    Args:
        kps: (T, 17, 2) or (T, 17, 3) COCO形式のキーポイント配列

    Returns:
        (T, 17, 2) or (T, 17, 3) H36M形式のキーポイント配列
    """
    if kps.ndim == 2:
        kps = kps[np.newaxis]
        squeeze = True
    else:
        squeeze = False

    t, _, d = kps.shape
    h36m = np.zeros((t, 17, d), dtype=kps.dtype)

    # 直接マッピング
    for h36m_idx, coco_idx in _DIRECT_MAP.items():
        h36m[:, h36m_idx] = kps[:, coco_idx]

    # ミッドポイント合成
    for h36m_idx, coco_indices in _MIDPOINT_MAP.items():
        h36m[:, h36m_idx] = np.mean(
            np.stack([kps[:, ci] for ci in coco_indices], axis=0),
            axis=0,
        )

    if squeeze:
        h36m = h36m[0]
    return h36m
