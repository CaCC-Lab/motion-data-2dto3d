# Tech Steering

## 言語・ランタイム
- Python >= 3.8

## 主要ライブラリ
- MMPose >= 1.0.0（2Dポーズ推定）
- VideoPose3D（2D→3D変換）
- OpenCV >= 4.5.0（動画処理）
- PyTorch >= 1.10.0 + CUDA >= 11.0（GPU推論）
- NumPy >= 1.20.0, SciPy >= 1.7.0（数値計算・補間）
- pytest + hypothesis（テスト）

## コーディング規約
- 型ヒント必須
- Google style docstring
- snake_case（関数/変数）、PascalCase（クラス）、UPPER_SNAKE_CASE（定数）
- @dataclass でコアデータモデル定義

## ロギング
- ライブラリ: Python標準 logging
- 各ログに以下を含める:
  - operation: 処理名
  - context: コンテキスト情報

## 開発フロー
- Canon TDD（テスト先行、tests/変更禁止）
- Living Spec（Kiro Spec 継続同期）
- AI開発フロー v7.8.3a 準拠
