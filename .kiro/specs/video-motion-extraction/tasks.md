# 実装計画: Video Motion Extraction

## 概要

動画から人体モーションデータを抽出し、2Dポーズ推定→データ補完・加工→3D変換を行うPythonツールを段階的に実装する。各コンポーネント（VideoExtractor, PoseEstimator, DataProcessor, Converter3D）を順に構築し、最終的にパイプライン全体を統合する。

## タスク

- [ ] 1. プロジェクト構造とデータモデルのセットアップ
  - [ ] 1.1 プロジェクトディレクトリ構造と依存関係の定義
    - `video_motion_extraction/` パッケージディレクトリを作成
    - `pyproject.toml` または `setup.py` で依存関係を定義（MMPose, OpenCV, NumPy, SciPy, PyTorch等）
    - テストフレームワーク（pytest, hypothesis）の設定
    - _Requirements: 全体_

  - [ ] 1.2 データモデルとコア型定義の実装
    - `models.py` に `VideoMetadata`, `Pose2DFrame`, `Pose2DSequence`, `Motion3DFrame`, `Motion3DData`, `BoundingBox` データクラスを実装
    - `config.py` に `ExtractorConfig`, `PoseModelConfig`, `ProcessingConfig`, `Converter3DConfig` を実装
    - バリデーションルール（width/height > 0, 0 <= confidence <= 1, frame_id >= 0 等）を各データクラスに組み込む
    - _Requirements: 11.2, 2.5, 7.4, 7.5_

  - [ ]* 1.3 データモデルのプロパティテスト
    - **Property 2: 関節データの完全性** — Pose2DSequenceのkeypoints.shape[0]がjoint_names長と一致することを検証
    - **Validates: Requirements 11.2**

- [ ] 2. VideoExtractor（動画フレーム抽出）の実装
  - [ ] 2.1 VideoExtractorクラスの実装
    - `video_extractor.py` に `VideoExtractor` クラスを作成
    - `extract_frames(video_path, target_fps)` メソッドを実装（OpenCVを使用）
    - `get_video_metadata(video_path)` メソッドを実装
    - 動画ファイルの存在確認・フォーマット検証を実装
    - 無効なファイルに対して `VideoLoadError` を発生させる
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 10.1_

  - [ ]* 2.2 VideoExtractorのユニットテスト
    - 有効な動画からのフレーム抽出テスト
    - 存在しない/破損ファイルのエラーハンドリングテスト
    - target_fps指定時のフレーム数検証テスト
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 2.3 フレーム数保存のプロパティテスト
    - **Property 1: フレーム数の保存** — target_fpsと動画長から計算されるフレーム数が出力と一致することを検証
    - **Validates: Requirements 1.1, 11.1**

- [ ] 3. 入力検証とセキュリティの実装
  - [ ] 3.1 入力バリデーションモジュールの実装
    - `validators.py` にファイルパス検証（パストラバーサル防止）を実装
    - 動画フォーマット・サイズ検証を実装
    - 処理時間・メモリ使用量の上限設定を実装
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ]* 3.2 入力検証のユニットテスト
    - パストラバーサル攻撃パターンの検出テスト
    - 不正なフォーマット・サイズの拒否テスト
    - _Requirements: 10.2_

- [ ] 4. チェックポイント - テスト実行確認
  - すべてのテストが通ることを確認し、不明点があればユーザーに質問する。

- [ ] 5. PoseEstimator（2Dポーズ推定）の実装
  - [ ] 5.1 PoseEstimatorクラスの実装
    - `pose_estimator.py` に `PoseEstimator` クラスを作成
    - `estimate_2d_pose(frames, batch_size)` メソッドを実装（MMPose連携）
    - `detect_person(frame)` メソッドを実装
    - バッチ処理によるGPU推論の効率化を実装
    - 人物未検出時の警告ログとフレームスキップ処理を実装
    - 連続検出失敗時のエラー報告を実装
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 5.2 GPUメモリ管理の実装
    - `gpu_manager.py` にGPUメモリ監視とバッチサイズ自動調整を実装
    - メモリ不足時のバッチサイズ縮小・再試行ロジックを実装
    - 最小バッチサイズでも失敗時の `GPUMemoryError` を実装
    - _Requirements: 9.1, 9.2, 9.3_

  - [ ]* 5.3 PoseEstimatorのユニットテスト（モック使用）
    - MMPoseモデルをモックしたポーズ推定テスト
    - 人物未検出時の警告・スキップ動作テスト
    - バッチサイズ自動調整テスト
    - _Requirements: 2.2, 2.3, 9.1_

- [ ] 6. DataProcessor（データ補完・加工）の実装
  - [ ] 6.1 欠損データ補完の実装
    - `data_processor.py` に `DataProcessor` クラスを作成
    - `interpolate_missing(pose_data)` メソッドを実装（スプライン補間）
    - 信頼度閾値に基づく欠損フレーム特定ロジックを実装
    - 有効フレーム2未満時の警告・スキップ処理を実装
    - 補完後のINTERPOLATED_CONFIDENCEマーカー設定を実装
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 6.2 欠損データ補完のプロパティテスト
    - **Property 4: 信頼度の単調性** — 補完処理後、元の有効データ（閾値以上の信頼度）が変更されないことを検証
    - **Validates: Requirements 3.2**

  - [ ] 6.3 不要関節削除の実装
    - `remove_joints(pose_data, joints_to_remove)` メソッドを実装
    - ワイルドカードパターン（例: "left_hand_*"）によるマッチングを実装
    - 削除後の関節データ整合性維持を実装
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 6.4 軌跡スムージングの実装
    - `smooth_trajectory(pose_data, window_size)` メソッドを実装
    - 時間的一貫性を維持するスムージングアルゴリズムを実装
    - _Requirements: 5.1, 5.2_

  - [ ] 6.5 角速度算出の実装
    - `calculate_angular_velocity(pose_data)` メソッドを実装
    - 角速度の-π〜π範囲正規化を実装
    - 出力データ長（入力フレーム数-1）の保証を実装
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 6.6 角速度算出のプロパティテスト
    - **Property 3: 時間的一貫性** — 角速度値がすべて有限値であり、出力長が入力フレーム数-1であることを検証
    - **Validates: Requirements 6.3, 6.4**

  - [ ]* 6.7 DataProcessorのユニットテスト
    - 補間処理の正確性テスト（既知の入力に対する期待出力）
    - 関節削除後のデータ整合性テスト
    - スムージング後の時間的一貫性テスト
    - _Requirements: 3.1, 4.3, 5.2_

- [ ] 7. チェックポイント - テスト実行確認
  - すべてのテストが通ることを確認し、不明点があればユーザーに質問する。

- [ ] 8. Converter3D（2D→3D変換）の実装
  - [ ] 8.1 Converter3Dクラスの実装
    - `converter_3d.py` に `Converter3D` クラスを作成
    - `convert_to_3d(pose_2d)` メソッドを実装（VideoPose3D連携）
    - 品質スコア計算と閾値以下の警告出力を実装
    - 出力のpositions (N,3)形状とクォータニオン正規化を保証
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 8.2 出力エクスポート機能の実装
    - `export(motion_data, output_path, format)` メソッドを実装
    - BVH、FBX、JSONフォーマットのエクスポートを実装
    - 各フォーマットの座標系規約に従った変換を実装
    - _Requirements: 8.1, 8.2_

  - [ ]* 8.3 Converter3Dのプロパティテスト
    - **Property 5: 座標系の一貫性** — 出力のrotationsが正規化されたクォータニオン（ノルム≈1）であることを検証
    - **Validates: Requirements 7.5**

  - [ ]* 8.4 出力エクスポートのユニットテスト
    - 各フォーマット（BVH, FBX, JSON）の出力妥当性テスト
    - 出力ファイルの読み込み可能性テスト
    - _Requirements: 8.1, 8.2_

- [ ] 9. パイプライン統合と全体結合
  - [ ] 9.1 メインパイプラインの実装
    - `pipeline.py` に `MotionExtractor` クラスを作成
    - `process(video_path)` メソッドで全コンポーネントを結合
    - 設計のメイン処理アルゴリズムに従い、VideoExtractor → PoseEstimator → DataProcessor → Converter3D の順で処理を実行
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ] 9.2 CLIインターフェースの実装
    - `cli.py` にコマンドラインインターフェースを実装
    - 動画ファイルパス、設定オプション、出力パス・フォーマットの引数を受け付ける
    - _Requirements: 全体_

  - [ ]* 9.3 パイプライン統合のプロパティテスト
    - **Property 1: フレーム数の保存** — パイプライン全体を通じて出力フレーム数が入力フレーム数と一致することを検証（モック使用）
    - **Validates: Requirements 11.1**

  - [ ]* 9.4 統合テスト
    - サンプル動画を使用したエンドツーエンドテスト（モック使用）
    - 出力フォーマットの妥当性検証
    - _Requirements: 11.1, 11.2, 11.3_

- [ ] 10. 最終チェックポイント - 全テスト実行確認
  - すべてのテストが通ることを確認し、不明点があればユーザーに質問する。

## 備考

- `*` マーク付きのタスクはオプションであり、MVP実装時にはスキップ可能
- 各タスクは対応する要件番号を参照しトレーサビリティを確保
- チェックポイントで段階的な検証を実施
- プロパティテストは設計ドキュメントの正当性プロパティに基づく
- GPU依存部分はモックを使用してテスト可能にする
