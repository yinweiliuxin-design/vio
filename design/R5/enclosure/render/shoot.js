// Render render.html in headless Chromium and save the canvas as PNG.
// Usage: node shoot.js <http base url> <query string> <out.png>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [base, query, out] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage();
  p.on('console', m => console.log('page:', m.text()));
  p.on('pageerror', e => console.log('pageerror:', e.message));
  await p.goto(`${base}/render.html?${query}`);
  await p.waitForFunction(() => window.DONE === true, null, { timeout: 600000 });
  const url = await p.evaluate(() => window.RESULT);
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  await b.close();
  console.log('saved', out);
})();
