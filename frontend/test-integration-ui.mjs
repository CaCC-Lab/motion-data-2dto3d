/**
 * Playwright E2Eテスト: Integration UIワークフロー
 * - Integrateボタンが有効になるか
 * - 動画アップロードができるか
 * - プロンプト入力 + 動画アップロード後にボタンが有効になるか
 */
import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('=== Test 1: Page loads ===');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  const title = await page.textContent('h1');
  console.log(`  Title: ${title}`);
  assert(title?.includes('MOTION LAB'), 'Title should contain MOTION LAB');

  console.log('=== Test 2: Integrate button exists and is enabled ===');
  // Find the Integrate button
  const integrateBtn = page.locator('button', { hasText: 'Integrate' });
  const btnCount = await integrateBtn.count();
  console.log(`  Integrate buttons found: ${btnCount}`);
  assert(btnCount > 0, 'Integrate button should exist');

  const isDisabled = await integrateBtn.getAttribute('disabled');
  console.log(`  Disabled: ${isDisabled}`);
  assert(isDisabled === null, 'Integrate button should be enabled (integration API is running)');

  console.log('=== Test 3: Switch to Integration mode ===');
  await integrateBtn.click();
  await sleep(500);

  // Check subtitle changed
  const subtitle = await page.textContent('span');
  console.log(`  Subtitle after switch: looking for integration UI...`);

  // Check that CREATE MODEL section exists
  const createModelSection = page.locator('text=CREATE MODEL');
  const cmCount = await createModelSection.count();
  console.log(`  CREATE MODEL section: ${cmCount > 0 ? 'found' : 'NOT found'}`);
  assert(cmCount > 0, 'CREATE MODEL section should be visible');

  // Check CAPTURE MOTION section
  const captureSection = page.locator('text=CAPTURE MOTION');
  console.log(`  CAPTURE MOTION section: ${(await captureSection.count()) > 0 ? 'found' : 'NOT found'}`);

  // Check ANIMATE section
  const animateSection = page.locator('text=ANIMATE');
  console.log(`  ANIMATE section: ${(await animateSection.count()) > 0 ? 'found' : 'NOT found'}`);

  console.log('=== Test 4: Execute button is disabled (no input yet) ===');
  const execBtn = page.locator('button', { hasText: '統合パイプラインを実行' });
  const execDisabled = await execBtn.getAttribute('disabled');
  console.log(`  Execute button disabled: ${execDisabled !== null}`);
  assert(execDisabled !== null, 'Execute button should be disabled initially');

  // Check hint message
  const hint = page.locator('text=プロンプトと動画を入力してください');
  const hintVisible = (await hint.count()) > 0;
  console.log(`  Hint message visible: ${hintVisible}`);

  console.log('=== Test 5: Enter prompt ===');
  const textarea = page.locator('textarea');
  await textarea.fill('ピッチャーのキャラクター');
  await sleep(300);

  // Check hint changed
  const hint2 = page.locator('text=動画をアップロードしてください');
  const hint2Visible = (await hint2.count()) > 0;
  console.log(`  Hint after prompt: ${hint2Visible ? 'asks for video' : 'unknown'}`);

  console.log('=== Test 6: Upload video file ===');
  // Create a small test video file (just a valid mp4 header)
  const fs = await import('fs');
  const testVideoPath = '/tmp/test_pitch.mp4';

  // Use existing test clip if available, otherwise create a minimal file
  const realVideo = '/home/ryu/projects/motion-data-2dto3d/data/input/test_clip.mp4';
  let videoPath;
  if (fs.existsSync(realVideo)) {
    videoPath = realVideo;
    console.log('  Using real test video');
  } else {
    // Create minimal mp4-like file
    fs.writeFileSync(testVideoPath, Buffer.alloc(1024));
    videoPath = testVideoPath;
    console.log('  Using dummy video');
  }

  // Find file input and upload
  const fileInput = page.locator('input[type="file"]');
  const fileInputCount = await fileInput.count();
  console.log(`  File inputs found: ${fileInputCount}`);

  // Check the button to trigger file dialog
  const fileBtn = page.locator('button', { hasText: '動画ファイルを選択' });
  const fileBtnCount = await fileBtn.count();
  console.log(`  File select button found: ${fileBtnCount > 0}`);

  if (fileInputCount > 0) {
    await fileInput.setInputFiles(videoPath);
    console.log('  File set on input');

    // Wait for upload
    await sleep(3000);

    // Check if checkmark appeared
    const checkmark = page.locator('svg path[d="M20 6L9 17l-5-5"]');
    const checkVisible = (await checkmark.count()) > 0;
    console.log(`  Upload checkmark visible: ${checkVisible}`);

    // Check if button label changed
    const fileBtnAfter = page.locator('button', { hasText: '動画ファイルを選択' });
    const fileBtnAfterCount = await fileBtnAfter.count();
    console.log(`  "動画ファイルを選択" still shows: ${fileBtnAfterCount > 0}`);

    // Check button text (should show filename now)
    const allButtons = await page.locator('button').allTextContents();
    const hasFilename = allButtons.some(t => t.includes('test_clip') || t.includes('test_pitch'));
    console.log(`  Button shows filename: ${hasFilename}`);

    // Check execute button state
    const execDisabledAfter = await execBtn.getAttribute('disabled');
    console.log(`  Execute button disabled after upload: ${execDisabledAfter !== null}`);

    if (execDisabledAfter !== null) {
      console.log('  ❌ PROBLEM: Execute button is still disabled after prompt + video upload');

      // Debug: screenshot
      await page.screenshot({ path: '/tmp/integration-debug.png', fullPage: true });
      console.log('  Screenshot saved to /tmp/integration-debug.png');

      // Debug: check page state
      const pageContent = await page.content();
      const hasError = pageContent.includes('error') || pageContent.includes('Error');
      console.log(`  Page has error text: ${hasError}`);

      // Check console errors
      page.on('console', msg => console.log(`  Browser console: ${msg.type()} ${msg.text()}`));

      // Check video_id state by looking for checkmark
      console.log(`  Checkmark SVGs on page: ${await checkmark.count()}`);
    } else {
      console.log('  ✅ Execute button is now ENABLED!');
    }
  }

  console.log('\n=== Test Summary ===');
  console.log(`  Total assertions passed: ${passCount}/${totalCount}`);

  await browser.close();

  if (passCount < totalCount) {
    process.exit(1);
  }
}

let passCount = 0;
let totalCount = 0;

function assert(condition, message) {
  totalCount++;
  if (condition) {
    passCount++;
    console.log(`  ✅ ${message}`);
  } else {
    console.log(`  ❌ FAIL: ${message}`);
  }
}

main().catch(e => {
  console.error('Test error:', e);
  process.exit(1);
});
