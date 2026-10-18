// 사용: PW=... node capture.mjs <video> <outDir> <start> <end> <url>
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW);
const [, , video, outDir, s0, s1, url] = process.argv;
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('console', m => { if (m.type() === 'error') console.log('PAGE', m.text()); });
await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => window.render && window.TL);
const total = await page.evaluate(v => window.TL[v].total, video);
const a = Number(s0 || 0), b = Math.min(Number(s1 || total), total);
const stage = page.locator('#stage');
const t0 = Date.now();
for (let f = a; f < b; f++) {
  await page.evaluate(([v, fr]) => window.render(v, fr), [video, f]);
  await stage.screenshot({ path: `${outDir}/${String(f).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 94 });
}
console.log(`CAPTURED ${video} ${a}-${b} in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
await browser.close();
