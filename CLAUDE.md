# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

動画から人体モーションデータを抽出し、2Dポーズ推定→データ補完・加工→3D変換を行うPythonツール。野球バッターのスイングなどの動画を入力とし、BVH/FBX/JSON形式の3Dモーションデータを出力する。AWS EC2上での本番運用を想定。

**現在のステータス**: 仕様策定完了、実装未着手。詳細な要件・設計・タスクは `.kiro/specs/video-motion-extraction/` に定義済み。

## アーキテクチャ

処理パイプライン:
```
動画入力 → VideoExtractor(CPU) → PoseEstimator(GPU/MMPose) → DataProcessor(CPU) → Converter3D(GPU/VideoPose3D) → 出力
```

4つのコアコンポーネント（パッケージ: `video_motion_extraction/`）:

| コンポーネント | ファイル | 役割 | 処理 |
|---|---|---|---|
| VideoExtractor | `video_extractor.py` | フレーム抽出 | CPU (OpenCV) |
| PoseEstimator | `pose_estimator.py` | 2Dポーズ推定 | GPU (MMPose) |
| DataProcessor | `data_processor.py` | 補完・スムージング・角速度 | CPU (SciPy) |
| Converter3D | `converter_3d.py` | 2D→3D変換・エクスポート | GPU (VideoPose3D) |

統合: `pipeline.py` の `MotionExtractor` クラスが全コンポーネントを結合。CLI: `cli.py`。

データモデルは `models.py`、設定は `config.py`、入力検証は `validators.py`、GPU管理は `gpu_manager.py` に配置。

## 技術スタック

- **Python** >= 3.8
- **MMPose** >= 1.0.0 — 2Dポーズ推定
- **VideoPose3D** — 2D→3D変換
- **OpenCV** >= 4.5.0 — 動画処理
- **PyTorch** >= 1.10.0 + **CUDA** >= 11.0 — GPU推論
- **NumPy** >= 1.20.0, **SciPy** >= 1.7.0 — 数値計算・補間
- **pytest** + **hypothesis** — テスト

## 開発コマンド

```bash
# テスト実行
pytest

# 単一テスト実行
pytest tests/test_video_extractor.py::test_extract_frames

# プロパティベーステスト
pytest -m property

# 使用例（実装後）
python -m video_motion_extraction.cli input.mp4 --output output.bvh --format bvh
```

## 仕様ドキュメント

実装時は必ず参照すること:

- `.kiro/specs/video-motion-extraction/requirements.md` — 11の機能要件と受入基準
- `.kiro/specs/video-motion-extraction/design.md` — コンポーネント設計、データモデル、アルゴリズム擬似コード、形式仕様
- `.kiro/specs/video-motion-extraction/tasks.md` — 10フェーズの実装計画

## 設計上の重要ポイント

- **GPU メモリ管理**: バッチサイズ自動縮小→再試行→最小でも失敗時は `GPUMemoryError`
- **欠損データ補完**: スプライン補間、信頼度閾値ベース。補完データには `INTERPOLATED_CONFIDENCE` マーカーを付与。元の有効データは変更禁止
- **角速度**: 出力長 = 入力フレーム数 - 1。値は -π〜π に正規化。全値有限
- **3D変換品質**: 品質スコア計算、閾値以下で警告。クォータニオンは正規化必須（ノルム≈1）
- **セキュリティ**: パストラバーサル防止、フォーマット/サイズ検証、処理時間/メモリ上限

## 5つの正当性プロパティ（テストで保証）

1. **フレーム数の保存** — 出力フレーム数 = 入力フレーム数（指定FPS換算）
2. **関節データの完全性** — keypoints.shape[0] == len(joint_names)
3. **時間的一貫性** — 角速度値がすべて有限、出力長 = 入力フレーム数 - 1
4. **信頼度の単調性** — 補完後、元の有効データが変更されない
5. **座標系の一貫性** — rotationsが正規化クォータニオン

## コミットメッセージ規約

Conventional Commits ベース、日本語で記述:

```
<prefix>: <サマリ（命令形/50文字以内）>

- 変更内容1
- 変更内容2

Refs: #<Issue番号>（任意）
```

Prefix: `feat:`, `fix:`, `refactor:`, `perf:`, `test:`, `docs:`, `build:`, `ci:`, `chore:`, `style:`, `revert:`

メッセージは必ず `git diff` の実際の差分から生成すること。

## テスト方針

- GPU依存部分はモックを使用
- プロパティベーステスト（hypothesis）で5つの正当性プロパティを検証
- `*` マーク付きタスク（tasks.md参照）はMVPではオプション
