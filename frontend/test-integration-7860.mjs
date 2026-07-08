/**
 * Playwright E2Eテスト: port 7860（ビルド版）でIntegration UIが動くか確認
 * GLBアップロードモード + 動画アップロードのテスト
 */
import { chromium } from 'playwright';
import { writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const BASE_URL = 'http://localhost:7860';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

let pass = 0, total = 0;
function assert(cond, msg) {
  total++;
  if (cond) { pass++; console.log(`  ✅ ${msg}`); }
  else { console.log(`  ❌ FAIL: ${msg}`); }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Collect console errors
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  console.log(`=== Testing on ${BASE_URL} ===`);

  console.log('\n--- Page Load ---');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  const title = await page.textContent('h1');
  assert(title?.includes('MOTION LAB'), 'Page loads with title');

  console.log('\n--- Integrate Button ---');
  const intBtn = page.locator('button', { hasText: 'Integrate' });
  assert((await intBtn.count()) > 0, 'Integrate button exists');

  // Wait a bit for health check
  await sleep(2000);

  const disabled = await intBtn.getAttribute('disabled');
  console.log(`  disabled attr: ${disabled}`);
  assert(disabled === null, 'Integrate button is ENABLED');

  if (disabled !== null) {
    console.log('\n  Debugging: checking /api/integration/health from page context...');
    const healthResult = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/integration/health');
        return { status: res.status, ok: res.ok, body: await res.text() };
      } catch (e) {
        return { error: e.message };
      }
    });
    console.log(`  Health check from browser: ${JSON.stringify(healthResult)}`);
    await page.screenshot({ path: '/tmp/debug-7860.png', fullPage: true });
    console.log('  Screenshot: /tmp/debug-7860.png');
    await browser.close();
    process.exit(1);
  }

  console.log('\n--- Switch to Integration mode ---');
  await intBtn.click();
  await sleep(500);
  assert((await page.locator('text=CREATE MODEL').count()) > 0, 'Integration UI visible');

  console.log('\n--- Model input mode toggle ---');
  // Default should be GLB mode
  const glbModeBtn = page.locator('button', { hasText: 'GLBアップロード' });
  const promptModeBtn = page.locator('button', { hasText: 'テキスト生成' });
  assert((await glbModeBtn.count()) > 0, 'GLB mode button exists');
  assert((await promptModeBtn.count()) > 0, 'Prompt mode button exists');

  // GLB upload UI should be visible by default
  const glbLabel = page.locator('text=3Dモデルファイル');
  assert((await glbLabel.count()) > 0, 'GLB file label visible in default mode');

  console.log('\n--- GLB upload + video upload ---');
  // Create a minimal dummy GLB file for testing
  const dummyGlbPath = join(tmpdir(), 'test_model.glb');
  // glTF binary magic: 0x46546C67 + version 2 + minimal content
  const glbHeader = Buffer.alloc(12);
  glbHeader.writeUInt32LE(0x46546C67, 0); // magic: glTF
  glbHeader.writeUInt32LE(2, 4);           // version 2
  glbHeader.writeUInt32LE(12, 8);          // total length
  writeFileSync(dummyGlbPath, glbHeader);

  // Upload GLB
  const glbFileInputs = page.locator('input[type="file"][accept=".glb,.gltf,.vrm"]');
  assert((await glbFileInputs.count()) > 0, 'GLB file input exists');
  await glbFileInputs.setInputFiles(dummyGlbPath);
  console.log('  Waiting for GLB upload...');
  await sleep(3000);

  const glbCheckmark = page.locator('svg path[d="M20 6L9 17l-5-5"]');
  assert((await glbCheckmark.count()) > 0, 'GLB upload checkmark visible');

  // Upload video
  const videoPath = '/home/ryu/projects/motion-data-2dto3d/data/input/test_clip.mp4';
  const videoFileInputs = page.locator('input[type="file"][accept="video/*"]');
  assert((await videoFileInputs.count()) > 0, 'Video file input exists');
  await videoFileInputs.setInputFiles(videoPath);
  console.log('  Waiting for video upload...');
  await sleep(5000);

  const allCheckmarks = page.locator('svg path[d="M20 6L9 17l-5-5"]');
  const checkmarkCount = await allCheckmarks.count();
  assert(checkmarkCount >= 2, `Both checkmarks visible (found ${checkmarkCount})`);

  const execBtn = page.locator('button', { hasText: '統合パイプラインを実行' });
  const execDisabled = await execBtn.getAttribute('disabled');
  assert(execDisabled === null, 'Execute button is ENABLED');

  console.log('\n--- Prompt mode switch ---');
  await promptModeBtn.click();
  await sleep(300);
  const textarea = page.locator('textarea');
  assert((await textarea.count()) > 0, 'Textarea visible after switching to prompt mode');

  console.log(`\n=== Results: ${pass}/${total} passed ===`);
  if (errors.length > 0) {
    console.log('\nBrowser console errors:');
    errors.forEach(e => console.log(`  ${e}`));
  }

  await browser.close();
  process.exit(pass === total ? 0 : 1);
}

main().catch(e => { console.error(e); process.exit(1); });
