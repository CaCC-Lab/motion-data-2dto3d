# Cursor タスク: Gradio GUI の Playwright MCP E2E テスト作成

## 概要

`src/video_motion_extraction/gui.py` の Gradio WebUI に対する E2E テストを作成してください。
**Playwright MCP サーバー** を使用してブラウザ操作を行います。

## Playwright MCP について

このプロジェクトでは Playwright MCP サーバーが設定済みです（`~/.claude/settings.json`）。

```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp", "--allowed-hosts", "tryon-dev.mitemite.app"]
  }
}
```

### 事前準備（必須）

テスト前に `--allowed-hosts` に `localhost` を追加する必要があります:

```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp", "--allowed-hosts", "tryon-dev.mitemite.app,localhost"]
  }
}
```

### Playwright MCP で使用可能なツール

テストコード内ではなく、**Cursor のMCPツールとして直接呼び出し**て操作します:

| ツール | 用途 |
|---|---|
| `browser_navigate` | URL へ遷移 |
| `browser_screenshot` | スクリーンショット取得 |
| `browser_click` | 要素をクリック |
| `browser_type` | テキスト入力 |
| `browser_select_option` | ドロップダウン選択 |
| `browser_snapshot` | アクセシビリティツリー取得（DOM構造確認） |
| `browser_wait_for_text` | テキスト出現を待機 |
| `browser_file_upload` | ファイルアップロード |
| `browser_tab_list` | タブ一覧 |
| `browser_close` | ブラウザを閉じる |

## 対象ファイル

- テスト対象: `src/video_motion_extraction/gui.py`
- テスト作成先: `tests/test_gui_e2e.py`
- 入力動画: `data/input/test_clip.mp4`（1920x1080, 25fps, 283frames, 野球バッターのスイング）

## GUI仕様

### 起動方法

```bash
vme-gui
# または
python -m video_motion_extraction.gui
```

Gradio が `http://localhost:7860` で起動。

### UIコンポーネント一覧

| コンポーネント | 型 | ラベル | デフォルト | 範囲 |
|---|---|---|---|---|
| video_input | gr.Video | 入力動画 | — | — |
| fps | gr.Slider | FPS | 30 | 1〜120 |
| threshold | gr.Slider | 信頼度閾値 | 0.3 | 0.0〜1.0 |
| smoothing | gr.Slider | スムージング窓 | 5 | 1〜21 |
| remove_joints | gr.Textbox | 除外関節 (カンマ区切り) | — | — |
| output_format | gr.Dropdown | 出力フォーマット | bvh | bvh/fbx/json |
| batch_size | gr.Slider | バッチサイズ | 32 | 1〜128 |
| bvh_mode | gr.Radio | BVHモード | position | position/rotation |
| smooth_3d | gr.Slider | 3Dスムージングσ | 1.0 | 0.0〜5.0 |
| root_motion_scale | gr.Slider | ルートモーション補正係数 | 2.5 | 0.1〜10.0 |
| run_btn | gr.Button | 実行 | — | — |
| output_file | gr.File | 出力ファイル | — | — |
| status_log | gr.Textbox | ログ | — | — |

### パイプライン処理フロー

```
動画アップロード → パラメータ設定 → 実行ボタン →
  フレーム抽出 → 2Dポーズ推定 → データ処理 → 3D変換 → ファイル出力
```

## テスト手順（Playwright MCP を使用）

### Step 0: Gradioサーバー起動

```bash
# バックグラウンドで起動
python -m video_motion_extraction.gui &
# 起動完了を待つ（約5秒）
sleep 5
```

### Step 1: 初期表示の確認

1. `browser_navigate` → `http://localhost:7860`
2. `browser_snapshot` → アクセシビリティツリーで全コンポーネントを確認
3. `browser_screenshot` → 初期状態のスクリーンショット保存
4. 確認項目:
   - タイトル「Video Motion Extraction」が表示される
   - 「実行」ボタンが存在する
   - 全スライダー・ドロップダウン・ラジオボタンが表示される

### Step 2: デフォルト値の確認

`browser_snapshot` の結果から以下を検証:
- FPS: 30
- 信頼度閾値: 0.3
- スムージング窓: 5
- バッチサイズ: 32
- 出力フォーマット: bvh
- BVHモード: position
- 3Dスムージングσ: 1.0
- ルートモーション補正係数: 2.5

### Step 3: パラメータ操作テスト

1. `browser_click` → FPSスライダーを操作
2. `browser_select_option` → 出力フォーマットを「json」に変更
3. `browser_click` → BVHモードを「rotation」に切替
4. `browser_type` → 除外関節に「left_hand_*,right_hand_*」を入力
5. 各操作後に `browser_snapshot` で値が反映されていることを確認

### Step 4: エラーハンドリングテスト

1. 動画をアップロードせずに「実行」ボタンを `browser_click`
2. `browser_wait_for_text` → 「Error: 動画ファイルをアップロードしてください」が表示される
3. `browser_screenshot` → エラー状態のスクリーンショット保存

### Step 5: パイプライン統合テスト（GPU必要、オプション）

1. `browser_file_upload` → `data/input/test_clip.mp4` をアップロード
2. `browser_click` → 「実行」ボタンをクリック
3. `browser_wait_for_text` → 「Done! Exported as bvh」の出現を待機（タイムアウト: 120秒）
4. `browser_snapshot` → 出力ファイルのダウンロードリンクが存在することを確認
5. `browser_screenshot` → 完了状態のスクリーンショット保存

### Step 6: クリーンアップ

1. `browser_close` → ブラウザを閉じる
2. Gradioサーバーを停止

## テストコード作成要件

上記のPlaywright MCP手動テスト手順を元に、**pytest + playwright（Pythonライブラリ）** でも自動実行できるテストファイルを作成してください。

### テストファイル: `tests/test_gui_e2e.py`

```python
"""Gradio GUI E2E テスト (Playwright)."""

import subprocess
import time
import signal
import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="module")
def gui_server():
    """Gradioサーバーをバックグラウンド起動."""
    proc = subprocess.Popen(
        ["python", "-m", "video_motion_extraction.gui"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(5)  # 起動待ち
    yield proc
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=10)

@pytest.fixture(scope="module")
def browser_page(gui_server):
    """Playwrightブラウザページ."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:7860")
        page.wait_for_load_state("networkidle")
        yield page
        browser.close()
```

### 作成すべきテストケース

#### 1. UI表示テスト（GPU不要）

- `test_gui_title_displayed` — 「Video Motion Extraction」が表示される
- `test_gui_all_controls_visible` — 全UIコンポーネントが表示される
- `test_gui_default_values` — デフォルト値が仕様通り
- `test_gui_run_button_exists` — 「実行」ボタンが存在

#### 2. パラメータ操作テスト（GPU不要）

- `test_gui_slider_fps_change` — FPSスライダーを変更できる
- `test_gui_dropdown_format_change` — 出力フォーマットを変更できる
- `test_gui_radio_bvh_mode_change` — BVHモードを切替できる
- `test_gui_textbox_remove_joints` — 除外関節テキストに入力できる

#### 3. エラーハンドリングテスト（GPU不要）

- `test_gui_run_without_video` — 動画未アップロードで実行 → エラーメッセージ表示

#### 4. パイプライン統合テスト（GPU必要）

- `test_gui_full_pipeline` — 動画アップロード → 実行 → 出力ファイルダウンロード可能
  - `@pytest.mark.gpu` でマーク
  - ログに「Done! Exported as bvh」が含まれることを検証

## 注意事項

- **Playwright MCP を先に使って手動でDOM構造を調査**してからテストコードを書くこと
  - `browser_snapshot` でアクセシビリティツリーを取得し、正確なセレクタを特定する
  - Gradio のDOM構造はバージョンにより変わるため、実際のDOMから特定が必須
- GPU依存テストは `@pytest.mark.gpu` を付け、`pytest -m "not gpu"` でスキップ可能にする
- conftest.py の変更が必要なら `tests/conftest.py` に追加

## 実行方法

```bash
# Playwright インストール
pip install playwright pytest-playwright
playwright install chromium

# E2Eテスト実行（GPU不要テストのみ）
pytest tests/test_gui_e2e.py -m "not gpu" -v

# 全テスト実行（GPU環境）
pytest tests/test_gui_e2e.py -v
```

## 推奨ワークフロー

1. Gradioサーバーを手動起動: `python -m video_motion_extraction.gui`
2. Playwright MCP で `browser_navigate` → `http://localhost:7860`
3. `browser_snapshot` でDOM構造を調査
4. 各コンポーネントのセレクタを特定
5. テストコードを作成
6. `pytest tests/test_gui_e2e.py -m "not gpu" -v` で動作確認
