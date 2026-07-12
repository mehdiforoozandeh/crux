// Regenerate the cockpit screenshots in this folder — see RECAPTURE.md.
//
//   node assets/screens/recapture.js        # captures 2x PNGs into /tmp/crux-shots
//
// Drives the *installed* Chrome via puppeteer-core (no bundled browser download):
//   npm i puppeteer-core              # in a scratch dir, or -g
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

// For a legible tree, collapse the deeper/later branches so the remaining nodes
// render large, and select one hypothesis to show its evidence ledger.
// Ids come from the vault's META.md — change them if you shoot a different vault.
const COLLAPSE = ['q3', 'q4', 'q5'];   // keep q1 + q2 expanded
const LEDGER_NODE = 'h1';              // a clean "supported" hypothesis

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-color-profile=srgb'],
    defaultViewport: { width: 1440, height: 940, deviceScaleFactor: 2 },
  });
  const page = await browser.newPage();
  // legend + controls-help hint off, so nothing overlaps the tree
  await page.evaluateOnNewDocument(() => {
    try {
      localStorage.setItem('crux-legend-hidden', '1');
      localStorage.setItem('crux-help-hidden', '1');
    } catch (e) {}
  });
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 30000 });
  await page.waitForSelector('#tree', { timeout: 15000 });
  await sleep(1200);

  const theme = (t) => page.evaluate((t) => { document.documentElement.dataset.theme = t; }, t);
  const click = (sel) => page.evaluate((s) => {
    const e = document.querySelector(s);
    if (e) e.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  }, sel);
  const toggle = async (ids) => { for (const id of ids) { await click(`[data-toggle="${id}"]`); await sleep(120); } };

  async function treeShot(name, t) {
    await click('#tabs [data-tab="tree"]'); await sleep(200);
    await theme(t);
    await toggle(COLLAPSE);                          // collapse deeper branches
    await click(`g.node[data-id="${LEDGER_NODE}"]`); await sleep(200);
    await click('#zoom-fit'); await sleep(500);      // fit the (smaller) tree large
    await page.screenshot({ path: path.join(OUT, name + '.png') });
    console.log('saved', name);
    await toggle(COLLAPSE);                           // re-expand for the next shot
  }
  async function wikiShot(name, t) {
    await theme(t);
    await click('#tabs [data-tab="wiki"]'); await sleep(1900); // let the force graph settle
    await page.screenshot({ path: path.join(OUT, name + '.png') });
    console.log('saved', name);
    await click('#tabs [data-tab="tree"]'); await sleep(200);
  }

  await treeShot('cockpit-tree-light', 'light');
  await treeShot('cockpit-tree-dark', 'dark');
  await wikiShot('wiki-graph-light', 'light');
  await wikiShot('wiki-graph-dark', 'dark');

  await browser.close();
  console.log('DONE — now convert to .webp (see RECAPTURE.md)');
}
main().catch((e) => { console.error(e); process.exit(1); });
