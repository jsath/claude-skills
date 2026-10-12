// Screenshot a page at phone width (default 390px), optionally scrolled to some text.
// Setup once in this folder: npm install playwright-core   (uses your installed Chrome, headless)
// Usage: node shot.js <url> <out.png> [anchor-text] [width]
const { chromium } = require('playwright-core');
(async () => {
  const [url, out, anchor, widthArg] = process.argv.slice(2);
  if (!url || !out) {
    console.error('usage: node shot.js <url> <out.png> [anchor-text] [width]');
    process.exit(1);
  }
  const width = parseInt(widthArg || '390', 10);
  const b = await chromium.launch({ headless: true, channel: 'chrome' });
  const p = await b.newPage({ viewport: { width, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await p.goto(url, { waitUntil: 'networkidle' });
  const y = await p.evaluate((a) => {
    const el = a && [...document.querySelectorAll('body *')].find(e => e.children.length === 0 && e.textContent.trim() === a);
    return el ? el.getBoundingClientRect().top + window.scrollY - 120 : 0;
  }, anchor);
  await p.evaluate((y) => window.scrollTo(0, Math.max(0, y)), y);
  await p.screenshot({ path: out });
  const w = await p.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  console.log(JSON.stringify({ out, scrollWidth: w[0], innerWidth: w[1], overflow: w[0] > w[1] }));
  await b.close();
})();
