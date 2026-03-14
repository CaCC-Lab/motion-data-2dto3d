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

---

## 発見・詰まり

| フェーズ | 内容 | 対処 | 再発防止 |
|----------|------|------|---------|
| Phase 4 | Blender render(animation=True)がキーフレームを正しく評価しない | write_stillループで個別レンダリング | メモリに記録済み |
| Phase 4 | depsgraph未使用でpose.bonesが更新されない | evaluated_get(depsgraph)経由でベイク | メモリに記録済み |
