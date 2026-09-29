// Applies the authorized AI instructor's recorded decisions to actual PoC candidates.
const { chromium } = require(process.env.CALIBOO_PLAYWRIGHT_PATH || 'playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

async function approve() {
  const base = process.env.CALIBOO_BASE_URL || 'http://localhost:5173';
  const trace = path.join(__dirname, 'trace');
  const review = JSON.parse(await fs.readFile(path.join(trace, 'candidate_review.json'), 'utf8'));
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    const page = await context.newPage();
    const errors = [];
    const decisions = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`${base}/login`);
    await page.getByLabel('ログインID').fill('sensei');
    // Public local development seed, not a private instructor credential.
    await page.getByLabel('パスワード').fill('caliboo-sensei');
    await page.getByRole('button', { name: 'ログイン', exact: true }).click();
    await page.waitForURL('**/home');
    const response = await context.request.get(`${base}/api/development/strengths?userId=5`);
    assert.equal(response.status(), 200);
    const { candidates } = await response.json();
    const pending = candidates.filter((item) => item.jobId === 12 && item.status === 'pending');
    assert.ok(pending.length > 0);
    assert.equal(pending.length, review.decisions.length);
    await page.goto(`${base}/strengths`);
    await page.getByRole('combobox', { name: '対象者' }).click();
    await page.getByRole('option', { name: '竹内', exact: true }).click();
    for (const candidate of pending) {
      const decision = review.decisions.find((item) =>
        item.kind === candidate.kind && item.skillCode === candidate.skillCode);
      assert.ok(decision, `Missing review for candidate ${candidate.id}`);
      if (decision.decision !== 'approve') continue;
      const card = page.getByRole('heading', { name: candidate.label, exact: true }).locator('..');
      for (const [label, value] of [
        ['強みの表現', decision.label], ['強みの解釈', decision.summary],
        ['評価できる範囲', decision.scopeNote], ['次の取り組み', decision.growthAction],
      ]) {
        assert.ok(value);
        await card.getByLabel(label, { exact: true }).fill(value);
      }
      if (!decisions.length) {
        await card.screenshot({ path: path.join(trace, 'instructor-review.png') });
      }
      const saved = page.waitForResponse((item) =>
        item.url().endsWith(`/api/development/strengths/${candidate.id}/decision`)
        && item.request().method() === 'POST');
      await card.getByRole('button', { name: '承認して表示', exact: true }).click();
      const result = await saved;
      assert.equal(result.status(), 200);
      const body = await result.json();
      assert.equal(body.status, 'approved');
      for (const key of ['label', 'summary', 'scopeNote', 'growthAction']) {
        assert.equal(body[key], decision[key]);
      }
      decisions.push(body);
      // Persist after every successful decision so an interrupted run keeps its evidence.
      await fs.writeFile(path.join(trace, 'candidate_decisions.json'), JSON.stringify(decisions, null, 2) + '\n');
      await page.getByRole('heading', { name: decision.label, exact: true }).waitFor();
    }
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ approved: decisions.length, held: review.decisions.filter((item) => item.decision !== 'approve').length, errors }));
  } finally {
    await browser.close();
  }
}

approve().catch((error) => { console.error(error); process.exitCode = 1; });
