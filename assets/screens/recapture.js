// Regenerate the cockpit screenshots in this folder — see RECAPTURE.md.
//
//   node assets/screens/recapture.js        # captures 2x PNGs into /tmp/crux-shots
//
// Drives the *installed* Chrome via puppeteer-core (no bundled browser download):
//   npm i -g puppeteer-core           # or: npm i puppeteer-core in a scratch dir
// Point CRUX_URL at a running `crux serve` over the vault you want to shoot
// (default http://localhost:8896 — the segssl_vault example makes good material).
// Then convert the PNGs to .webp (RECAPTURE.md has the one-liner).

const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME = process.env.CHROME_BIN ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const URL = process.env.CRUX_URL || 'http://localhost:8896';
const OUT = process.env.OUT || '/tmp/crux-shots';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Which node to select for each tree shot (ids from the vault's META.md).
// h1 = a clean "supported" hypothesis (rich ledger); q2 = a resolved question (roll-up).
const SHOTS = [
  { name: 'cockpit-tree-dark',      theme: 'dark',  tab: 'tree', node: 'h1' },
  { name: 'cockpit-tree-light',     theme: 'light', tab: 'tree', node: 'h1' },
  { name: 'wiki-graph-dark',        theme: 'dark',  tab: 'wiki' },
  { name: 'wiki-graph-light',       theme: 'light', tab: 'wiki' },
  { name: 'question-rollup-dark',   theme: 'dark',  tab: 'tree', node: 'q2' },
  { name: 'question-rollup-light',  theme: 'light', tab: 'tree', node: 'q2' },
];

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-color-profile=srgb'],
    defaultViewport: { width: 1360, height: 812, deviceScaleFactor: 2 },
  });
  const page = await browser.newPage();
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });
  await page.waitForSelector('#tree, #cockpit', { timeout: 15000 });
  await sleep(1200);

  for (const s of SHOTS) {
    await page.evaluate((t) => {
      document.documentElement.dataset.theme = t;
      try { localStorage.setItem('crux-theme', t); } catch (e) {}
      const hint = document.querySelector('#help .hint'); if (hint) hint.hidden = true;
    }, s.theme);
    await page.evaluate((tab) => {
      const b = document.querySelector(`#tabs [data-tab="${tab}"]`);
      if (b) b.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    }, s.tab);
    await sleep(300);
    if (s.tab === 'wiki') {
      await sleep(1900); // let the force graph settle
    } else if (s.node) {
      await page.evaluate((id) => {
        const g = document.querySelector(`g.node[data-id="${id}"]`);
        if (g) g.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      }, s.node);
      await sleep(700);
    }
    await sleep(250);
    const p = path.join(OUT, s.name + '.png');
    await page.screenshot({ path: p });
    console.log('saved', p);
  }
  await browser.close();
  console.log('DONE — now convert to .webp (see RECAPTURE.md)');
}
main().catch((e) => { console.error(e); process.exit(1); });
