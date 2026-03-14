# AGENTS.md

## Overview

このリポジトリはCanon TDD（テスト先行）で開発しています。
tests/ は Cursor が作成し、src/ は Claude Code が実装します。
Kiro Spec は Living Spec として継続的に同期します。

## Review guidelines

### 要件トレーサビリティ（P0）
- .kiro/specs/*/requirements.md の各要件に対応する実装があるか確認
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

### エッジケース（P1）
- 空リスト、空文字列、None、ゼロ除算の考慮漏れ
- 境界値（off-by-one）エラー

### 型安全性（P2）
- 型ヒントの欠落
- 型の不一致（Any型の多用）

## Coding guidelines

- Python >= 3.8
- 型ヒント必須
- Google style docstring
- snake_case（関数/変数）、PascalCase（クラス）

## Project structure

```
src/video_motion_extraction/  # 実装コード（Claude Code担当）
tests/                        # テストコード（Cursor担当、変更禁止）
.kiro/specs/                  # 仕様書（Kiro生成・同期）
.kiro/steering/               # 基盤Steering（product/tech/structure）
logs/                         # ログ出力
```

## Agent Instructions
- すべての応答は日本語で行うこと
- エージェントの役割はレビュワーとし、変更内容の不具合、回帰リスク、設計上の懸念、テスト不足を優先して確認すること
- 指摘事項がない場合は、その旨を明確に記載すること
