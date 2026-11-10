import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Map and record checks: "Com maqueta 3D" filter, spider for overlapping markers, prefetch on hover, sections without data.
// Use: node tests/map_t.mjs <out dir>   (CDN=<npm folder> when the CDNs are blocked; BASE= for another server)
import fs from 'fs';
const D=(process.argv[2]||'.')+'/',BASE=process.env.BASE||'http://localhost:8765/';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await (await b.newContext({viewport:{width:1300,height:850}})).newPage();p.setDefaultTimeout(60000);
if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
  await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const u=r.request().url();const f=u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?(fs.existsSync(M+'three160')?M+'three160':M+'three')+'/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto(BASE+'test.html');await p.waitForSelector('.leaflet-marker-icon',{state:'attached'});await p.waitForTimeout(3000);
// filter
const openIdx=async()=>{if(!await p.locator('#tchips').isVisible().catch(()=>false)){await p.locator('#bIdx').click();await p.waitForTimeout(700)}};
await openIdx();
if(await p.locator('#tchips [data-dio]').count()){await p.locator('#tchips [data-dio]').click();await p.waitForTimeout(600);
  console.log('filter com maqueta 3D: list items',await p.locator('#list .item').count(),'| active note:',await p.locator('.filtro-ativo').textContent().catch(()=>null));
  await p.screenshot({path:D+'map-filter.png'});await p.locator('#tchips [data-dio]').click();await p.waitForTimeout(400);console.log('filter off: items',await p.locator('#list .item').count())}
else console.log('index panel not found');
// spider: find a marker with neighbours within 18 px at the current zoom
const pair=await p.evaluate(()=>{const ms=[...document.querySelectorAll('.leaflet-marker-pane .leaflet-marker-icon')].filter(e=>e.offsetParent!==null&&e.title).map(e=>{const r=e.getBoundingClientRect();return {e,x:r.left+r.width/2,y:r.top+r.height/2,t:e.title}});
  for(const a of ms){const n=ms.filter(b=>Math.hypot(a.x-b.x,a.y-b.y)<18);if(n.length>1)return {x:a.x,y:a.y,t:a.t,n:n.map(b=>b.t)}}return null});
console.log('overlapping markers',pair);
if(pair){await p.evaluate(t=>{const e=[...document.querySelectorAll('.leaflet-marker-icon')].find(e=>e.title===t);e.dispatchEvent(new MouseEvent('click',{bubbles:true}))},pair.t);await p.waitForTimeout(800);
  const names=await p.locator('.spi-b').allTextContents();console.log('spider buttons',names);await p.screenshot({path:D+'map-spider.png'});
  if(names.length){await p.locator('.spi-b').nth(1).dispatchEvent('click');await p.waitForTimeout(2500);console.log('opened',await p.evaluate(()=>location.hash),'| spider gone',!(await p.locator('.spi-b').count()))}}
// prefetch on hover
await p.goto(BASE+'test.html');await p.waitForSelector('.leaflet-marker-icon',{state:'attached'});await p.waitForTimeout(2500);
await p.evaluate(()=>{const e=[...document.querySelectorAll('.leaflet-marker-icon')].find(e=>e.title==='Castro de Sabroso');e&&e.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}))});await p.waitForTimeout(300);
console.log('prefetch links',await p.evaluate(()=>[...document.querySelectorAll('link[rel=prefetch]')].map(l=>l.getAttribute('href'))));
// sections without data
await p.goto('about:blank');await p.goto(BASE+'test.html#alijo-castro-do-populo');await p.waitForTimeout(4000);
console.log('sections',await p.evaluate(()=>[...document.querySelectorAll('section[id^=sec-]')].map(s=>s.id+(s.querySelector('.sem-dados')?'(sem dados)':'')).join(' ')));
await b.close();
