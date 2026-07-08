# FLOW_LOG: motion-data-2dto3d

## 概要
- 開始日: 2025-02-22
- 目標: 動画から人体モーションデータを抽出し3D変換するツール
- フロー: v7.8.3a（v7.5 GitHub用）
- tmux: ai4（Pane: 0=Claude / 1=Cursor / 2=Codex / 3=Git）
- リポジトリ: https://github.com/CaCC-Lab/motion-data-2dto3d
- 主要 feature spec: `.kiro/specs/video-motion-extraction/`
- 基盤 steering: `product.md / tech.md / structure.md`

---

## Phase記録

### 2025-02-22: Phase 1-4 完了
- Kiro Spec作成（requirements/design/tasks）
- テスト作成（pytest + hypothesis）
- 全コンポーネント実装（VideoExtractor, PoseEstimator, DataProcessor, Converter3D）
- パイプライン統合、CLI実装

### 2026-03-12: feat/root-motion-and-tilt-correction
- ルートモーション復元とグローバル傾き補正を追加
- コードレビューP1/P2修正（root motion順序、tilt閾値）
- 3Dスムージングベクトル化（gaussian_filter）
- BVH再生成、比較動画作成（バッター・ピッチャー）

### 2026-07-07: 本番リリース向けハードニング
- Spec同期: tasks.md 5.2/9.1 が完了扱いなのに `gpu_manager.py`/`pipeline.py` が未存在だったため実体化
- `pipeline.py`（MotionExtractor）を新設し、CLI/GUI/API の3重複パイプラインを集約
- `gpu_manager.py` を新設（OOMバッチ半減リトライ・デバイス自動解決・CUDAキャッシュ解放）
- strictモード導入（`VME_STRICT` / `--strict`、`ModelNotAvailableError`）でスタブへのサイレントフォールバックを本番で禁止
- 品質スコア（REQ 7.2）、リソース上限配線（REQ 10.3）、max_resolution、角速度CLI統合（REQ 6）を実装
- モデルバリデーション（models.py `__post_init__`）、ロギング設定、`/health`、Docker重みダウンロード+HEALTHCHECK
- GitHub Actions CI（ruff + pytest + frontend build）、ruff設定追加・全lint解消
- design.md / tasks.md を実装に同期（Phase 14.1〜14.4 完了、Phase 16 追加）
- tests/ は無変更、全28テスト通過を維持

### 2026-07-07: Phase 14.5 完了（Dockerビルド・起動テスト）
- Dockerfile修正2件: pip/setuptools更新（PEP 660 editable対応、chumpyビルド後に実行）、numpy<2固定（torch 2.1.0/mmcv 2.1.0のNumPy 2.x非互換対応）
- `docker build` 成功（10.3GB、VideoPose3D重み同梱、MMPose事前DL済み）
- `docker run --gpus all` でGradio GUI起動、HTTP 200、HEALTHCHECK healthy
- `VME_UI=web` で `/health` が cuda_available=true / weights=true を返却
- tasks.md Phase 14 全完了 → 全タスク完了

### 2026-07-07: 全体レビュー（code-reviewer subagent + 自己検証）と修正
- 自己検証: CI相当のクリーンvenv（torch/mmpose無し）で28テスト通過、frontendビルド成功、ruff通過
- 修正: pipeline.export/export_angular_velocity の出力パス検証をmkdir前に実施
- P0修正: api/app.py create_app() に logger.configure() 追加（uvicorn直接マウント時のログロスト防止）
- P1修正: 進捗コールバック例外をパイプラインで吸収（警告ログ化）、空入力時の quality_score を0.0に
- P2修正: logger.configure() 再初期化時のハンドラ累積防止（handlers.clear）
- 誤指摘の確認: enforce_resource_limits は存置済みで名前ズレなし、Docker numpy<2 は同一pip解決で有効（コンテナ実測1.26.4）
- tests/test_hip_rotation.py は本セッション以前からの未追跡ファイル（Cursor作成のテスト、変更なし）

### 2026-07-08: 骨盤回転推定と統合ワークフロー（Phase 17）
- `estimate_pelvis_rotation` を実装し、BVH rotation モードでルート Hip の yaw を復元
- `tests/test_hip_rotation.py` 追加（10テスト、全パス）
- Integration API（`integration/`）を新設: GLBアップロード、5ステップワークフロー、SSE進捗、Blender連携
- Blender スクリプト2本（`rig_glb_to_vrm.py`, `retarget_bvh_to_vrm.py`）、WSL→Windows パス変換
- フロントエンドに Motion/Integrate モード切替、`WorkflowPanel`、`VrmViewer`（three-vrm）を追加
- `vme-integration` エントリポイント、メイン API への integration ルーターマウント
- Spec同期（要件17/18、design/tasks Phase 17）、pyproject に httpx 追加
- 既存28テスト + hip_rotation 10テスト = 38テスト通過、frontend ビルド成功

---

## 発見・詰まり

| フェーズ | 内容 | 対処 | 再発防止 |
|----------|------|------|---------|
| Phase 4 | Blender render(animation=True)がキーフレームを正しく評価しない | write_stillループで個別レンダリング | メモリに記録済み |
| Phase 4 | depsgraph未使用でpose.bonesが更新されない | evaluated_get(depsgraph)経由でベイク | メモリに記録済み |
