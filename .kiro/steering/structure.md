# Structure Steering

## ディレクトリ構成

```
src/video_motion_extraction/  # 実装コード
tests/                        # テストコード（変更禁止）
.kiro/specs/                  # Feature Spec
.kiro/steering/               # 基盤Steering
data/input/                   # 入力動画
data/output/                  # 出力（BVH/FBX/JSON/動画）
data/sample/                  # サンプル動画
data/model/                   # VRMモデル等
logs/                         # ログ出力
docs/                         # ドキュメント
```

## ファイル命名規則
- 実装: src/video_motion_extraction/{module}.py
- テスト: tests/test_{module}.py
- Spec: .kiro/specs/{feature}/

## モジュール分離方針

パイプライン4段階に対応するモジュール構成:

| モジュール | 役割 | 処理 |
|---|---|---|
| video_extractor.py | フレーム抽出 | CPU (OpenCV) |
| pose_estimator.py | 2Dポーズ推定 | GPU (MMPose) |
| data_processor.py | 補完・スムージング・角速度 | CPU (SciPy) |
| converter_3d.py | 2D→3D変換・エクスポート | GPU (VideoPose3D) |

統合: pipeline.py、CLI: cli.py
データモデル: models.py、設定: config.py、検証: validators.py、GPU管理: gpu_manager.py
