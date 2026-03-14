# Kiro Spec / Steering 運用ルール

## 目的
Kiro を「Spec生成ツール」ではなく「Living Spec の維持・同期ツール」として使う。

## Steering の原則

### 基盤Steering（常時読み込み）
以下を `.kiro/steering/` に配置する。

- product.md
- tech.md
- structure.md

## Feature Spec の原則

### 初回生成
Kiro により以下を生成する。

- requirements.md
- design.md
- tasks.md

### 継続更新（MUST）
仕様変更・要件追加・設計差分が発生した場合は以下の順に同期する。

1. requirements.md を更新
2. design.md を Refine
3. tasks.md を Update tasks
4. 必要なら「Check which tasks are already complete」で再判定

### 禁止
- requirements.md だけ更新して design/tasks を放置すること
- 実装コードを正として requirements を暗黙更新すること
- tasks.md が古いまま Cursor / Claude Code に作業を渡すこと

## Canon TDD との接続

### Task順序
1. requirements.md
2. design.md
3. tasks.md
4. Cursor で tests 作成
5. Claude Code / Cloud Agent で実装

### 例外時
Spec の誤り・要件変更・テストバグ時は、必ず Spec 同期を先に行う。

## requirements.md のルール
- EARS 形式を基本とする
- 各要件に REQ-xxx のIDを付与する
- Acceptance Criteria を明示する
- 変更時は差分理由をコミットメッセージで残す

## design.md のルール
- requirements.md に追従する
- Refine を使って差分同期する
- 実装詳細ではなく設計判断・境界・責務分離を明示する

## tasks.md のルール
- tasks は requirements / design にトレースできること
- テスト作成タスクと実装タスクを分離する
- Update tasks を定期実施する
- 完了済みタスクの再判定を正式手順として認める

## コミット規約

- `spec(req): {理由}`
- `spec(design): {理由}`
- `spec(tasks): {理由}`
- `fix(test): {理由}`
- `feat: {機能名}`
- `refactor: {内容}`

## Spec Sync Gate（MUST）

Phase 3 以降に進む前に以下を満たすこと。

- requirements.md が最新
- design.md が Refine 済み
- tasks.md が Update tasks 済み
- 必要時に完了タスク再判定済み
