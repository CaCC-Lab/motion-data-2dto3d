# プロジェクト全体のBugbotルール

## プロジェクト概要

- 言語: Python >= 3.8
- テスト: pytest, Hypothesis
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

### テスト
- tests/ディレクトリの変更は要注意フラグ（Canon TDD違反の可能性）
- Property-based testing（Hypothesis）推奨
- tests/ 変更時はP0として報告

### 構造
- 実装コードはsrc/video_motion_extraction/配下に配置
- テストコードはtests/配下に配置
