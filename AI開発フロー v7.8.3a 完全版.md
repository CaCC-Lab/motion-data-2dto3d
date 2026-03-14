# AI開発フロー v7.8.3a 完全版

## 目次

1. [概要](#1-概要)
2. [ツールと月額](#2-ツールと月額)
3. [AI役割分離](#3-ai役割分離)
4. [v7.5（GitHub用）フロー](#4-v75github用フロー)
5. [v7.7-local（GitHubなし）フロー](#5-v77-localgithubなしフロー)
6. [tmux/tmuxp環境設定](#6-tmuxtmuxp環境設定)
7. [設定ファイル一覧](#7-設定ファイル一覧)
8. [設定ファイル内容](#8-設定ファイル内容)
9. [Skills設定](#9-skills設定)
10. [GitHub Actions設定（v7.5専用）](#10-github-actions設定v75専用)
11. [ワンライナー集](#11-ワンライナー集)
12. [初期化チェックリスト](#12-初期化チェックリスト)
13. [FLOW_LOG.mdテンプレート](#13-flow_logmdテンプレート)
14. [コマンド早見表](#14-コマンド早見表)
15. [レビュー体制比較](#15-レビュー体制比較)
16. [フロー使い分け](#16-フロー使い分け)
17. [トラブルシューティング](#17-トラブルシューティング)
18. [重要な学び](#18-重要な学び)
19. [変更履歴](#19-変更履歴)

-----

## 1. 概要

### 設計思想

1. **Canon TDD**：テスト先行 → 実装は tests/ 変更禁止
2. **Living Spec**：Kiro Spec は一回生成して終わりではなく、継続的に更新・同期する
3. **AI役割固定**：各AIに明確な責務を割り当てる
4. **構造の力で品質を守る**：意志ではなくツール制約で強制する
5. **AIの弱点を補完**：クロスチェックで視点の偏りを排除する
6. **環境まで含めた設計**：tmux / Skill / pre-commit / CI / steering まで統合する

### Canon TDD 例外手順（MUST）

Canon TDD の「tests/変更禁止」は原則だが、以下の3条件に限り例外を認める。

|トリガー      |例                          |
|----------|---------------------------|
|Specの誤りが判明|requirements.md の記述自体が誤っていた|
|要件変更      |ステークホルダー判断で仕様が変わった         |
|テスト自体のバグ  |期待値やテストロジックに欠陥がある          |

**例外時の手順（この順序は MUST）：**

1. requirements.md を修正（Kiro or 人間）
   コミット: `spec(req): {理由}`
2. design.md を Refine
   コミット: `spec(design): {理由}`
3. tasks.md を Update tasks
   コミット: `spec(tasks): {理由}`
4. 必要に応じて「Check which tasks are already complete」で再判定
5. テスト修正（Cursor）
   コミット: `fix(test): {理由}`
6. 例外理由を FLOW_LOG.md に記録
   （トリガー種別・影響範囲・判断者・requirements/design/tasks の同期有無）
7. 以降の実装は再び tests/変更禁止に復帰

**禁止：**

- 実装側（Claude Code / Cursor Cloud Agent）が「テストが間違っている」と判断して自ら tests を変更すること
- requirements.md 更新後に design.md / tasks.md を未同期のまま実装へ進むこと

### Kiro運用の絶対ルール（v7.8.3）

- Kiro Spec は一回生成して終わりではない
- requirements.md を変えたら design.md を Refine する
- design.md を変えたら tasks.md を Update tasks する
- 必要なら完了タスク再判定を行う
- Spec Sync Gate を通らない限り Phase 3 以降へ進まない
- 実装中に仕様差分が見つかったら Phase 1 に戻る

### 2つのフロー

|フロー       |対象                      |月額  |
|----------|------------------------|---:|
|v7.5      |GitHubでPR運用するプロジェクト     |$319|
|v7.7-local|Git管理のみ（GitHubなし）のプロジェクト|$279|

### 規範レベルの定義

本文書では手順の強制度を以下の3段階で区別する。

|レベル       |意味                 |例                                               |
|----------|-------------------|------------------------------------------------|
|**MUST**  |常に実施する標準手順。省略不可    |Canon TDD制約、tests/変更禁止、pre-commit、Spec Sync Gate|
|**SHOULD**|推奨される強化手順。省略時は理由を記録|Agent Teams並列レビュー、Hypothesis使用                  |
|**MAY**   |有効だが任意。プロジェクト判断で採否 |FLOW_LOG.md記録、Devin Review                      |

### v7.6 → v7.7 変更サマリー

|項目            |v7.6-local|v7.7-local                              |
|--------------|----------|----------------------------------------|
|Phase 5 レビュー構造|逐次6ステップ   |Agent Teams 3並列 + 逐次（SHOULD）            |
|レビュー所要時間      |20-45分    |15-28分                                  |
|コンテキスト汚染      |あり（1ウィンドウ）|なし（teammate独立）                          |
|環境変数          |不要        |`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`|
|フォールバック       |-         |v7.6逐次フローに自動退行                          |
|トークン消費        |1x        |約3x（Step 1のみ）                           |
|Phase 1-4, 6-7|変更なし      |変更なし                                    |
|v7.5（GitHub用） |変更なし      |変更なし                                    |

### v7.7 → v7.8 変更サマリー

|項目                 |v7.7    |v7.8                  |
|-------------------|--------|----------------------|
|Canon TDD例外手順      |なし（暗黙運用）|明文化（Spec起点、3トリガー、手順固定）|
|Cloud Agent制約      |基本禁止事項のみ|MUST NOT リスト追加        |
|Phase Exit Criteria|なし      |Phase 3・4に導入          |
|KPI                |なし      |手戻り回数を FLOW_LOG で計測   |
|Phase 1-4 フロー構造    |変更なし    |変更なし                  |
|Phase 5 レビュー構造     |変更なし    |変更なし                  |

### v7.8.2 → v7.8.3 変更サマリー

|項目         |v7.8.2        |v7.8.3                                             |
|-----------|--------------|---------------------------------------------------|
|Kiroの位置づけ  |Spec生成中心      |Living Spec の作成・同期・再判定中心                           |
|Phase 1    |初回生成寄り        |初回生成 + 反復更新に変更                                     |
|Spec同期     |明示なし          |Spec Sync Gate を導入                                 |
|Canon TDD例外|Spec修正 → テスト修正|requirements → design refine → tasks update → テスト修正|
|Steering   |specs.md 中心   |product.md / tech.md / structure.md を基盤化           |
|tasks運用    |固定タスク寄り       |Update tasks / 完了タスク再判定を正式手順化                      |
|フロー構造      |直線型           |反復型（仕様差分発見時に Phase 1 へ戻る）                          |

-----

## 2. ツールと月額

|ツール               |月額  |役割                                                                  |v7.5    |v7.7-local|
|------------------|---:|--------------------------------------------------------------------|:------:|:--------:|
|Kiro Pro          |$19 |Living Spec 作成・同期（requirements / design / tasks）、Steering運用、完了タスク再判定|✅       |✅         |
|Cursor Pro+       |$40 |テスト作成                                                               |✅       |✅         |
|Claude Code Max 20|$200|実装、セキュリティレビュー、CI修正、Agent Teams                                      |✅       |✅         |
|Bugbot            |$40 |バグ検出＋Autofix（PR連携）                                                  |✅       |❌         |
|ChatGPT Plus      |$20 |Codex（クロスチェック）                                                      |✅       |✅         |
|Devin Review      |$0  |追加レビュー（PR連携）                                                        |✅       |❌         |
|CodeRabbit        |$0  |PRサマリー、CLI統合                                                        |✅       |✅         |
|**合計**                                                                                    |||**$319**|**$279**  |

### 2.x 追加ツール（状況により追加費用が発生し得るため合計には未計上）

- **Cursor Cloud Agent**：Cursor側のクラウド実行（非同期）で、実装の反映・横断修正をオフロードする。
- **Claude Code on the web**：隔離サンドボックスでの調査・即席修正・移動中の指示に限定して使う（主実装には使わない）。

-----

## 3. AI役割分離

|AI / ツール          |できること                                                                        |禁止事項                                              |
|------------------|-----------------------------------------------------------------------------|--------------------------------------------------|
|Kiro              |Feature Spec 作成、requirements更新、design Refine、tasks Update、完了タスク再判定、Steering活用|実装コードを直接正として要件を上書きしない                             |
|Cursor            |テスト作成（tests/配下）                                                              |src/参照禁止                                          |
|Cursor Cloud Agent|実装・修正の実行（非同期／クラウド）                                                           |要件解釈・設計判断・tests/変更禁止                              |
|Cursor（Debug Mode）|実行時バグの仮説検証・根本原因特定（Phase 5 SHOULD）                                            |本番環境での実行禁止・計測ログは修正後に必ず除去                          |
|Claude Code       |実装、セキュリティレビュー、セルフレビュー、Agent Teams統括                                          |tests/変更禁止、requirements/design/tasks 未同期状態での仕様解釈禁止|
|Claude Code（Web）  |隔離調査・即席修正・移動時の指示（Phase 0用途）                                                  |主実装・設計判断・長期作業・tests/変更禁止                          |
|Claude Code Action|CI修正（GitHub用）                                                                |tests/変更禁止                                        |
|Bugbot            |PRレビュー、Autofix（GitHub用）                                                      |-                                                 |
|Codex             |クロスチェック、差分バグ検出                                                               |直接修正しない（指摘のみ）                                     |
|CodeRabbit        |ロジックバグ検出（CLI）、PRサマリー                                                         |-                                                 |


> **Kiro の正式な役割定義**
> Kiro は「Spec を作るAI」ではなく、**Spec を継続同期するAI**として扱う。

> **用語の固定**：このドキュメントで「Claude Code」と書いた場合、原則として **CLI/IDE上で動かすClaude Code** を指す。Web版は上表の通り **Phase 0（隔離・即席・移動）専用** として扱う。

### Codexの特性（重要）

**Codex `/review` の設計思想：「明確なバグだけを指摘する」**

|得意             |苦手（沈黙しやすい）             |
|---------------|-----------------------|
|差分局所で完結するロジックバグ|PR説明と設計意図に依存する判断       |
|API・ライブラリの明確な誤用|既存バグが変更で顕在化するケース       |
|単一スコープ内の不整合    |テストの不足                 |
||設計・保守性・将来リスク           |
||**セキュリティ**（プロンプトに用語がない）|

**解決策：Codexレビュー後に補完レビューを実施**

### Cursor Cloud Agent の MUST NOT（追加制約）

Cursor Cloud Agent は非同期クラウド実行のため、暴走時の被害が不可逆になり得る。以下を MUST NOT として厳守する。

|MUST NOT                               |理由             |
|---------------------------------------|---------------|
|.env / secrets / credential の作成・変更・コミット|秘密情報漏洩リスク      |
|依存関係の追加（pip/npm等）を人間承認なしで実行            |ライセンス・セキュリティリスク|
|DBマイグレーション・データ破壊操作                     |不可逆な被害         |
|大規模リファクタ・アーキテクチャ変更                     |「横断修正」のスコープ逸脱  |
|tests/ の変更（Canon TDD制約）                |役割分離違反         |

Cloud Agent の適正スコープ：**タスク定義済みの機械的置換・横断反映・フォーマット修正**に限定する。
スコープ外の作業を検出した場合は停止し、人間に判断を仰ぐこと。

-----

## 4. v7.5（GitHub用）フロー

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Kiro Spec作成・同期                                     │
│   初回: requirements.md / design.md / tasks.md を生成            │
│   変更時: requirements更新 → design Refine → tasks Update        │
│   必要時: 完了タスク再判定                                        │
│   場所: .kiro/specs/{feature}/                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: featureブランチ作成                                      │
│   git checkout -b feature/{機能名}                               │
│   git add .kiro/specs/{feature}/ .kiro/steering/                 │
│   git commit -m "spec(req|design|tasks): {機能名}"               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2.5: Spec Sync Gate（MUST）                                │
│   確認: requirements/design/tasks が最新同期済み                  │
│   確認: 変更があれば tasks.md まで更新済み                        │
│   確認: 実装済みタスクの再判定が必要なら完了                       │
│   未達なら Phase 3 へ進まない（MUST）                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Cursor（テスト作成）                                     │
│   参照: .kiro/specs/ のみ                                        │
│   禁止: src/ の参照 ⚠️                                           │
│   出力: tests/test_{feature}.py                                  │
│   コミット: git commit -m "test: {機能名}"                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Claude Code / Cursor Cloud Agent（実装）                 │
│   参照: tests/, .kiro/specs/                                     │
│   禁止: tests/ の変更 ⚠️                                         │
│   出力: src/{feature}.py                                         │
│   コミット: git commit -m "feat: {機能名}"                        │
│                                                                 │
│   ※実装中に仕様差分が見つかった場合 → Phase 1 に戻る             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4.5（SHOULD）: /simplify（コード品質改善）                   │
│   Claude Code で /simplify を実行                                 │
│   → 再利用性・品質・効率性の3観点で自動修正                       │
│   → 機能は不変（テストはそのままPASS）                             │
│   → git diff で修正内容を目視確認（MUST）                         │
│   → コミット: git commit -m "refactor: /simplify で品質改善"      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: pre-commit                                              │
│   pytest自動実行                                                  │
│   失敗 → Claude Codeで修正（tests/変更禁止）→ 再コミット           │
│   成功 → Phase 6へ                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 6: PR作成 → GitHub CI                                       │
│   git push origin feature/{機能名}                               │
│   GitHub でPR作成                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  ┌───────────┴───────────┐
                  │                       │
               CI緑 ✅                  CI赤 ❌
                  │                       │
                  ▼                       ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│ Phase 7: 自動レビュー     │   │ Phase 7': Claude Code    │
│         （4ツール並列）   │   │          Action          │
│                          │   │                          │
│  ├─ Bugbot               │   │  最大3回、15分上限        │
│  │   （バグ検出＋Autofix）│   │  tests/変更禁止          │
│  │                       │   │                          │
│  ├─ Security Review CI   │   │  失敗 → Issue作成        │
│  │   （セキュリティ5観点）│   │                          │
│  │                       │   └──────────────────────────┘
│  ├─ Devin Review         │              │
│  │   （設計観点）        │              └──→ CI再実行
│  │                       │
│  └─ CodeRabbit PR        │
│      （サマリー生成）    │
└──────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 8: Bugbot指摘対応                                           │
│                                                                 │
│   Autofix提案あり:                                                │
│     → PRコメント: @cursor push {commit_hash}                     │
│                                                                 │
│   手動修正必要:                                                    │
│     → Cursor Dashboard: Fix in Cursor                            │
│     → 修正後 push                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 9a: Codex（差分バグ検出）                                    │
│                                                                 │
│   PRコメント: @codex review                                       │
│                                                                 │
│   Codexの動作:                                                    │
│     1. リポジトリ内のAGENTS.mdを自動検索                           │
│     2. Review guidelinesセクションに従ってレビュー                 │
│                                                                 │
│   指摘あり → Claude Codeで修正 → push                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 9b: 補完レビュー                                            │
│                                                                 │
│   観点（REVIEW_SUPPLEMENT.md）:                                   │
│     1. 仕様・意図確認                                             │
│     2. 設計・保守性                                               │
│     3. AI可読性                                                   │
│     4. 既存機能への影響・回帰リスク                                │
│     5. テスト・運用                                               │
│                                                                 │
│   ※セキュリティは自動レビュー済みのため対象外                      │
│                                                                 │
│   指摘あり → 修正 → push                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 10: Merge                                                  │
│                                                                 │
│   GitHub UI: Squash and merge                                    │
│                                                                 │
│   ローカル:                                                       │
│     git checkout main                                            │
│     git pull origin main                                         │
│     git branch -d feature/{機能名}                               │
└─────────────────────────────────────────────────────────────────┘
```

**仕様差分が発見された場合の戻り先：**

- requirements 変更が必要 → Phase 1 に戻る
- design だけ更新が必要 → Phase 1 に戻る
- tasks 再同期が必要 → Phase 1 に戻る
- 未同期のまま Phase 4 へ進むことは禁止

-----

## 5. v7.7-local（GitHubなし）フロー

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Kiro Spec作成・同期                                     │
│   初回: requirements.md / design.md / tasks.md を生成            │
│   変更時: requirements更新 → design Refine → tasks Update        │
│   必要時: 完了タスク再判定                                        │
│   場所: .kiro/specs/{feature}/                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: ローカルブランチ作成                                      │
│   git checkout -b feature/{機能名}                               │
│   git add .kiro/specs/{feature}/ .kiro/steering/                 │
│   git commit -m "spec(req|design|tasks): {機能名}"               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2.5: Spec Sync Gate（MUST）                                │
│   確認: requirements/design/tasks が最新同期済み                  │
│   確認: 変更があれば tasks.md まで更新済み                        │
│   確認: 実装済みタスクの再判定が必要なら完了                       │
│   未達なら Phase 3 へ進まない（MUST）                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Cursor（テスト作成）                                     │
│   参照: .kiro/specs/ のみ                                        │
│   禁止: src/ の参照 ⚠️                                           │
│   出力: tests/test_{feature}.py                                  │
│   コミット: git commit -m "test: {機能名}"                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Claude Code / Cursor Cloud Agent（実装）                 │
│   参照: tests/, .kiro/specs/                                     │
│   禁止: tests/ の変更 ⚠️                                         │
│   出力: src/{feature}.py                                         │
│                                                                 │
│   ※実装中に仕様差分が見つかった場合 → Phase 1 に戻る             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4.5（SHOULD）: /simplify（コード品質改善）                   │
│   Claude Code で /simplify を実行                                 │
│   → 再利用性・品質・効率性の3観点で自動修正                       │
│   → 機能は不変（テストはそのままPASS）                             │
│   → git diff で修正内容を目視確認（MUST）                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: ローカルレビュー（Agent Teams並列化）                     │
│                                                                 │
│   前提: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 が有効             │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ tmux ai4 ペイン構成                                      │   │
│   │ +------------------+------------------+                  │   │
│   │ |   Claude Code    |     Cursor       |                  │   │
│   │ |    (Pane 0)      |    (Pane 1)      |                  │   │
│   │ +------------------+------------------+                  │   │
│   │ |     Codex        |      Git         |                  │   │
│   │ |    (Pane 2)      |    (Pane 3)      |                  │   │
│   │ +------------------+------------------+                  │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Step 1: Agent Teams 並列レビュー（3-5分）                    │ │
│ │                                                             │ │
│ │  Lead（Pane 0 Claude Code）                                 │ │
│ │    │                                                        │ │
│ │    ├─ spawn Teammate: security-reviewer                     │ │
│ │    │   → /security-review 実行                              │ │
│ │    │   → 5観点（SQLi, XSS, 認証, データ, 依存関係）         │ │
│ │    │                                                        │ │
│ │    ├─ spawn Teammate: logic-reviewer                        │ │
│ │    │   → セルフレビュー（review Skill）                      │ │
│ │    │   → 5観点（可読性, バグ, パフォーマンス, セキュリティ,  │ │
│ │    │          テスト）                                       │ │
│ │    │                                                        │ │
│ │    └─ spawn Teammate: supplement-reviewer                   │ │
│ │        → REVIEW_SUPPLEMENT.md 観点                          │ │
│ │        → 5観点（仕様, 設計, AI可読性, 回帰, 運用）          │ │
│ │                                                             │ │
│ │  ※3つのteammateが同時並列で実行                             │ │
│ │  ※各teammateは独立コンテキスト（視点の偏りなし）            │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Step 2: Lead が指摘を統合（2-3分）                          │ │
│ │                                                             │ │
│ │  ・3つのteammateの結果を受信（inbox経由）                   │ │
│ │  ・指摘を優先度別に統合（P0/P1/P2）                        │ │
│ │  ・重複指摘を排除                                           │ │
│ │  ・teammates をシャットダウン                                │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Step 3: 修正（5-10分）                                      │ │
│ │                                                             │ │
│ │  ・P0指摘を優先修正（tests/変更禁止）                       │ │
│ │  ・P1指摘を対応                                             │ │
│ │  ・P2は判断して対応/スキップ                                │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Step 4: CodeRabbit + Codex クロスチェック（5-10分）          │ │
│ │                                                             │ │
│ │  ・/coderabbit:review uncommitted（ロジックバグ）           │ │
│ │  ・Pane2（Codex）へ tmux send-keys で差分レビュー依頼      │ │
│ │  ・指摘があれば修正                                         │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Step 4.5（SHOULD）: Cursor Debug Mode（原因不明バグ時）      │ │
│ │                                                             │ │
│ │  ・レビューで「挙動が怪しいが原因不明」の指摘が出た場合に発動│ │
│ │  ・Cursor Debug Mode で仮説→計測→証拠→修正                 │ │
│ │  ・計測ログ（vibelogger外）は修正確認後に必ず除去            │ │
│ │  ・該当なければスキップ                                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│                  「コミット可能」宣言                             │
│                  コミットメッセージ案を3つ提示                    │
│                                                                 │
│ ※Agent Teams 起動失敗時:                                        │
│   従来の逐次フロー（下記フォールバック）に退行                   │
│                                                                 │
│ ┌─ フォールバック（逐次フロー） ──────────────────────────────┐ │
│ │ 5a: /security-review（セキュリティ）→ 修正                  │ │
│ │ 5b: /coderabbit:review uncommitted（ロジックバグ）→ 修正   │ │
│ │ 5c: セルフレビュー（review Skill）→ 修正                    │ │
│ │ 5d: tmux send-keys → Codex /review → 修正                  │ │
│ │ 5e: 補完レビュー（REVIEW_SUPPLEMENT.md）→ 修正             │ │
│ │ 5f: 「コミット可能」宣言                                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 6: コミット                                                │
│                                                                 │
│   git add .                                                     │
│   git commit -m "feat: {機能名}"                                │
│                                                                 │
│   ↓ pre-commit自動実行                                          │
│                                                                 │
│   pytest tests/ -v                                              │
│                                                                 │
│   失敗 → Claude Codeで修正（tests/変更禁止）→ 再コミット          │
│   成功 → Phase 7へ                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 7: マージ                                                  │
│                                                                 │
│   git checkout main                                             │
│   git merge --squash feature/{機能名}                           │
│   git commit -m "feat: {機能名}"                                │
│   git branch -d feature/{機能名}                                │
└─────────────────────────────────────────────────────────────────┘
```

**仕様差分が発見された場合の戻り先：**

- requirements 変更が必要 → Phase 1 に戻る
- design だけ更新が必要 → Phase 1 に戻る
- tasks 再同期が必要 → Phase 1 に戻る
- 未同期のまま Phase 4 へ進むことは禁止

### なぜ CodeRabbit と Codex は Agent Teams に含めないのか

|ツール       |理由                                                                    |
|----------|----------------------------------------------------------------------|
|CodeRabbit|Claude Code プラグイン（`/coderabbit:review`）であり、Agent Teamsのteammateからは実行不可|
|Codex     |別ツール（Pane 2）であり、Agent Teamsの範囲外。tmux send-keys で連携                    |

Agent Teams で並列化できるのは **Claude Code 内で完結するレビュー** のみ。
外部ツール連携は従来通り Lead が逐次で実行する。

-----

## 6. tmux/tmuxp環境設定

### 6.1 tmux基本設定

**~/.tmux.conf**

```bash
# プレフィックスキーをCtrl+aに変更
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# ペイン分割
bind | split-window -h
bind - split-window -v

# ペイン移動（Vim風）
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# マウス操作有効化
set -g mouse on

# 履歴保持行数
set -g history-limit 10000

# ステータスバー
set -g status-bg colour235
set -g status-fg white
```

### 6.2 tmuxp設定（ai4）

**~/.tmuxp/ai4.yaml**

```yaml
session_name: ai4
start_directory: ${__AI4_DIR__:-.}
environment:
  CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"
windows:
  - window_name: dev
    layout: tiled
    panes:
      - shell_command:
          - echo "Pane 0: Claude Code (Lead + Agent Teams)"
          - echo "Run: claude"
      - shell_command:
          - echo "Pane 1: Cursor"
          - echo "Run: cursor ."
      - shell_command:
          - echo "Pane 2: Codex"
          - echo "Run: codex"
      - shell_command:
          - echo "Pane 3: Git"
          - git status
```

### 6.3 ai4起動スクリプト

**~/bin/ai4**

```bash
#!/bin/bash
# ai4 - AI開発用tmuxセッション起動

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR" || exit 1

export __AI4_DIR__="$(pwd)"
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# 既存セッションがあればアタッチ、なければ新規作成
if tmux has-session -t ai4 2>/dev/null; then
    tmux attach -t ai4
else
    tmuxp load ai4
fi
```

```bash
# 実行権限付与
chmod +x ~/bin/ai4

# PATHに追加（~/.bashrc または ~/.zshrc）
export PATH="$HOME/bin:$PATH"
```

### 6.4 ペイン役割

|Pane|役割                                   |起動コマンド    |
|:--:|-------------------------------------|----------|
|0   |Claude Code（実装・レビュー・Agent Teams Lead）|`claude`  |
|1   |Cursor（テスト作成）                        |`cursor .`|
|2   |Codex（クロスチェック）                       |`codex`   |
|3   |Git（操作・ログ確認）                         |シェル       |

### 6.5 ペイン操作

|操作     |キー（Ctrl+a前提）        |
|-------|--------------------|
|ペイン間移動 |`Ctrl+a` → `h/j/k/l`|
|ペイン一覧確認|`tmux list-panes`   |
|左右分割   |`Ctrl+a` → `        |
|上下分割   |`Ctrl+a` → `-`      |
|セッション一覧|`tmux ls`           |
|デタッチ   |`Ctrl+a` → `d`      |

-----

## 7. 設定ファイル一覧

### 7.1 ディレクトリ構造

```
project/
├── .kiro/
│   ├── steering/
│   │   ├── product.md            # プロダクト方針（基盤Steering）
│   │   ├── tech.md               # 技術制約（基盤Steering）
│   │   ├── structure.md          # 構造規約（基盤Steering）
│   │   ├── specs.md              # Kiro生成ルール
│   │   ├── testing-standards.md  # テスト基準（任意）
│   │   └── security-policies.md  # セキュリティ方針（任意）
│   └── specs/
│       └── {feature}/
│           ├── requirements.md   # 要件定義
│           ├── design.md         # 設計
│           └── tasks.md          # タスク分解
│
├── .cursor/
│   └── BUGBOT.md                 # Bugbotルール（ルート）
│
├── .github/                      # ★v7.5（GitHub用）のみ
│   └── workflows/
│       ├── ci.yml                # pytest実行
│       ├── claude-ci-fix.yml     # CI失敗時自動修正
│       └── security-review.yml   # セキュリティレビュー
│
├── src/
│   ├── .cursor/
│   │   └── BUGBOT.md             # src専用ルール
│   ├── __init__.py
│   └── {feature}.py
│
├── tests/
│   ├── .cursor/
│   │   └── BUGBOT.md             # tests専用ルール
│   ├── __init__.py
│   └── test_{feature}.py
│
├── logs/                         # vibelogger出力先
│
├── docs/
│   └── TMUX_FLOW.md              # tmux運用ガイド（任意）
│
├── .pre-commit-config.yaml       # pytest自動実行
├── .gitignore
├── CLAUDE.md                     # Claude Code指示
├── AGENTS.md                     # Codexレビュー指示
├── REVIEW_SUPPLEMENT.md          # 補完レビュープロンプト
├── FLOW_LOG.md                   # 開発ログ
├── requirements.txt              # Python依存関係
└── README.md
```

### 7.2 ユーザーホーム設定

```
~/
├── .tmux.conf                    # tmux設定
├── .tmuxp/
│   └── ai4.yaml                  # tmuxp設定（Agent Teams環境変数含む）
├── bin/
│   └── ai4                       # ai4起動スクリプト
├── .claude/
│   └── skills/
│       ├── tmux-sender/
│       │   └── SKILL.md          # tmuxペイン送信
│       └── review/
│           └── SKILL.md          # レビュー観点
└── .codex/
    └── skills/
        ├── tmux-sender/
        │   └── SKILL.md          # tmuxペイン送信
        └── review/
            └── SKILL.md          # レビュー観点
```

-----

## 8. 設定ファイル内容

### 8.1 requirements.txt

```
pytest
hypothesis
vibelogger
```

### 8.2 .pre-commit-config.yaml

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests/ -v
        language: system
        pass_filenames: false
        always_run: true
```

### 8.3 .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
.env

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Temporary
*.tmp
*.bak
```

### 8.4 CLAUDE.md

```markdown
# Claude Code 指示書

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
- 詳細は本ドキュメント §1「Canon TDD 例外手順」を参照

### Spec Sync Gate
- Phase 3 以降に進む前に、requirements/design/tasks の同期状態を確認する
- 以下のいずれかが未実施なら、実装を開始してはならない
  - requirements 更新後の design Refine
  - design 更新後の tasks Update
  - 必要時の完了タスク再判定

### Cursor Cloud Agent への委譲ルール
- Cloud Agentに委譲する場合、スコープは「タスク定義済みの機械的置換・横断反映」に限定
- Cloud Agent の MUST NOT：secrets操作、依存追加（未承認）、DB操作、大規模リファクタ、tests変更
- 詳細は本ドキュメント §3「Cursor Cloud Agent の MUST NOT」を参照

### /simplify 実行ルール（Phase 4.5）
- 実装コミット後、レビュー前に `/simplify` を実行する（SHOULD）
- `/simplify` は機能を変えずに再利用性・品質・効率性を改善する
- **vibelogger の operation / context / ai_todo パターンを削除してはならない**（保護対象）
- `/simplify` 実行後、`git diff` で修正内容を必ず目視確認する（MUST）
- 意図しない変更（vibeloggerログ削除、公開API変更等）があれば `git checkout` で戻す
- 確認後 `git commit -m "refactor: /simplify で品質改善"` でコミット

### 参照ルール
- 実装時は tests/ と .kiro/specs/ を参照
- src/ の既存コードも参照可

## コーディング規約

- Python 3.11
- 型ヒント必須
- docstring必須（Google style）

## ロギング

- ライブラリ: vibelogger
- 各ログに以下を含める:
  - operation: 処理名
  - context: コンテキスト情報
  - human_note: 人間向けメモ（任意）
  - ai_todo: AI向けTODO（必須）

```python
from vibelogger import logger

logger.info(
    "Processing started",
    operation="process_data",
    context={"input_size": len(data)},
    ai_todo="エラー時はcontext.errorを確認"
)
```

## ディレクトリ構造

- 実装コード: src/
- テストコード: tests/
- ログ出力: logs/
- 仕様: .kiro/specs/
- 基盤Steering: .kiro/steering/

## 禁止事項

- print()の使用（vibeloggerを使う）
- tests/の変更
- 外部APIキーのハードコード
- bare except（except Exceptionは可）
- requirements/design/tasks 未同期状態での実装開始

## ローカルレビュー手順（v7.7：Agent Teams並列化）

### 前提

- 環境変数 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` が有効であること

### Phase 5 実行手順

#### Step 1: Agent Teams 並列レビュー

以下の3つのteammateを同時にspawnしてレビューを並列実行する：

**Teammate: security-reviewer**

- /security-review を実行
- 検出観点: SQLi, XSS, 認証・認可, データ処理, 依存関係
- P0以上があれば即報告

**Teammate: logic-reviewer**

- セルフレビュー（review Skill相当）を実行
- 検出観点: 可読性, バグ可能性, パフォーマンス, セキュリティ, テスト
- 問題があれば優先度つきで報告

**Teammate: supplement-reviewer**

- REVIEW_SUPPLEMENT.md の観点でレビュー
- 検出観点: 仕様・意図, 設計・保守性, AI可読性, 回帰リスク, テスト・運用
- ※セキュリティは security-reviewer が担当するため対象外
- 問題があれば優先度つきで報告

#### Step 2: 指摘統合

- 3つのteammateの結果を統合
- 重複指摘を排除し、P0/P1/P2で整理
- teammatesをシャットダウン

#### Step 3: 修正

- P0 → 必須修正（tests/変更禁止）
- P1 → 推奨修正
- P2 → 判断して対応/スキップ

#### Step 4: 外部ツールクロスチェック

1. /coderabbit:review uncommitted を実行、指摘があれば修正
2. Pane2（Codex）へ「mainとの差分レビュー」を依頼
3. Codex指摘があれば修正

#### Step 4.5（SHOULD）: Cursor Debug Mode

- レビューで「テストは通るが挙動が怪しい」「原因不明の不具合」が指摘された場合に発動
- Pane 1（Cursor）で Debug Mode を起動し、仮説→計測→再現→根本原因特定→修正
- Debug Mode が追加する計測ログ（インストルメンテーション）は vibelogger 制約の例外とする
- **修正確認後、計測ログは必ず全除去すること（Debug Mode のクリーンアップ機能を使用）**
- 該当する指摘がなければスキップ

#### Step 5: 完了宣言

- すべてパスしたら「コミット可能」と宣言
- コミットメッセージ案を3つ提示

### フォールバック

Agent Teams 起動失敗時は以下の逐次手順で実行：

1. /security-review → 修正
2. /coderabbit:review uncommitted → 修正
3. セルフレビュー → 修正
4. Pane2 Codex → 修正
5. REVIEW_SUPPLEMENT.md 補完レビュー → 修正
6. 「コミット可能」宣言

```
### 8.5 AGENTS.md

```markdown
# AGENTS.md

## Overview

このリポジトリはCanon TDD（テスト先行）で開発しています。
tests/ は Cursor が作成し、src/ は Claude Code が実装します。
Kiro Spec は Living Spec として継続的に同期します。

## Review guidelines

### 要件トレーサビリティ（P0）
- .kiro/specs/*/requirements.md の各要件（REQ-xxx）に対応する実装があるか確認
- 未実装の要件があればP0として報告
- 要件IDを明示して報告すること

### 仕様ズレ（P0）
- 実装が requirements.md の記述と矛盾していればP0として報告
- Acceptance Criteria（EARS形式）との整合性を確認

### Spec同期（P0）
- requirements/design/tasks の同期状態を確認
- requirements が更新されているのに design/tasks が古い場合はP0として報告

### Canon TDD制約（P0）
- tests/ディレクトリの変更は要注意フラグ
- src/のみを修正すべきPRでtests/を変更していたらP0として報告
- 理由: テストはCursorの責務、実装はClaude Codeの責務

### ロギング（P1）
- vibelogger以外のprint()やlogging使用はP1として報告
- ログにoperation/context/ai_todoが含まれていなければP1として報告

### エッジケース（P1）
- 空リスト、空文字列、None、ゼロ除算の考慮漏れ
- 境界値（off-by-one）エラー

### 型安全性（P2）
- 型ヒントの欠落
- 型の不一致（Any型の多用）

## Coding guidelines

- Python 3.11
- 型ヒント必須
- Google style docstring
- vibelogger使用（print禁止）

## Project structure

src/           # 実装コード（Claude Code担当）
tests/         # テストコード（Cursor担当、変更禁止）
.kiro/specs/   # 仕様書（Kiro生成・同期）
.kiro/steering/ # 基盤Steering（product/tech/structure）
logs/          # ログ出力
```

### 8.6 REVIEW_SUPPLEMENT.md

```markdown
# 補完レビュープロンプト

## 役割

あなたは経験豊富なソフトウェアエンジニアとしてコードをレビューします。
このレビューは、実行済みの機械レビュー（ロジックバグ・セキュリティ検出）を**補完する目的**です。

以下の観点に集中してください：
- 仕様・意図
- 設計・保守性
- AI可読性
- 回帰リスク
- テスト・運用

**※セキュリティは/security-reviewで自動レビュー済みのため対象外**

---

## レビュー観点

### 1. 仕様・意図確認
- 実際の変更内容はPRの説明（またはコミットメッセージ）通りか
- 説明に書かれていない挙動変更が含まれていないか
- 変更は仕様・プロダクト観点で妥当か
- .kiro/specs/*/requirements.md との整合性
- requirements/design/tasks の同期状態は適切か

### 2. 設計・保守性
- 責務分離が適切か（単一責任原則）
- 新しい依存関係や結合度が過剰になっていないか
- 周辺コードの設計方針と一貫しているか
- 将来の変更に対して柔軟か

### 3. AI可読性
- 変数名・関数名から意図が一意に推測できるか
- AIが誤った推論をしやすい構造・命名がないか
  - 例: `data`, `info`, `tmp` などの曖昧な名前
  - 例: 複数の責務を持つ関数
- 暗黙の前提や文脈依存が多くないか
- コメントやdocstringは十分か

### 4. 既存機能への影響・回帰リスク
- 既存の機能・挙動に影響を与える可能性はないか
- 暗黙的に変わる振る舞いはないか
- 過去の仕様に依存していたコードが静かに壊れる可能性はないか
- 公開APIの変更はあるか

### 5. テスト・運用
- 変更内容は十分にテストされているか
- 重要な分岐・失敗ケースが未検証ではないか
- 障害時に調査可能なログ・エラー・メトリクスがあるか
- vibeloggerのoperation/context/ai_todoは適切か

---

## 出力形式

1. **全体サマリ**（3〜5点、箇条書き）
2. **仕様・意図確認レビュー**
3. **設計・保守性レビュー**
4. **AI可読性レビュー**
5. **既存機能への影響・回帰リスクレビュー**
6. **テスト・運用レビュー**
7. **作者への確認事項**（質問形式）

---

## トーン・制約

- このレビューは**他のAIエージェントが後続で読むこと**を前提とする
- 中立・事実ベース・建設的に書く
- 明確な根拠が無い限り断定しない
- 「このコードからは判断できない」「明示的な確認が必要」を積極的に使う
- 指摘には優先度を付ける（P0: 必須修正 / P1: 推奨 / P2: 任意）
```

### 8.7 .kiro/steering/ 設定

#### .kiro/steering/specs.md

```markdown
# Kiro Spec / Steering 運用ルール

## 目的
Kiro を「Spec生成ツール」ではなく「Living Spec の維持・同期ツール」として使う。

## Steering の原則

### 基盤Steering（常時読み込み）
以下を `.kiro/steering/` に配置する。

- product.md
- tech.md
- structure.md

### 追加Steering（必要に応じて）
- testing-standards.md
- security-policies.md
- deployment-workflow.md
- api-standards.md
- review-standards.md

### AGENTS.md
- ルート `AGENTS.md` も併用可
- Kiro に対する常時指示は steering と AGENTS.md の両方で明文化する

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
- 曖昧な主語を避ける
- 変更時は差分理由をコミットメッセージで残す

### EARS形式の例

REQ-001: ユーザー認証
When: ユーザーが正しい認証情報を入力したとき
The system shall: アクセストークンを発行する
So that: 保護されたリソースにアクセスできる

Acceptance Criteria:
- Given: 有効なユーザー名とパスワード
- When: ログインAPIを呼び出す
- Then: 200 OKとアクセストークンを返す

## design.md のルール
- requirements.md に追従する
- Refine を使って差分同期する
- 19プロパティを含め、各プロパティに PROP-xxx のIDを付与する
- 実装詳細ではなく設計判断・境界・責務分離を明示する
- エラーハンドリング、制約、非機能要件を落とさない

### 必須プロパティ
1. 目的（PROP-001）
2. 入力（PROP-002）
3. 出力（PROP-003）
4. 前提条件（PROP-004）
5. 事後条件（PROP-005）
6. 不変条件（PROP-006）
7. エラー処理（PROP-007）
8. 境界条件（PROP-008）
9. 依存関係（PROP-009）
10. 副作用（PROP-010）

## tasks.md のルール
- tasks は requirements / design にトレースできること
- テスト作成タスクと実装タスクを分離する
- Update tasks を定期実施する
- 完了済みタスクの再判定を正式手順として認める

### フォーマット
```markdown
## Task 1: テスト作成
- 担当: Cursor
- 入力: requirements.md
- 出力: tests/test_{feature}.py
- 禁止: src/ の参照

## Task 2: 実装
- 担当: Claude Code
- 入力: tests/, requirements.md
- 出力: src/{feature}.py
- 禁止: tests/ の変更
```

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

```
#### .kiro/steering/product.md（テンプレート）

```markdown
# Product Steering

## プロダクト名
{プロダクト名}

## 目的
{1-2文でプロダクトの目的}

## ターゲットユーザー
{対象ユーザー}

## 主要機能
{機能一覧}

## 制約・方針
{ビジネス制約やUX方針}
```

#### .kiro/steering/tech.md（テンプレート）

```markdown
# Tech Steering

## 言語・ランタイム
- Python 3.11

## 主要ライブラリ
- pytest, hypothesis（テスト）
- vibelogger（ロギング）

## コーディング規約
- 型ヒント必須
- Google style docstring
- print()禁止（vibelogger使用）
- vibelogger使用を強制
  - operation: 処理名
  - context: コンテキスト情報
  - ai_todo: AI向けTODO（必須）

## 開発フロー
- Canon TDD（テスト先行、tests/変更禁止）
- Living Spec（Kiro Spec 継続同期）
```

#### .kiro/steering/structure.md（テンプレート）

```markdown
# Structure Steering

## ディレクトリ構成
```

src/           # 実装コード
tests/         # テストコード（変更禁止）
.kiro/specs/   # Feature Spec
.kiro/steering/ # 基盤Steering
logs/          # ログ出力

```
## ファイル命名規則
- 実装: src/{feature}.py
- テスト: tests/test_{feature}.py
- Spec: .kiro/specs/{feature}/

## モジュール分離方針
{プロジェクト固有のモジュール分離ルール}
```

### 8.8 .cursor/BUGBOT.md（ルート）

```markdown
# プロジェクト全体のBugbotルール

## プロジェクト概要

- 言語: Python 3.11
- テスト: pytest, Hypothesis
- ロギング: vibelogger
- 開発フロー: Canon TDD（テスト先行）+ Living Spec（Kiro Spec継続同期）

## 重点チェック

### ロジックバグ（P0）
- null/None参照
- 境界値エラー（off-by-one）
- エッジケース（空リスト、空文字列、ゼロ除算）
- 型の不一致
- 無限ループ

### セキュリティ（P0）
- インジェクション（SQL、コマンド、パス）
- 認証・認可の欠陥
- 機密情報のハードコード（APIキー、パスワード）
- XSS脆弱性
- パストラバーサル

### 並行処理（P1）
- レースコンディション
- デッドロック
- スレッドセーフでないコード

### エラーハンドリング（P1）
- 例外の握りつぶし（bare except）
- 不適切なエラーメッセージ
- リソースリーク（ファイル、コネクション）

## 無視してよい項目

- コードスタイル（black/ruffで対応）
- docstringの有無（別途チェック）
- 変数名の好み（PEP8準拠であれば可）
- import順序

## プロジェクト固有ルール

### ロギング
- print()ではなくvibeloggerを使用
- ログにoperation、context、ai_todoを含める
- print()使用はP1として報告

### テスト
- tests/ディレクトリの変更は要注意フラグ（Canon TDD違反の可能性）
- Property-based testing（Hypothesis）推奨
- tests/ 変更時はP0として報告

### 構造
- 実装コードはsrc/配下に配置
- テストコードはtests/配下に配置
```

### 8.9 src/.cursor/BUGBOT.md

```markdown
# src/ 専用ルール

## 追加チェック

### API・外部連携
- 外部API呼び出しのタイムアウト設定
- リトライ処理の有無
- 接続エラーのハンドリング

### リソース管理
- ファイルハンドルのクローズ
- データベースコネクションの解放
- メモリ使用量（大量データ処理時）

### パフォーマンス
- O(n²)以上のアルゴリズム
- 不要なループ内処理
- 大量データのメモリロード

## vibelogger必須

- 全ての公開関数にログ出力
- エラー発生時にスタックトレース出力
- operation/context/ai_todo の3項目必須

## 禁止事項

- print()の使用
- bare except
- TODO/FIXMEコメントの放置
- ハードコードされた設定値
```

### 8.10 tests/.cursor/BUGBOT.md

```markdown
# tests/ 専用ルール

## 警告

⚠️ **Canon TDD制約**
このディレクトリはCursor（テスト作成）の責務です。
Claude Code（実装）はこのディレクトリを変更してはいけません。

tests/の変更を検出した場合はP0として報告してください。

## チェック項目

### テスト品質
- テストが実装の詳細に依存していないか
- テスト名が意図を表しているか
- Arrange-Act-Assertパターンに従っているか

### Hypothesis
- strategiesが適切か
- @given デコレータの使用
- 境界値のカバー

### フィクスチャ
- 再利用性
- セットアップ/ティアダウンの適切さ
- conftest.py の活用

## 許容事項

- テストコード内のprint()（デバッグ用）
- マジックナンバー（テストデータとして）
```

-----

## 9. Skills設定

### 9.1 ~/.claude/skills/tmux-sender/SKILL.md

```markdown
---
name: tmux-sender
description: tmux の別ペインにコマンドを送信する。「ペインで実行して」「Codexに依頼して」「Pane2で」などのリクエストで使用。
allowed-tools: Bash(tmux:*)
---

# tmux コマンド送信スキル

## 概要

tmuxの別ペインにコマンドやプロンプトを送信して実行する。
AI間の連携（Claude Code ⇔ Codex）に使用。

## ペイン構成（ai4）

| Pane | 役割 |
|:----:|------|
| 0 | Claude Code（実装・レビュー・Agent Teams Lead） |
| 1 | Cursor（テスト作成） |
| 2 | Codex（クロスチェック） |
| 3 | Git（操作・ログ確認） |

## 使い方

### コマンド送信
```bash
tmux send-keys -t <ペイン番号> '<コマンド>' Enter
```

### プロンプト送信（改行なし）

```bash
tmux send-keys -t <ペイン番号> '<プロンプト>'
```

## 手順

1. `tmux list-panes` でペイン一覧を確認
2. `tmux send-keys -t <ペイン番号> '<コマンド>' Enter` で送信・実行

## 例

### Codex（Pane2）にレビュー依頼

```bash
tmux send-keys -t 2 '/review' Enter
```

### Codex（Pane2）にカスタムプロンプト送信

```bash
tmux send-keys -t 2 'mainとの差分をレビューして。観点: 1.エッジケース 2.ロジックバグ 3.回帰リスク' Enter
```

### Git（Pane3）でステータス確認

```bash
tmux send-keys -t 3 'git status' Enter
```

## 注意事項

- Claude Code → Codex: 自動実行される
- Codex → Claude Code: テキスト入力のみ、実行は手動Enter必要

```
### 9.2 ~/.claude/skills/review/SKILL.md

```markdown
---
name: review
description: コードレビューを行う。「レビューして」「コードレビュー」「セルフレビュー」などのリクエストで使用。
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git log:*), Bash(git show:*)
---

# コードレビュースキル

## 概要

コードの品質をチェックし、問題点を報告する。
/security-review や /coderabbit:review とは別の観点で実施。

## レビュー観点

### 1. 可読性
- 変数名・関数名はわかりやすいか
- コードの意図が伝わるか
- 適切なコメント・docstringがあるか

### 2. バグの可能性
- エッジケースの考慮漏れがないか
  - 空リスト、空文字列、None
  - 境界値（0, 1, max-1, max）
- null/undefinedの扱いは大丈夫か
- 型の不一致はないか

### 3. パフォーマンス
- 明らかに非効率な処理がないか
- O(n²)以上のアルゴリズム
- 不要な再計算・再レンダリングがないか

### 4. セキュリティ
- 入力値の検証は適切か
- 機密情報の扱いは問題ないか
- ※詳細は/security-reviewで確認

### 5. テスト
- テストは書かれているか
- テストのカバレッジは十分か
- 重要な分岐がカバーされているか

## 出力形式

```markdown
## セルフレビュー結果

### 問題点（P0: 必須修正）
- [ ] {ファイル名}:{行番号} - {問題内容}

### 問題点（P1: 推奨）
- [ ] {ファイル名}:{行番号} - {問題内容}

### 問題点（P2: 任意）
- [ ] {ファイル名}:{行番号} - {問題内容}

### 良い点
- {良い点}

### 総評
{1-2文で総評}
```

## 使用コマンド例

```bash
# 変更差分の確認
git diff main

# 特定ファイルの確認
git diff main -- src/feature.py

# コミット履歴の確認
git log --oneline -10
```

```
### 9.3 ~/.codex/skills/tmux-sender/SKILL.md

```markdown
---
name: tmux-sender
description: tmux の別ペインにコマンドを送信する。「Claude Codeに依頼して」「Pane0で」などで使用。
metadata:
  short-description: tmuxペイン間コマンド送信
---

# tmux コマンド送信スキル

## ペイン構成（ai4）

| Pane | 役割 |
|:----:|------|
| 0 | Claude Code（実装・レビュー） |
| 1 | Cursor（テスト作成） |
| 2 | Codex（クロスチェック）← 自分 |
| 3 | Git（操作・ログ確認） |

## 使い方

```bash
tmux send-keys -t <ペイン番号> '<コマンド>' Enter
```

## 手順

1. `tmux list-panes` でペイン一覧を確認
2. `tmux send-keys -t <ペイン番号> '<コマンド>' Enter` で送信・実行

## 例

### Claude Code（Pane0）に修正依頼

```bash
tmux send-keys -t 0 'エッジケースの処理を追加して: 空リストの場合にValueErrorを発生させる'
```

### Git（Pane3）でdiff確認

```bash
tmux send-keys -t 3 'git diff main' Enter
```

## 注意事項

⚠️ **Codex → Claude Code への送信制限**

Claude CodeはインタラクティブなTUIのため、`tmux send-keys`でプロンプトを送信しても自動実行されません。

- テキストは入力バッファに届く
- 実行は受け取り側（Pane0）で手動Enterが必要

**運用方法**:

1. Codexから指摘をまとめて送信
2. ユーザーがPane0に移動してEnterを押す

```
### 9.4 ~/.codex/skills/review/SKILL.md

```markdown
---
name: review
description: コードレビューを行う。「レビューして」「コードレビュー」などのリクエストで使用。
metadata:
  short-description: コードレビュー用スキル
---

# コードレビュースキル

## 役割

Claude Codeとは**異なる視点**でコードをレビューする。
同じ視点に偏らないことが目的。

## レビュー観点

### 1. 可読性
- 変数名・関数名はわかりやすいか
- コードの意図が伝わるか

### 2. バグの可能性
- エッジケースの考慮漏れがないか
  - 空リスト、空文字列、None、0
  - 境界値（off-by-one）
- null/undefinedの扱いは大丈夫か

### 3. パフォーマンス
- 明らかに非効率な処理がないか

### 4. セキュリティ
- 入力値の検証は適切か
- 機密情報の扱いは問題ないか

### 5. テスト
- テストは書かれているか
- カバレッジは十分か
- **重要な分岐・失敗ケースが未検証ではないか**

### 6. 仕様との整合性
- requirements.md の要件を満たしているか
- 仕様にない挙動が含まれていないか

### 7. 回帰リスク
- 既存機能への影響はないか
- 暗黙的に変わる振る舞いはないか

## 出力形式

```markdown
## Codex クロスチェック結果

### P0（必須修正）
- {ファイル名}:{行番号} - {問題内容}
  - 理由: {なぜ問題か}
  - 修正案: {どう直すべきか}

### P1（推奨）
- {ファイル名}:{行番号} - {問題内容}

### P2（任意）
- {ファイル名}:{行番号} - {問題内容}

### Claude Codeへのフィードバック
{Claude Codeに伝えるべき指摘のまとめ}
```

## プリセット選択

`/review` 実行時に選択肢が表示される:

1. **Review against a base branch** ← 推奨
2. Review uncommitted changes
3. Review a commit
4. Custom review instructions

```
-----

## 10. GitHub Actions設定（v7.5専用）

### 10.1 .github/workflows/ci.yml

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v --tb=short
```

### 10.2 .github/workflows/claude-ci-fix.yml

```yaml
name: Claude CI Fix

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  fix-on-failure:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.workflow_run.head_branch }}
      
      - name: Claude Code Fix
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            CIが失敗しました。修正してください。
            
            ## 手順
            1. GitHub Actionsのログを確認し、失敗原因を特定
            2. 修正を実施
               - tests/ディレクトリは**変更禁止**（Canon TDD制約）
               - src/および設定ファイル（requirements.txt等）は修正可
            3. コミット＆プッシュ
            4. CIが通るまで繰り返す（最大3回）
            
            ## 失敗時
            3回失敗した場合はIssueを作成してください。
            タイトル: "CI Fix Failed: {エラー概要}"
            本文: 試行内容と失敗理由
```

### 10.3 .github/workflows/security-review.yml

```yaml
name: Security Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  security-review:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Claude Code Security Review
        uses: anthropics/claude-code-security-review@main
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

-----

## 11. ワンライナー集

### 11.0 Claude Code on the web用：Phase 0（隔離調査／即席修正）

```
このリポジトリを **Claude Code on the web（隔離サンドボックス）** で調査したい。

目的：
- 依存関係と起動手順の把握
- 危険なスクリプト／外部通信の有無の確認
- 変更が必要なら「最小差分」の修正案（commit/PR前提）

制約：
- ここでは **主実装はしない**
- 設計判断が必要なら「判断点」と選択肢を箇条書きで返す
- 秘密情報（鍵・トークン・顧客データ）は投入しない
```

### 11.0b Kiro用：既存Specへの要件追記

```
#requirements.md に以下の要件を追加:
{要件の内容}

追記後の手順：
1. design.md を Refine
2. tasks.md を Update tasks
3. git commit -m "spec(req): {理由}"
4. git commit -m "spec(design): {理由}"
5. git commit -m "spec(tasks): {理由}"
```

### 11.0c Kiro用：既存Specの設計同期

```
design.md を開いて Refine を実行。
変更差分を確認し、整合性を検証。
git commit -m "spec(design): {理由}"
```

### 11.0d Kiro用：tasks同期

```
tasks.md を開いて Update tasks を実行。
新規タスク・完了済みタスクの変化を確認。
git commit -m "spec(tasks): {理由}"
```

### 11.0e Kiro用：完了タスク再判定

```
Spec session で「Check which tasks are already complete」を実行。
自動再判定結果を確認。
必要なら git commit -m "spec(tasks): 完了タスク再判定"
```

### 11.1 Claude Code用：レビュー→コミット準備（v7.7 Agent Teams）

```
Phase 5のレビューをAgent Teamsで並列実行して。

■ spawn する teammate（3つ同時）
1. security-reviewer: /security-review を実行。5観点でセキュリティチェック
2. logic-reviewer: セルフレビュー。可読性・バグ・パフォーマンス・テストをチェック
3. supplement-reviewer: REVIEW_SUPPLEMENT.md の観点でレビュー（セキュリティ除く）

■ 統合後の手順
- 3つの結果を P0/P1/P2 で統合し、重複排除
- P0から順に修正（tests/変更禁止）
- /coderabbit:review uncommitted を実行、指摘があれば修正
- Pane2（Codex）へ「mainとの差分レビュー」を依頼
- Codex指摘があれば修正
- すべてパスしたら「コミット可能」と宣言し、コミットメッセージ案を3つ出す

■ フォールバック
Agent Teams起動失敗時は従来の逐次レビュー（5a→5f）で実行して。
```

### 11.2 Claude Code用：レビュー→コミット準備（フォールバック/逐次）

```
以下を順番に実行して。

1. /security-review を実行し、問題があれば tests/ を変更せずに修正
2. /coderabbit:review uncommitted を実行し、指摘があれば修正
3. セルフレビュー（仕様・意図、回帰、運用）を行い修正
4. Pane2（Codex）へ「mainとの差分レビュー」を依頼（要点を貼る）
5. Codex指摘があれば修正
6. REVIEW_SUPPLEMENT.md 観点で補完レビューし修正
7. すべてパスしたら「コミット可能」と宣言し、コミットメッセージ案を3つ出す
```

### 11.3 Codex用：クロスチェック

```
mainとの差分をレビューして。

観点：
1. エッジケース漏れ（空リスト、None、境界値）
2. ロジックバグ（特に境界条件）
3. テストの穴（重要な分岐/失敗ケースの未検証）
4. 仕様ズレ（.kiro/specs/*/requirements.md との整合性）
5. 回帰リスク（既存挙動の暗黙変更）

指摘は P0/P1/P2 で優先度をつけて。
```

### 11.4 Claude Code用：実装開始（Phase 4）

```
tests/test_{feature}.py と .kiro/specs/{feature}/ を参照して実装を開始して。

ルール：
- tests/ は変更禁止
- vibeloggerを使用（print禁止）
- 型ヒント必須
- 全テストをパスさせる
- 実装中に仕様差分が見つかったら報告して停止（Phase 1に戻る）
```

### 11.4b Cursor Cloud Agent用：実装反映（Phase 4 実行役）

```
次の前提で **Cursor Cloud Agent** として実装を進めて。

入力：
- .kiro/specs/{feature}/requirements.md, design.md, tasks.md
- tests/test_{feature}.py

ルール：
- tests/ は変更禁止（必要なら不足点を指摘するだけ）
- 仕様解釈や設計判断はしない（判断が要る場合は質問して止める）
- 変更は PR/コミット単位でまとまるように
- 既存のコーディング規約・命名・構造を維持

出力：
- src/ 配下の実装
- 変更概要（影響範囲・リスク・実行したテスト）
```

### 11.4c Claude Code用：/simplify（Phase 4.5 品質改善）

```
/simplify

※ 実行後の確認手順：
1. git diff で修正内容を目視確認
2. vibelogger の operation/context/ai_todo が削除されていないか確認
3. 公開APIの変更がないか確認
4. 問題なければ git commit -m "refactor: /simplify で品質改善"
5. 意図しない変更があれば git checkout で該当ファイルを戻す
```

### 11.4d Claude Code用：/batch（大規模マイグレーション）

```
/batch {変更内容を自然言語で指示}

例：
/batch replace all deprecated API calls with v2 equivalents in src/
/batch add type annotations to all untyped function parameters in src/
/batch rename all snake_case module names to match new naming convention

※ 実行フロー：
1. 調査 → 影響ファイル特定
2. 計画 → 独立ユニットに分解（ユーザー承認待ち）
3. 並列実行 → 各ユニットを独立worktreeで同時処理（内部で/simplify自動実行）
4. 結果集約 → PR or コミット

制約：
- tests/ は変更禁止（Canon TDD制約は/batchにも適用）
- 依存関係追加は人間承認必須
- 計画フェーズで必ず内容を確認してから承認する
```

### 11.5 Cursor用：テスト作成（Phase 3）

```
.kiro/specs/{feature}/requirements.md を参照してテストを作成して。

ルール：
- src/ は参照禁止（まだ存在しない前提）
- pytest + Hypothesis を使用
- Acceptance Criteria を全てカバー
- エッジケースを含める（空リスト、None、境界値）
```

-----

## 12. 初期化チェックリスト

### 12.1 事前準備（1回だけ）

#### 環境構築

- [ ] Python 3.11 インストール済み
- [ ] tmux インストール済み
- [ ] tmuxp インストール済み (`pip install tmuxp`)
- [ ] pre-commit インストール済み (`pip install pre-commit`)
- [ ] CodeRabbit CLI インストール済み (`npm install -g @coderabbit/cli`)
- [ ] CodeRabbit 認証済み (`coderabbit auth login`)

#### ツール契約

- [ ] Kiro Pro 契約済み ($19/月)
- [ ] Cursor Pro+ 契約済み ($40/月)
- [ ] Claude Code Max 契約済み ($200/月)
- [ ] ChatGPT Plus 契約済み ($20/月)
- [ ] Bugbot 契約済み ($40/月) ※v7.5のみ

#### tmux/tmuxp設定

- [ ] ~/.tmux.conf 設定済み（Ctrl+a前提）
- [ ] ~/.tmuxp/ai4.yaml 作成済み（Agent Teams環境変数含む）
- [ ] ~/bin/ai4 作成済み（実行権限付与）
- [ ] ~/bin が PATH に入っている
- [ ] `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` が設定済み（ai4スクリプトまたはsettings.json）
- [ ] Agent Teams の動作確認済み（簡単なタスクでteammate spawnを確認）

#### Skills設定

- [ ] ~/.claude/skills/tmux-sender/SKILL.md 作成済み
- [ ] ~/.claude/skills/review/SKILL.md 作成済み
- [ ] ~/.codex/skills/tmux-sender/SKILL.md 作成済み
- [ ] ~/.codex/skills/review/SKILL.md 作成済み

#### Claude Code プラグイン

- [ ] CodeRabbitプラグイン インストール済み
  
  ```
  /add-marketplace @coderabbit/install @coderabbit/coderabbit-plugin
  ```

#### Kiro Steering 初期化

- [ ] `.kiro/steering/` ディレクトリ構造を理解済み
- [ ] `product.md` テンプレート準備済み
- [ ] `tech.md` テンプレート準備済み
- [ ] `structure.md` テンプレート準備済み
- [ ] 必要に応じて `testing-standards.md` / `security-policies.md` テンプレート準備済み

#### WSL/SSH運用（該当する場合）

- [ ] ~/.local/bin や ~/bin が PATH に入っている
- [ ] シェルスクリプトが CRLF でない（LF）

-----

### 12.2 プロジェクト初期化（v7.5：GitHub用）

#### 基本ファイル作成

- [ ] requirements.txt
- [ ] .pre-commit-config.yaml
- [ ] .gitignore
- [ ] CLAUDE.md
- [ ] AGENTS.md
- [ ] REVIEW_SUPPLEMENT.md
- [ ] FLOW_LOG.md

#### ディレクトリ作成

- [ ] .kiro/steering/specs.md
- [ ] .kiro/steering/product.md
- [ ] .kiro/steering/tech.md
- [ ] .kiro/steering/structure.md
- [ ] src/**init**.py
- [ ] tests/**init**.py
- [ ] logs/

#### Kiro Spec 運用初期化

- [ ] `.kiro/specs/` ディレクトリ作成
- [ ] 初回 feature spec を生成（requirements/design/tasks）
- [ ] requirements/design/tasks の更新ルールを AGENTS.md に明記
- [ ] Spec Sync Gate をチーム運用ルールとして固定

#### Bugbot設定

- [ ] .cursor/BUGBOT.md（ルート）
- [ ] src/.cursor/BUGBOT.md
- [ ] tests/.cursor/BUGBOT.md

#### GitHub Actions

- [ ] .github/workflows/ci.yml
- [ ] .github/workflows/claude-ci-fix.yml
- [ ] .github/workflows/security-review.yml

#### GitHub Secrets

- [ ] ANTHROPIC_API_KEY 設定済み

#### 外部ツール連携

- [ ] Cursor Dashboard → Bugbot有効化
- [ ] chatgpt.com/codex → Code review有効化
- [ ] Devin Review連携
- [ ] CodeRabbit連携

#### Git初期化

- [ ] git init
- [ ] pre-commit install
- [ ] 初期コミット完了
- [ ] GitHubリポジトリ作成・push

-----

### 12.3 プロジェクト初期化（v7.7-local：GitHubなし）

#### 基本ファイル作成

- [ ] requirements.txt
- [ ] .pre-commit-config.yaml
- [ ] .gitignore
- [ ] CLAUDE.md
- [ ] AGENTS.md
- [ ] REVIEW_SUPPLEMENT.md
- [ ] FLOW_LOG.md

#### ディレクトリ作成

- [ ] .kiro/steering/specs.md
- [ ] .kiro/steering/product.md
- [ ] .kiro/steering/tech.md
- [ ] .kiro/steering/structure.md
- [ ] src/**init**.py
- [ ] tests/**init**.py
- [ ] logs/

#### Kiro Spec 運用初期化

- [ ] `.kiro/specs/` ディレクトリ作成
- [ ] 初回 feature spec を生成（requirements/design/tasks）
- [ ] requirements/design/tasks の更新ルールを AGENTS.md に明記
- [ ] Spec Sync Gate をチーム運用ルールとして固定

#### Git初期化

- [ ] git init
- [ ] pre-commit install
- [ ] 初期コミット完了

-----

## 13. FLOW_LOG.mdテンプレート

```markdown
# FLOW_LOG: {プロジェクト名}

## 概要
- 開始日: YYYY-MM-DD
- 目標: {1行で}
- フロー: v7.8.3（v7.7-local / v7.5）
- tmux: ai4（Pane: 0=Claude / 1=Cursor / 2=Codex / 3=Git）
- リポジトリ: {URL or local}
- 主要 feature spec: `.kiro/specs/{feature}/`
- 基盤 steering: `product.md / tech.md / structure.md`

---

## Day 1 (YYYY-MM-DD)

### 実施フェーズ
- [ ] Phase 1: Kiro Spec作成・同期
- [ ] Phase 2: featureブランチ作成（Spec commit）
- [ ] Phase 2.5: Spec Sync Gate

### Spec同期記録（記録必須）
| 項目 | 値 |
|------|-----|
| requirements 更新有無 | |
| design Refine 実施有無 | |
| tasks Update 実施有無 | |
| 完了タスク再判定有無 | |
| 同期理由 | |

### 発見・詰まり（記録必須）
| フェーズ | 内容 | 対処 | 時間 | 再発防止 |
|----------|------|------|-----:|---------|
| Phase 1 | Kiroが○○を誤解 | プロンプト修正 | 15m | steering更新 |

### 良かった点
- 

### 改善候補（次バージョンネタ）
- 

---

## Day 2 (YYYY-MM-DD)

### 実施フェーズ
- [ ] Phase 3: Cursor（テスト作成）
- [ ] Phase 4: Claude Code（実装）

### Spec同期記録
| 項目 | 値 |
|------|-----|
| requirements 更新有無 | |
| design Refine 実施有無 | |
| tasks Update 実施有無 | |
| 完了タスク再判定有無 | |
| 同期理由 | |

### 手戻り記録
| Phase | 手戻り回数 | 原因区分 | 備考 |
|-------|--------:|--------|------|
| Phase 3 | | Exit Criteria未達 / Spec不備 / Spec未同期 | |
| Phase 4 | | テスト不通過 / lint失敗 / スコープ超過 / 仕様差分発見→Phase 1戻り | |

### 発見・詰まり
| フェーズ | 内容 | 対処 | 時間 | 再発防止 |
|----------|------|------|-----:|---------|
| | | | | |

### 良かった点
- 

### 改善候補
- 

---

## Day N (完走日)

### 実施フェーズ
- [ ] Phase 5: ローカルレビュー（Agent Teams並列化）
- [ ] Phase 6: コミット
- [ ] Phase 7: マージ

### Spec同期記録
| 項目 | 値 |
|------|-----|
| requirements 更新有無 | |
| design Refine 実施有無 | |
| tasks Update 実施有無 | |
| 完了タスク再判定有無 | |
| 同期理由 | |

### Agent Teams 実行記録
| 項目 | 値 |
|------|-----|
| spawn成功 | ✅ / ❌（フォールバック） |
| 並列レビュー所要時間 | 分 |
| security-reviewer 指摘数 | P0: / P1: / P2: |
| logic-reviewer 指摘数 | P0: / P1: / P2: |
| supplement-reviewer 指摘数 | P0: / P1: / P2: |
| 重複排除後の指摘数 | P0: / P1: / P2: |
| CodeRabbit 指摘数 | |
| Codex 指摘数 | P0: / P1: / P2: |
| 修正所要時間 | 分 |
| 合計所要時間 | 分 |
| v7.6逐次比（体感） | 速い / 同程度 / 遅い |

### Debug Mode 実行記録（該当時のみ）
| 項目 | 値 |
|------|-----|
| 発動理由 | |
| 症状 | |
| 根本原因 | |
| 修正内容 | |
| 計測ログ除去 | ✅ / ❌ |
| テスト追加要否 | 要 / 否 |

### 発見・詰まり
| フェーズ | 内容 | 対処 | 時間 | 再発防止 |
|----------|------|------|-----:|---------|
| | | | | |

### 良かった点
- 

### 改善候補
- 

---

## 完走後の振り返り

### 総所要時間
| フェーズ | 時間 |
|----------|-----:|
| Phase 1: Spec作成・同期 | |
| Phase 2: Branch | |
| Phase 2.5: Spec Sync Gate | |
| Phase 3: Test | |
| Phase 4: Impl | |
| Phase 4.5: /simplify | |
| Phase 5: Review | |
| Phase 6-7: Commit/Merge | |
| **合計** | |

### フロー評価

#### Spec同期の評価
| 項目 | 評価 |
|------|------|
| Spec同期は機能したか | |
| Spec Sync Gate は機能したか | |
| requirements/design/tasks の乖離はあったか | |
| 完了タスク再判定は有効だったか | |
| Phase 1 への差し戻しは何回発生したか | |

#### KPI: 手戻り回数
| Phase | 手戻り合計 | 主な原因 |
|-------|--------:|--------|
| Phase 2.5（Spec Sync Gate） | | |
| Phase 3（テスト） | | |
| Phase 4（実装） | | |
| Phase 5（レビュー） | | |
| **合計** | | |

※ 手戻り = CI赤→修正、Exit Criteria未達→差し戻し、レビュー指摘→修正、仕様差分→Phase 1戻り の各1回をカウント。
※ この値が減少傾向ならフローは機能している。増加傾向ならボトルネックを特定して改善する。

#### 機能した点（次バージョンに継続）
1. 
2. 
3. 

#### 重すぎた点（簡略化候補）
1. 
2. 

#### 形骸化した点（削除候補）
1. 
2. 

#### 不足していた点（追加候補）
1. 
2. 

### v7.8.4への改善案（決定稿）
- 

---

## 付録：エラーログ（再現性が命）

### エラー1
- 発生日: 
- フェーズ: 
- エラー内容: 
- 原因: 
- 解決策: 
- 予防策: 
```

-----

## 14. コマンド早見表

### 14.1 tmux/tmuxp

|操作        |コマンド                                    |
|----------|----------------------------------------|
|ai4セッション起動|`ai4` または `cd project && tmuxp load ai4`|
|既存セッションに接続|`tmux attach -t ai4`                    |
|ペイン一覧確認   |`tmux list-panes`                       |
|ペイン間移動    |`Ctrl+a` → `h/j/k/l`                    |
|セッション一覧   |`tmux ls`                               |
|デタッチ      |`Ctrl+a` → `d`                          |
|左右分割      |`Ctrl+a` → `                            |
|上下分割      |`Ctrl+a` → `-`                          |

### 14.2 Claude Code

|操作                         |コマンド                            |
|---------------------------|--------------------------------|
|起動                         |`claude`                        |
|セキュリティレビュー                 |`/security-review`              |
|CodeRabbitレビュー             |`/coderabbit:review`            |
|CodeRabbitレビュー（uncommitted）|`/coderabbit:review uncommitted`|
|CodeRabbitレビュー（base指定）     |`/coderabbit:review --base main`|
|コード品質改善（/simplify）         |`/simplify`                     |
|観点指定の品質改善                  |`/simplify focus on {観点}`       |
|大規模マイグレーション（/batch）        |`/batch {自然言語で変更指示}`            |

### 14.3 Codex CLI

|操作     |コマンド                |
|-------|--------------------|
|起動     |`codex`             |
|レビューモード|`/review`           |
|モデル変更  |`/model gpt-5-codex`|
|終了     |`/exit`             |

### 14.4 Git

|操作           |コマンド                                                   |
|-------------|-------------------------------------------------------|
|featureブランチ作成|`git checkout -b feature/{機能名}`                        |
|差分確認         |`git diff main`                                        |
|コミット         |`git commit -m "..."`                                  |
|マージ          |`git checkout main && git merge --squash feature/{機能名}`|
|ブランチ削除       |`git branch -d feature/{機能名}`                          |

### 14.5 PRコメント（v7.5専用）

|目的            |コメント                                    |
|--------------|----------------------------------------|
|Codexレビュー     |`@codex review`                         |
|Codexカスタムレビュー |`@codex review for security regressions`|
|Bugbot Autofix|`@cursor push {hash}`                   |
|Bugbot手動実行    |`@bugbot run`                           |

### 14.6 プロジェクト初期化

```bash
# ディレクトリ作成
mkdir -p .kiro/steering .kiro/specs src tests logs docs

# 基盤Steering作成
touch .kiro/steering/product.md .kiro/steering/tech.md .kiro/steering/structure.md
touch .kiro/steering/specs.md

# 基本ファイル作成
touch requirements.txt .pre-commit-config.yaml .gitignore
touch CLAUDE.md AGENTS.md REVIEW_SUPPLEMENT.md FLOW_LOG.md
touch src/__init__.py tests/__init__.py

# Git初期化
git init
pre-commit install
git add .
git commit -m "chore: init v7.8.3-local"
```

### 14.7 Kiro Spec操作

|操作               |手順                                               |
|-----------------|-------------------------------------------------|
|Feature Spec 初回生成|Kiro で requirements → design → tasks を生成         |
|要件追加             |requirements.md 更新 → design Refine → tasks Update|
|設計同期             |design.md を Refine                               |
|タスク同期            |tasks.md を Update tasks                          |
|完了タスク再判定         |「Check which tasks are already complete」         |
|Spec Sync Gate 確認|requirements/design/tasks の同期状態を目視確認             |

-----

## 15. レビュー体制比較

### 15.1 v7.5（GitHub用）：5層

|層|ツール                  |観点            |方式    |タイミング |
|-|---------------------|--------------|------|------|
|1|Bugbot               |ロジックバグ、Autofix|自動（PR）|PR作成時 |
|2|Security Review CI   |セキュリティ5観点     |自動（CI）|PR作成時 |
|3|Codex `@codex review`|差分バグ          |手動トリガー|CI通過後 |
|4|補完レビュー               |仕様・設計・AI可読性・回帰|手動    |Codex後|
|5|Devin / CodeRabbit   |設計観点・サマリー     |自動    |PR作成時 |

### 15.2 v7.7-local（Agent Teams並列化）：5層

|層|ツール                  |観点                   |方式       |タイミング       |
|-|---------------------|---------------------|---------|------------|
|0|**/simplify（SHOULD）**|再利用性・品質・効率性          |**自動**   |実装コミット後     |
|1|**Agent Teams（3並列）** |セキュリティ + ロジック + 設計・仕様|**並列自動** |/simplify後  |
|2|/coderabbit:review   |ロジックバグ補完             |手動       |Agent Teams後|
|3|Codex /review（tmux）  |クロスチェック（別AI視点）       |tmux連携   |CodeRabbit後 |
|4|pre-commit           |pytest               |自動（コミット時）|コミット時       |

### 15.3 v7.6-local（フォールバック）との比較

|項目      |v7.6-local（フォールバック）|v7.7-local（Agent Teams）|
|--------|-------------------|-----------------------|
|レビューステップ|6（逐次）              |4（並列+逐次）               |
|所要時間    |20-45分             |15-28分                 |
|コンテキスト汚染|あり（1ウィンドウで全実行）     |なし（teammate独立）         |
|外部ツール連携 |逐次                 |逐次（変更なし）               |
|トークン消費  |1x                 |約3x（Step 1のみ）          |
|フォールバック |-                  |v7.6逐次フローに退行可          |

-----

## 16. フロー使い分け

### 16.1 GitHub有無

|状況                      |フロー                    |月額  |
|------------------------|-----------------------|---:|
|GitHubでPR運用             |v7.5                   |$319|
|Git管理のみ（GitHub/GitLabなし）|v7.7-local             |$279|
|社内GitLab                |v7.7-local（GitLab対応要調査）|$279|
|個人プロジェクト（GitHub不要）      |v7.7-local             |$279|

### 16.2 作業種別

|状況         |実行フェーズ                                           |
|-----------|-------------------------------------------------|
|新機能追加      |Phase 1〜最後（フル）                                   |
|バグ修正       |原則 Phase 1 で既存Spec同期確認 → Phase 3〜最後              |
|要件追加       |Phase 1 からやり直し                                   |
|設計変更       |Phase 1 からやり直し                                   |
|リファクタリング   |Phase 1 で tasks との整合確認後、Phase 4〜最後               |
|ドキュメント修正   |Kiro関連なら Phase 1 を含む。非Kiroなら Phase 6〜最後          |
|セキュリティ修正   |Phase 1 で影響要件確認 + Phase 4〜最後 + /security-review重点|
|大規模マイグレーション|/batch 専用ワークフロー（MAY）※下記参照                        |

**原則：**
仕様差分・要件差分・設計差分が見つかった時点で、作業フェーズに関係なく Phase 1 に戻る。

**大規模マイグレーション（/batch）の運用（MAY）**

通常のPhase 1〜7フローとは別ルートで実行する。

1. `/batch {変更内容}` を実行 → 調査・計画フェーズが自動開始
2. 計画を人間が確認・承認（MUST）
3. 並列実行（各ユニットは独立worktree、内部で/simplify自動実行）
4. 結果のPR or コミットを人間がレビュー（MUST）
5. Canon TDD制約（tests/変更禁止）は/batchにも適用される

**Phase 4 ツール選択 / Phase 0 利用判断**

|作業内容             |使用ツール                             |
|-----------------|----------------------------------|
|未知リポジトリ調査・隔離実行   |Claude Code on the web（Phase 0 専用）|
|要件解釈・原因分析・実装方針決定 |Claude Code（CLI / IDE）            |
|機械的修正・横断修正・実装修正反映|Cursor Cloud Agent（Phase 4 実行役）   |

### 16.3 Phase Exit Criteria（Phase 2.5・3・4）

各Phaseの完了判定を以下で固定する。未達項目がある場合は次Phaseに進まない（MUST）。

**Phase 2.5: Spec Sync Gate**

|#|条件                                     |判定方法   |
|-|---------------------------------------|-------|
|1|requirements.md が最新である                 |目視     |
|2|requirements 更新後に design.md が Refine 済み|目視     |
|3|design 更新後に tasks.md が Update tasks 済み |目視     |
|4|必要時に完了タスク再判定が済んでいる                     |目視     |
|5|spec コミットが残っている                        |自動 / 目視|

**Phase 3: テスト作成（Cursor）**

|#|条件                                                  |判定方法|
|-|----------------------------------------------------|----|
|1|requirements.md の全 Acceptance Criteria に対応するテストが存在する|目視  |
|2|エッジケース（空リスト、None、境界値）のテストが含まれる                      |目視  |
|3|`pytest tests/ -v` が全 FAIL or ERROR で終了する（実装未着手の証明） |自動  |
|4|src/ を参照していない（`grep -r "from src" tests/` が空）       |自動  |
|5|Spec Sync Gate を通過済み                                |目視  |

**Phase 4: 実装（Claude Code / Cursor Cloud Agent）**

|#|条件                                             |判定方法|
|-|-----------------------------------------------|----|
|1|`pytest tests/ -v` が全 PASS                     |自動  |
|2|lint / format が pre-commit で PASS              |自動  |
|3|変更範囲が tasks.md のスコープ内                          |目視  |
|4|tests/ に差分がない（`git diff --name-only tests/` が空）|自動  |
|5|依存追加がある場合、requirements.txt に明示かつ人間が承認済み        |目視  |
|6|実装中に仕様差分が出た場合は Phase 1 に戻った                    |目視  |

-----

## 17. トラブルシューティング

### 17.0 Kiro同期系

|エラー / 症状                  |原因                    |対処                                                          |
|--------------------------|----------------------|------------------------------------------------------------|
|requirements.md だけ更新されている |design/tasks 未同期      |design.md を Refine → tasks.md を Update tasks                |
|tasks.md が古い              |Update tasks 未実施      |tasks.md を更新してコミット                                          |
|既に終わっている作業が未完了扱い          |完了タスク再判定未実施           |Spec session で「Check which tasks are already complete」      |
|Kiro の提案がプロジェクト前提を外す      |Steering 不足           |`.kiro/steering/product.md` / `tech.md` / `structure.md` を整備|
|Claude Code と Kiro の解釈がずれる|Spec Sync Gate を飛ばしている|Phase 2.5 に戻って同期確認                                          |

### 17.1 共通

|エラー                      |原因                |対処                                        |
|-------------------------|------------------|------------------------------------------|
|`ModuleNotFoundError`    |requirements.txt漏れ|依存関係追加、`pip install -r requirements.txt`  |
|pre-commit失敗             |pytest未インストール     |`pip install pytest`                      |
|CodeRabbitが動かない          |認証切れ              |`coderabbit auth login`                   |
|`/coderabbit:review`が動かない|プラグイン未インストール      |`/install @coderabbit/coderabbit-plugin`  |
|Skillが認識されない             |パス間違い             |`~/.claude/skills/`または`~/.codex/skills/`確認|

### 17.2 v7.5専用

|エラー                   |原因             |対処                                   |
|----------------------|---------------|-------------------------------------|
|Bugbot沈黙              |リポジトリ未連携       |Cursor Dashboardで有効化                 |
|`@codex review` 反応なし  |Code review未有効化|chatgpt.com/codexで設定                 |
|Claude Code Action動かない|APIキー未設定       |GitHub Secrets `ANTHROPIC_API_KEY` 確認|
|Security Review CI動かない|workflow未作成    |security-review.yml追加                |

### 17.3 v7.7-local専用

|エラー                     |原因           |対処                             |
|------------------------|-------------|-------------------------------|
|tmux send-keys失敗        |ペイン番号間違い     |`tmux list-panes`で確認           |
|Codex→Claude Codeが実行されない|仕様（手動Enter必要）|Pane0でEnter押す                  |
|ai4コマンドが見つからない          |PATH未設定      |`export PATH="$HOME/bin:$PATH"`|
|tmuxpがない                |未インストール      |`pip install tmuxp`            |
|bash\rエラー（WSL）          |CRLF         |`dos2unix ~/bin/ai4`           |

### 17.4 Agent Teams専用

|エラー                  |原因                                        |対処                               |
|---------------------|------------------------------------------|---------------------------------|
|teammate が spawn されない|`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 未設定|環境変数またはsettings.json確認           |
|teammate が spawn されない|タスクが単純すぎると判断された                           |明示的に「agent team を作成して」と指示        |
|teammate が途中で停止      |5分ハートビートタイムアウト                            |Lead から再spawn、または逐次フォールバック       |
|split-pane が表示されない   |VS Code統合ターミナル使用                          |tmux または iTerm2 で実行              |
|Max 20 上限に早く到達       |teammate × 3 のトークン消費                      |1日のAgent Teams使用回数を制限（目安: 3-5回/日）|
|teammate の結果が不完全     |コンテキスト不足                                  |spawn プロンプトにプロジェクト概要を含める         |

### 17.5 Cursor Debug Mode（実行時バグ対応）

Debug Mode は「テストは通るが実行時に壊れる」類の問題に対する標準手順。

**発動条件（SHOULD）：**

- レビューで「挙動が怪しいが原因特定できない」指摘が出た
- テスト全PASSだが手動確認で期待と異なる動作がある
- レースコンディション / タイミング依存 / メモリリークの疑い
- リグレッション（以前は動いていたのに動かなくなった）

**手順：**

1. Pane 1（Cursor）で Debug Mode を起動
2. バグの症状・再現手順・期待動作をできるだけ詳しく記述
3. Debug Mode が仮説を立て、計測用ログ（インストルメンテーション）を追加
4. 指示された再現手順を実行（人間操作が必要）
5. 収集ログに基づき根本原因を特定、修正を実施
6. 再現手順を再実行して修正を検証
7. **計測ログを全除去（Debug Mode のクリーンアップ機能）**

**注意事項：**

|注意点                   |理由・対処                              |
|----------------------|-----------------------------------|
|計測ログは vibelogger 制約の例外|Debug Mode が自動追加するため。ただし修正確認後に必ず全除去|
|本番環境では実行しない           |計測ログが本番に混入するリスク。ローカル開発環境限定         |
|人間の再現操作が必須            |完全自動化フローには組み込めない。オンデマンド発動          |
|FLOW_LOG に記録する        |発動理由・根本原因・修正内容を記録し、テスト追加の判断材料にする   |

|エラー              |原因             |対処                           |
|-----------------|---------------|-----------------------------|
|Debug Mode が起動しない|Cursor バージョンが古い|Cursor を最新版にアップデート           |
|計測ログがコミットに混入     |クリーンアップ忘れ      |`git diff` で確認、Debug Mode で除去|
|再現できない           |手順が不正確         |症状・手順をより具体的に記述して再実行          |

-----

## 18. 重要な学び

### 18.1 Codexの特性理解が必須

- 「明確なバグ」のみ検出
- セキュリティ・仕様判断は苦手
- AGENTS.mdはoverrideされる可能性あり
- **解決策**: 補完レビューで網羅

### 18.2 2段階レビューの有効性

- AIも「指摘を見つけると満足して終わる」
- 機械レビュー → 補完レビューで網羅
- Claude Code（実装者）≠ Codex（レビュー者）の分離が重要

### 18.3 構造の力で品質を守る

- 「意志の力」ではなく「ツール制約」で強制
- tests/変更禁止 → CLAUDE.md + AGENTS.md + Bugbot設定
- pre-commit → コミット時に自動テスト
- Spec Sync Gate → 未同期のまま実装に進むことを構造的に防ぐ

### 18.4 環境まで含めた設計

- tmux/tmuxp でAI間連携を物理的に構築
- Skill でAIの行動を固定化（DSL化）
- GitHub Actions / pre-commit で自動化
- Kiro Steering でAIの解釈基盤を固定化

### 18.5 GitHub有無で全く異なるフロー

- PR系ツール（Bugbot, Security Review CI, Devin）はGitHub必須
- ローカルツール（/security-review, /coderabbit:review, Codex CLI）で代替可能
- コストも$40削減（$319→$279）

### 18.6 Agent Teamsによる並列化の効果

- 独立コンテキストで視点の偏り（コンテキスト汚染）を排除
- レビュー時間を30-40%短縮（20-45分 → 15-28分）
- 外部ツール（CodeRabbit, Codex）は並列化不可 → Lead が逐次実行
- トークン消費は約3倍 → Max 20上限に注意

### 18.7 テストで捕まらないバグへの対処

- Canon TDDは「テストで検出可能なバグ」には強いが、レースコンディション・メモリリーク・タイミング依存の問題には無力
- 静的レビュー（Agent Teams / CodeRabbit / Codex）も実行時挙動は検出できない
- Cursor Debug Mode は「仮説→計測→証拠→修正」の科学的アプローチでこの穴を埋める
- ただし人間の再現操作が必須であり、完全自動化はできない → SHOULD（オンデマンド）が適正

### 18.8 「書く速度」と「維持する速度」の分離

- AIによるコード生成は速いが、生成コードは冗長になりやすい（重複ロジック・過剰な抽象化・不要なネスト）
- 冗長なコードは以降のセッションでトークンを余分に消費し、Max 20上限を圧迫する
- `/simplify` は「機能不変のまま書き方だけ改善」するため、Canon TDDとの整合性が高い（テストはそのままPASS）
- レビュー前に実行することで、Agent Teamsの指摘がP1/P2の可読性問題ではなく本質的なバグ・設計問題に集中する
- `/batch` は「退屈だが量が多い機械的変更」をworktree分離で並列化し、マイグレーション工数を桁で削減する

### 18.9 Living Spec の意義

- Kiro Spec を「一度作って終わり」にすると、実装が進むにつれて Spec と実態が乖離する
- 乖離した Spec を参照してテストを書くと、テスト自体が仕様ズレを含む
- requirements → design → tasks の同期チェーンを維持することで、Spec が常に信頼できる情報源（Single Source of Truth）になる
- Spec Sync Gate は「乖離を防ぐ構造」であり、人間の注意力に依存しない

-----

## 19. 変更履歴

|バージョン  |日付        |変更内容                                                                                                                                                                                                                                                |
|-------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|v7.3   |-         |初版（ドライラン完了）                                                                                                                                                                                                                                         |
|v7.4   |-         |Codexの特性を反映、2段階レビュー導入                                                                                                                                                                                                                               |
|v7.5   |-         |Claude Code `/security-review` 追加、セキュリティ自動化                                                                                                                                                                                                         |
|v7.6   |-         |2フロー体制（GitHub用/ローカル用）確立                                                                                                                                                                                                                             |
|v7.6   |-         |tmux-sender/Codex連携追加（Zenn記事参照）                                                                                                                                                                                                                     |
|v7.6   |-         |ai4（4ペイン構成）対応                                                                                                                                                                                                                                       |
|v7.6   |-         |FLOW_LOG.md追加（実戦投入用）                                                                                                                                                                                                                                |
|v7.6   |-         |ChatGPTレビュー反映（再発防止列、Ctrl+a前提）                                                                                                                                                                                                                       |
|v7.7   |2025-02-07|Agent Teams レビュー並列化導入（Phase 5）                                                                                                                                                                                                                      |
|v7.7   |2025-02-07|Phase 5 を 6逐次ステップ → 4層（並列+逐次）に再構成                                                                                                                                                                                                                   |
|v7.7   |2025-02-07|フォールバック機構追加（Agent Teams失敗 → v7.6逐次）                                                                                                                                                                                                                 |
|v7.7   |2025-02-07|FLOW_LOG.md に Agent Teams 実行記録テンプレート追加                                                                                                                                                                                                              |
|v7.7.1 |2026-03-01|Cursor Cloud Agent／Claude Code on the web の位置づけを追記（役割分離・ワンライナー強化）                                                                                                                                                                                   |
|v7.7.2 |2026-03-01|v7.7.1のMarkdown構造破損（§11.3）修正、タイトル不整合修正、禁止事項を補強                                                                                                                                                                                                      |
|v7.7.3 |2026-03-01|§16.2にツール使い分け判断基準を追記（Phase 0 / Phase 4 ツール選択）                                                                                                                                                                                                       |
|v7.8   |2026-03-02|Canon TDD例外手順明文化、Cloud Agent MUST NOT追加、Phase Exit Criteria導入、KPI（手戻り回数）追加                                                                                                                                                                          |
|v7.8.1 |2026-03-03|Cursor Debug Mode導入（Phase 5 SHOULD + §17トラブルシューティング）                                                                                                                                                                                                |
|v7.8.2 |2026-03-03|/simplify（Phase 4.5 SHOULD）・/batch（§16.2 大規模マイグレーション MAY）導入                                                                                                                                                                                         |
|v7.8.3 |2026-03-14|Kiro を Living Spec 前提に再定義。requirements更新→design Refine→tasks Update→完了タスク再判定を正式手順化。Spec Sync Gate（Phase 2.5）導入。基盤Steering（product/tech/structure）追加。Canon TDD例外手順をSpec同期チェーン対応に拡張。FLOW_LOGにSpec同期記録を追加。コミット規約をspec(req)/spec(design)/spec(tasks)に体系化|
|v7.8.3a|2026-03-14|リグレッション修正：specs.md にEARS形式テンプレート・19プロパティ一覧・tasks.mdフォーマットを復元。tech.mdテンプレートにvibelogger詳細を復元                                                                                                                                                          |

-----

# 付録：テンプレートリポジトリ構成

実戦投入を効率化するため、以下の構成でテンプレートリポジトリを作成推奨：

```
v7.8.3-local-template/
├── .kiro/
│   ├── steering/
│   │   ├── product.md
│   │   ├── tech.md
│   │   ├── structure.md
│   │   ├── specs.md
│   │   ├── testing-standards.md
│   │   └── security-policies.md
│   └── specs/
├── src/
│   └── __init__.py
├── tests/
│   └── __init__.py
├── logs/
│   └── .gitkeep
├── docs/
│   └── TMUX_FLOW.md
├── .pre-commit-config.yaml
├── .gitignore
├── CLAUDE.md
├── AGENTS.md
├── REVIEW_SUPPLEMENT.md
├── FLOW_LOG.md
├── requirements.txt
└── README.md
```

**使い方:**

```bash
# テンプレートからクローン
git clone https://github.com/yourname/v7.8.3-local-template.git new-project
cd new-project

# リモート削除（新規プロジェクトとして独立）
rm -rf .git
git init
pre-commit install
git add .
git commit -m "chore: init from v7.8.3-local-template"
```
