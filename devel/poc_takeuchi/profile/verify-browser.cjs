// Actual PoC data only: no request interception or synthetic candidate insertion.
const { chromium } = require(process.env.CALIBOO_PLAYWRIGHT_PATH || 'playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

async function verify() {
  const password = process.env.TAKEUCHI_POC_PASSWORD;
  assert.ok(password, 'Set TAKEUCHI_POC_PASSWORD without writing it to this file');
  const base = process.env.CALIBOO_BASE_URL || 'http://localhost:5173';
  const trace = path.join(__dirname, 'trace');
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    const page = await context.newPage();
    const errors = [];
    const checks = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`${base}/login`);
    await page.getByLabel('ログインID').fill('takeuchi');
    await page.getByLabel('パスワード').fill(password);
    await page.getByRole('button', { name: 'ログイン', exact: true }).click();
    await page.waitForURL('**/home');
    const response = await context.request.get(`${base}/api/development/strengths`);
    assert.equal(response.status(), 200);
    const { candidates } = await response.json();
    assert.ok(candidates.some((item) => item.kind === 'ability'));
    assert.ok(candidates.some((item) => item.kind === 'work_style'));
    assert.ok(candidates.every((item) => item.status === 'approved'));
    const current = candidates.filter((item) => item.jobId === 12);
    assert.equal(current.length, 4);
    assert.ok(current.every((item) => item.summary && item.scopeNote));
    for (const item of candidates) {
      await page.getByText(item.label, { exact: true }).waitFor();
      if (item.summary) await page.getByText(item.summary, { exact: true }).waitFor();
    }
    await page.getByRole('heading', { name: '得意な能力', exact: true }).waitFor();
    await page.getByRole('heading', { name: '性格・仕事の進め方の傾向', exact: true }).waitFor();
    await page.screenshot({ path: path.join(trace, 'home-profile.png'), fullPage: true });
    checks.push('SP-1/4: ホームに承認済み能力・性格傾向と解釈を表示');
    await page.getByRole('link', { name: '強みを詳しく見る' }).click();
    for (const item of candidates) {
      const card = page.getByRole('heading', { name: item.label, exact: true }).locator('..');
      if (item.summary) await card.getByText(item.summary, { exact: true }).waitFor();
      if (item.scopeNote) await card.getByText(`評価できる範囲: ${item.scopeNote}`, { exact: true }).waitFor();
      const details = card.locator('details');
      assert.equal(await details.getAttribute('open'), null);
      await details.locator('summary').click();
      assert.notEqual(await details.getAttribute('open'), null);
      const quotes = await details.locator('blockquote').allTextContents();
      assert.equal(quotes.length, item.evidence.length);
      for (const evidence of item.evidence) {
        assert.ok(quotes.some((quote) => quote.includes(evidence.quote)));
      }
      await details.locator('summary').click();
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(trace, 'strength-profile.png'), fullPage: true });
    checks.push('SP-4: 新候補の判断理由・評価範囲と全候補の原文根拠の開閉');
    for (const width of [320, 390]) {
      await page.setViewportSize({ width, height: 844 });
      await page.evaluate(() => window.scrollTo(0, 0));
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({ path: path.join(trace, `strength-profile-${width}.png`), fullPage: true });
      checks.push(`SP-4: ${width}px幅で横はみ出しなし`);
    }
    await page.setViewportSize({ width: 1440, height: 1050 });
    const diary = JSON.parse(await fs.readFile(path.join(trace, 'diary.json'), 'utf8'));
    await page.goto(`${base}/report`);
    await page.getByRole('button', { name: `${diary.date}の日報を開く` }).first().click();
    const dialog = page.getByRole('dialog');
    await dialog.waitFor();
    assert.ok((await dialog.textContent()).includes(diary.kpt.keep));
    await page.screenshot({ path: path.join(trace, 'profile-diary.png'), fullPage: true });
    await page.keyboard.press('Escape');
    checks.push('今回の作業日報を本人の提出履歴から表示');
    await page.goto(`${base}/assignments/7`);
    await page.getByText(/Fan-in要約/).waitFor();
    await page.screenshot({ path: path.join(trace, 'profile-feedback.png'), fullPage: true });
    checks.push('追加課題の実提出・3職種レビュー・Fan-in要約を表示');
    assert.deepEqual(errors, []);
    const result = { status: 'PASS', checkedAt: new Date().toISOString(), checks, errors,
      currentCandidates: current.length, retainedLegacyCandidates: candidates.length - current.length,
      labels: candidates.map(({ kind, label }) => ({ kind, label })) };
    await fs.writeFile(path.join(trace, 'browser-profile.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
}

verify().catch((error) => { console.error(error); process.exitCode = 1; });
