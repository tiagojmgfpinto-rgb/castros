// Capas das maquetas (site/public/maquetas/<id>/capa.jpg): o visor do site, sem placas nem giro, vista inicial de sudoeste.
// Uso: node tests/capas.mjs [id …]   com o site compilado servido em BASE (por omissão http://localhost:8802/castros/)
import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const BASE = process.env.BASE || 'http://localhost:8802/castros/';
const ids = process.argv.slice(2).length ? process.argv.slice(2) : fs.readdirSync('site/public/maquetas');
const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
const ctx = await b.newContext({viewport: {width: 1280, height: 1000}, deviceScaleFactor: 1.8, reducedMotion: 'reduce'});
for (const id of ids) {
  const p = await ctx.newPage();
  await p.goto(`${BASE}castro/${id}/`);
  await p.waitForURL(/\/(castros|citanias|cividades|museus|sitios)\//);
  await p.locator('.maqueta').scrollIntoViewIfNeeded();
  await p.waitForFunction(() => window.__maqueta, null, {timeout: 180000});
  await p.evaluate(() => [...document.querySelectorAll('.maqueta-botoes button')].find((x) => x.textContent === 'Placas').click());
  await p.addStyleTag({content: '.maqueta-norte,.maqueta-escala,.maqueta-placas,.maqueta-selo{display:none!important}'});
  await p.waitForTimeout(6000);
  const bx = await p.locator('.maqueta-palco canvas').boundingBox();
  await p.screenshot({path: `site/public/maquetas/${id}/capa.jpg`, type: 'jpeg', quality: 86, clip: bx, timeout: 180000});
  console.log(id, Math.round(bx.width), Math.round(bx.height));
  await p.close();
}
await b.close();
