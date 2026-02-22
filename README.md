# video-motion-extraction

動画から人体モーションデータを抽出し、2Dポーズ推定→データ補完・加工→3Dモーションデータへ変換するPythonツール。

## セットアップ

```bash
# インストール
pip install -e .

# 開発用（テスト含む）
pip install -e ".[dev]"
```

### 依存ライブラリ

- Python >= 3.8
- NumPy >= 1.20.0
- SciPy >= 1.7.0
- OpenCV >= 4.5.0
- (本番運用時) PyTorch >= 1.10.0 + CUDA >= 11.0, MMPose >= 1.0.0, VideoPose3D

## 使い方

### Python APIから使う

```python
from video_motion_extraction import (
    VideoExtractor,
    PoseEstimator,
    DataProcessor,
    Converter3D,
    ProcessingConfig,
)

# 1. 動画からフレーム抽出
extractor = VideoExtractor()
frames = extractor.extract_frames("input.mp4", target_fps=30.0)
metadata = extractor.get_video_metadata("input.mp4")

# 2. 2Dポーズ推定
estimator = PoseEstimator()
pose_2d = estimator.estimate_2d_pose(frames)

# 3. データ補完・加工
config = ProcessingConfig(confidence_threshold=0.3, smoothing_window=5)
processor = DataProcessor(config)

pose_2d = processor.interpolate_missing(pose_2d)                     # 欠損補完
pose_2d = processor.remove_joints(pose_2d, ["left_hand_*", "right_hand_*"])  # 不要関節削除
pose_2d = processor.smooth_trajectory(pose_2d, window_size=5)        # スムージング
angular_vel = processor.calculate_angular_velocity(pose_2d)          # 角速度算出

# 4. 3D変換 & エクスポート
converter = Converter3D()
motion_3d = converter.convert_to_3d(pose_2d)
converter.export(motion_3d, "output.bvh", "bvh")   # BVH形式
converter.export(motion_3d, "output.json", "json")  # JSON形式
converter.export(motion_3d, "output.fbx", "fbx")    # FBX形式
```

### 処理パイプライン

```
動画 → VideoExtractor → PoseEstimator → DataProcessor → Converter3D → BVH/FBX/JSON
         (CPU/OpenCV)    (GPU/MMPose)      (CPU/SciPy)    (GPU/VideoPose3D)
```

## テスト

```bash
# 全テスト実行
python -m pytest

# 詳細出力
python -m pytest -v

# 特定テスト実行
python -m pytest tests/test_video-motion-extraction.py::test_req_001_video_extractor_extracts_frames_and_metadata
```

## プロジェクト構成

```
src/video_motion_extraction/
├── models.py           # データモデル (VideoMetadata, Pose2DSequence, Motion3DData等)
├── config.py           # 設定クラス (ExtractorConfig, ProcessingConfig等)
├── errors.py           # 例外 (VideoLoadError, GPUMemoryError)
├── validators.py       # 入力検証 (パストラバーサル防止、フォーマット検証)
├── logger.py           # VibeLogger互換ロギング
├── video_extractor.py  # フレーム抽出 (OpenCV)
├── pose_estimator.py   # 2Dポーズ推定 (MMPose)
├── data_processor.py   # データ補完・スムージング・角速度算出
└── converter_3d.py     # 2D→3D変換・エクスポート
```

## 出力フォーマット

| フォーマット | 拡張子 | 用途 |
|---|---|---|
| BVH | `.bvh` | モーションキャプチャ標準形式。3Dソフト全般で読み込み可 |
| FBX | `.fbx` | Unity/Unreal Engine等のゲームエンジン向け |
| JSON | `.json` | プログラムからの解析・加工用 |
