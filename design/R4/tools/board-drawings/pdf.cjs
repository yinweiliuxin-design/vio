const { chromium } = require('/tmp/claude-0/-home-user-vio/3feb98dd-4d20-5b5c-81b5-59ee6194072c/scratchpad/render/node_modules/playwright-core');
(async () => {
  const [src, out] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell' });
  const p = await b.newPage();
  await p.goto('file://' + src, { waitUntil: 'networkidle' });
  await p.pdf({ path: out, format: 'A4', landscape: true, printBackground: true, preferCSSPageSize: true });
  await b.close(); console.log('ok');
})();
