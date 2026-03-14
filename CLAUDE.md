# Claude Code 指示書

## プロジェクト概要

動画から人体モーションデータを抽出し、2Dポーズ推定→データ補完・加工→3D変換を行うPythonツール。野球バッターのスイングなどの動画を入力とし、BVH/FBX/JSON形式の3Dモーションデータを出力する。AWS EC2上での本番運用を想定。

## 基本ルール

### Canon TDD制約
- tests/ディレクトリのファイルは**変更禁止**
- 既存テストを通す実装を作成する
- テストが間違っていると思っても、まず実装で対応を試みる

### Living Spec 前提
- Kiro Spec は一回生成して終わりではなく、継続的に更新・同期する
- requirements.md が変わったら、design.md と tasks.md の同期完了を確認してから実装へ進む
- requirements/design/tasks が未同期なら、仕様解釈を進めてはならない

### Canon TDD例外（Spec起点のみ）
- 例外トリガー：Specの誤り、要件変更、テスト自体のバグ
- **実装側からの例外発動は禁止**
- 例外手順：
  1. requirements.md 修正
  2. design.md Refine
  3. tasks.md Update tasks
  4. 必要なら完了タスク再判定
  5. テスト修正（Cursor）
  6. FLOW_LOG記録
  7. tests/変更禁止に復帰

### Spec Sync Gate
- Phase 3 以降に進む前に、requirements/design/tasks の同期状態を確認する
- 以下のいずれかが未実施なら、実装を開始してはならない
  - requirements 更新後の design Refine
  - design 更新後の tasks Update
  - 必要時の完了タスク再判定

### /simplify 実行ルール（Phase 4.5）
- 実装コミット後、レビュー前に `/simplify` を実行する（SHOULD）
- `/simplify` は機能を変えずに再利用性・品質・効率性を改善する
- `/simplify` 実行後、`git diff` で修正内容を必ず目視確認する（MUST）
- 意図しない変更があれば `git checkout` で戻す

## アーキテクチャ

処理パイプライン:
```
動画入力 → VideoExtractor(CPU) → PoseEstimator(GPU/MMPose) → DataProcessor(CPU) → Converter3D(GPU/VideoPose3D) → 出力
```

4つのコアコンポーネント（パッケージ: `src/video_motion_extraction/`）:

| コンポーネント | ファイル | 役割 | 処理 |
|---|---|---|---|
| VideoExtractor | `video_extractor.py` | フレーム抽出 | CPU (OpenCV) |
| PoseEstimator | `pose_estimator.py` | 2Dポーズ推定 | GPU (MMPose) |
| DataProcessor | `data_processor.py` | 補完・スムージング・角速度 | CPU (SciPy) |
| Converter3D | `converter_3d.py` | 2D→3D変換・エクスポート | GPU (VideoPose3D) |

統合: `pipeline.py`、CLI: `cli.py`
データモデル: `models.py`、設定: `config.py`、検証: `validators.py`、GPU管理: `gpu_manager.py`

## 参照ルール
- 実装時は tests/ と .kiro/specs/ を参照
- src/ の既存コードも参照可

## 仕様ドキュメント

実装時は必ず参照すること:

- `.kiro/specs/video-motion-extraction/requirements.md` — 11の機能要件と受入基準
- `.kiro/specs/video-motion-extraction/design.md` — コンポーネント設計、データモデル、アルゴリズム擬似コード
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

Prefix: `feat:`, `fix:`, `refactor:`, `perf:`, `test:`, `docs:`, `build:`, `ci:`, `chore:`, `style:`, `revert:`, `spec(req):`, `spec(design):`, `spec(tasks):`

メッセージは必ず `git diff` の実際の差分から生成すること。

## 開発コマンド

```bash
pytest                    # テスト実行
pytest tests/test_video_extractor.py::test_extract_frames  # 単一テスト
pytest -m property        # プロパティベーステスト
python -m video_motion_extraction.cli input.mp4 --output output.bvh --format bvh  # CLI
```

## テスト方針

- GPU依存部分はモックを使用
- プロパティベーステスト（hypothesis）で5つの正当性プロパティを検証
- `*` マーク付きタスク（tasks.md参照）はMVPではオプション

## ディレクトリ構造

- 実装コード: src/video_motion_extraction/
- テストコード: tests/
- ログ出力: logs/
- 仕様: .kiro/specs/
- 基盤Steering: .kiro/steering/

## 禁止事項

- tests/の変更
- 外部APIキーのハードコード
- bare except（except Exceptionは可）
- requirements/design/tasks 未同期状態での実装開始
