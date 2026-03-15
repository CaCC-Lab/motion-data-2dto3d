"""Gradio GUI E2E テスト (Playwright)."""

import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

# pytest-playwright がインストールされていない場合はスキップ
pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GUI_MODULE = "video_motion_extraction.gui"
BASE_URL = "http://127.0.0.1:7860"
TEST_VIDEO = PROJECT_ROOT / "data" / "input" / "test_clip.mp4"


def _wait_for_server(url: str, timeout: float = 30) -> bool:
    """サーバー起動を待機."""
    import urllib.request
    import urllib.error

    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


@pytest.fixture(scope="module")
def gui_server():
    """Gradioサーバーをバックグラウンド起動."""
    proc = subprocess.Popen(
        [sys.executable, "-m", GUI_MODULE],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**__import__("os").environ},
    )
    if not _wait_for_server(BASE_URL, timeout=30):
        proc.terminate()
        proc.wait(timeout=5)
        pytest.fail("Gradio server failed to start within 30s")
    try:
        yield proc
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="module")
def browser_page(gui_server):
    """Playwrightブラウザページ."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        yield page
        browser.close()


# ---- 1. UI表示テスト（GPU不要） ----


def test_gui_title_displayed(browser_page):
    """「Video Motion Extraction」が表示される."""
    page = browser_page
    heading = page.get_by_role("heading", name="Video Motion Extraction")
    heading.wait_for(state="visible", timeout=5000)
    assert heading.is_visible()


def test_gui_run_button_exists(browser_page):
    """「実行」ボタンが存在する."""
    page = browser_page
    btn = page.get_by_role("button", name="実行")
    btn.wait_for(state="visible", timeout=5000)
    assert btn.is_visible()


def test_gui_all_controls_visible(browser_page):
    """全UIコンポーネントが表示される."""
    page = browser_page
    # Gradio Sliderはspinbutton+sliderの2要素になるため、roleで個別に確認
    roles_and_names = [
        ("spinbutton", "number input for FPS"),
        ("spinbutton", "number input for 信頼度閾値"),
        ("spinbutton", "number input for スムージング窓"),
        ("textbox", "除外関節 (カンマ区切り)"),
        ("listbox", "出力フォーマット"),
        ("spinbutton", "number input for バッチサイズ"),
        ("radio", "position"),
        ("radio", "rotation"),
        ("spinbutton", "number input for 3Dスムージングσ"),
        ("spinbutton", "number input for ルートモーション補正係数"),
    ]
    for role, name in roles_and_names:
        loc = page.get_by_role(role, name=name)
        loc.first.wait_for(state="visible", timeout=3000)
        assert loc.first.is_visible(), f"Role '{role}' name '{name}' not visible"
    # 入力動画・ログはラベルで確認
    assert page.get_by_text("入力動画", exact=False).first.is_visible()
    assert page.get_by_text("ログ", exact=False).first.is_visible()


def test_gui_default_values(browser_page):
    """デフォルト値が仕様通り."""
    page = browser_page
    # FPS: 30 (spinbuttonの値を取得)
    fps_input = page.get_by_role("spinbutton", name="number input for FPS")
    fps_input.wait_for(state="visible")
    fps_val = fps_input.input_value()
    assert int(float(fps_val)) == 30
    # 出力フォーマット: bvh (listboxの表示値を確認)
    format_box = page.get_by_role("listbox", name="出力フォーマット")
    format_box.wait_for(state="visible")
    assert format_box.is_visible()
    # BVHモード: position が選択されている
    position_radio = page.get_by_role("radio", name="position")
    assert position_radio.is_visible()


# ---- 2. パラメータ操作テスト（GPU不要） ----


def test_gui_slider_fps_change(browser_page):
    """FPSスライダーを変更できる."""
    page = browser_page
    fps_input = page.get_by_role("spinbutton", name="number input for FPS")
    fps_input.fill("24")
    page.wait_for_timeout(300)
    val = fps_input.input_value()
    assert int(float(val)) == 24


def test_gui_dropdown_format_change(browser_page):
    """出力フォーマットを変更できる."""
    page = browser_page
    # Gradio 4のDropdownはlistbox、クリックで開いてオプションをクリック
    dropdown = page.get_by_role("listbox", name="出力フォーマット")
    dropdown.click()
    page.wait_for_timeout(300)
    page.get_by_role("option", name="json").click()
    page.wait_for_timeout(300)
    # 選択後、listboxが閉じる
    assert page.get_by_role("listbox", name="出力フォーマット").is_visible()


def test_gui_radio_bvh_mode_change(browser_page):
    """BVHモードを切替できる."""
    page = browser_page
    rotation_radio = page.get_by_role("radio", name="rotation")
    rotation_radio.click()
    rotation_radio.wait_for(state="visible")
    assert rotation_radio.is_visible()


def test_gui_textbox_remove_joints(browser_page):
    """除外関節テキストに入力できる."""
    page = browser_page
    textbox = page.get_by_label("除外関節 (カンマ区切り)")
    textbox.fill("left_hand_*,right_hand_*")
    value = textbox.input_value()
    assert "left_hand_*" in value
    assert "right_hand_*" in value


# ---- 3. エラーハンドリングテスト（GPU不要） ----


def test_gui_run_without_video(browser_page):
    """動画未アップロードで実行 → エラーメッセージ表示."""
    page = browser_page
    run_btn = page.get_by_role("button", name="実行")
    run_btn.click()
    # エラーメッセージがログエリアに表示される（Gradioの非同期更新を待つ）
    log_area = page.get_by_label("ログ")
    log_area.wait_for(state="visible")
    text = ""
    for _ in range(30):  # 最大15秒
        page.wait_for_timeout(500)
        try:
            text = log_area.input_value()
        except Exception:
            text = log_area.inner_text() or ""
        if "動画ファイルをアップロードしてください" in text or "Error" in text:
            break
    else:
        body_text = page.locator("body").inner_text()
        pytest.fail(
            f"Expected error message not found. "
            f"Log (first 300 chars): {repr(text[:300])}. "
            f"Body has 'Error': {'Error' in body_text}"
        )
    assert "動画ファイルをアップロードしてください" in text or "Error" in text


# ---- 4. パイプライン統合テスト（GPU必要） ----


@pytest.mark.gpu
def test_gui_full_pipeline(browser_page):
    """動画アップロード → 実行 → 出力ファイルダウンロード可能."""
    if not TEST_VIDEO.exists():
        pytest.skip(f"Test video not found: {TEST_VIDEO}")

    page = browser_page

    # ファイルアップロード: 入力動画用のinput[type=file]（左カラムの最初）に直接セット
    file_inputs = page.locator('input[type="file"]')
    file_inputs.first.set_input_files(str(TEST_VIDEO))

    # アップロード完了待ち（Gradioが動画を処理する時間）
    page.wait_for_timeout(5000)

    # 実行ボタンクリック
    run_btn = page.get_by_role("button", name="実行")
    run_btn.click()

    # 完了メッセージをログエリアでポーリング（最大180秒）
    log_box = page.get_by_label("ログ")
    log_box.wait_for(state="visible")
    log_content = ""
    for _ in range(180):  # 180秒
        page.wait_for_timeout(1000)
        try:
            log_content = log_box.input_value()
        except Exception:
            log_content = log_box.inner_text() or ""
        if "Done! Exported as" in log_content:
            break
        if "Error" in log_content and "動画ファイルをアップロード" not in log_content:
            pytest.fail(f"Pipeline failed. Log:\n{log_content}")
    else:
        pytest.fail(f"Timeout waiting for pipeline completion. Log (last 500 chars):\n{repr(log_content[-500:])}")

    assert "Done! Exported as" in log_content

    # 出力ファイルのダウンロードが可能（ページ内にファイルリンクが表示される）
    # Gradio Fileは .bvh 等の拡張子を含むリンクを表示
    download_link = page.locator('a[href*=".bvh"], a[href*=".fbx"], a[href*=".json"]').first
    download_link.wait_for(state="visible", timeout=10000)
    assert download_link.is_visible()
