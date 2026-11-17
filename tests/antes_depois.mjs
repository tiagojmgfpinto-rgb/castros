// Capturas para o antes/depois do site: node tests/antes_depois.mjs <antes|depois> <saida> <desk|phone> [nome,...]
// BASE = endereço do site (por omissão http://localhost:8801/castros/). CDN=<pasta npm> quando as CDN estão bloqueadas.
import {chromium, devices} from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const [VER, OUT, VP='desk', SO] = process.argv.slice(2);
const BASE = process.env.BASE || 'http://localhost:8801/castros/';
fs.mkdirSync(OUT, {recursive: true});
const BRIT = 'guimaraes-citania-de-briteiros', POP = 'alijo-castro-do-populo';
const espera = ms => new Promise(r => setTimeout(r, ms));
const clicar = sel => async p => { await p.locator(sel).first().click(); await espera(1800); };
const SHOTS = {
  antes: [
    ['01-mapa', '', async p => { await espera(9000); await p.evaluate(() => { const n = document.querySelector('#novid'); if (n) n.hidden = true; }); }],
    ['02-indice', '', clicar('#bIdx')],
    ['03-distritos', '', clicar('#bDist')],
    ['04-novidades', '', async p => { await p.evaluate(() => window.novShow && window.novShow()); await espera(1500); }],
    ['05-fontes', '', clicar('#bSrc')],
    ['06-caderno', '', clicar('#bCad')],
    ['07-ficha-com-maqueta', '#' + BRIT, async p => { await espera(25000); }],
    ['08-ficha-sem-maqueta', '#' + POP, async p => { await espera(4000); }],
    ['09-catalogo', 'castros/', null, true],
    ['10-pagina-com-maqueta', 'castro/' + BRIT + '/', null, true],
    ['11-pagina-sem-maqueta', 'castro/' + POP + '/', null, true],
    ['12-proximas-adicoes', null],
    ['13-creditos', 'creditos/', null, true],
  ],
  depois: [
    ['01-mapa', '', async p => { await espera(12000); await p.evaluate(() => document.querySelector('#novidades .fechar')?.click()); await espera(800); }],
    ['02-indice', '', clicar('button[aria-controls="indice"]')],
    ['03-distritos', '', clicar('button[aria-controls="distritos"]')],
    ['04-novidades', '', clicar('button[aria-controls="novidades"]')],
    ['05-fontes', '', clicar('button[aria-controls="fontes"]')],
    ['06-caderno', null],
    ['07-ficha-com-maqueta', '#' + BRIT, async p => { await espera(30000); }],
    ['08-ficha-sem-maqueta', null],
    ['09-catalogo', 'castros/', null, true],
    ['10-pagina-com-maqueta', 'citanias/' + BRIT + '/', async p => { await p.locator('.maqueta').first().scrollIntoViewIfNeeded().catch(() => {}); await espera(25000); await p.evaluate(() => scrollTo(0, 0)); }, true],
    ['11-pagina-sem-maqueta', 'castros/' + POP + '/', null, true],
    ['12-proximas-adicoes', 'proximas-adicoes/', null, true],
    ['13-creditos', 'creditos/', null, true],
  ],
};
const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']});
const ctx = await b.newContext(VP === 'phone' ? {...devices['iPhone 13'], deviceScaleFactor: 2} : {viewport: {width: 1440, height: 900}, deviceScaleFactor: 1});
for (const [nome, url, acao, pagina] of SHOTS[VER]) {
  if (SO && !SO.split(',').includes(nome)) continue;
  if (url === null) { console.log(nome, 'sem equivalente'); continue; }
  const p = await ctx.newPage(); p.setDefaultTimeout(240000);
  if (process.env.CDN) {
    const M = process.env.CDN + '/node_modules/';
    const map = u => u.includes('leaflet/1.9.4/') ? M + (u.endsWith('.css') ? 'leaflet/dist/leaflet.css' : 'leaflet/dist/leaflet.js') : u.includes('three.js/0.160.0/') ? M + 'three160/build/three.min.js' : u.includes('topojson/3.0.2/') ? M + 'topojson/dist/topojson.min.js' : /three@0\.1\d\d\.\d\//.test(u) ? M + 'three/' + u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0] : null;
    await p.route(/cdnjs|jsdelivr|unpkg/, r => { const f = map(r.request().url()); return f && fs.existsSync(f) ? r.fulfill({path: f, contentType: f.endsWith('.css') ? 'text/css' : 'application/javascript', headers: {'access-control-allow-origin': '*'}}) : r.abort(); });
  }
  p.on('pageerror', e => console.log(nome, 'ERR', e.message.slice(0, 200)));
  await p.goto(BASE + url, {waitUntil: 'load'});
  await espera(pagina ? 2500 : 6000);
  if (acao) await acao(p);
  const ficheiro = `${OUT}/${nome}-${VP}.png`;
  if (pagina) {
    const h = await p.evaluate(() => document.documentElement.scrollHeight);
    const w = VP === 'phone' ? 390 : 1440;
    await p.screenshot({path: ficheiro, clip: {x: 0, y: 0, width: w, height: Math.min(h, VP === 'phone' ? 2600 : 2200)}, fullPage: true, timeout: 240000});
  } else await p.screenshot({path: ficheiro, timeout: 240000});
  console.log(nome, 'ok');
  await p.close();
}
await b.close();
