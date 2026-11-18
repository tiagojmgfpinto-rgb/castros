import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Captures of a site model from given viewpoints (to compare with real photographs taken from the same place).
// Use: VIEWS='name:x,y,z,tx,ty,tz[,fov];…' node tests/dio_views.mjs <out dir> <id> [A|B]   (viewer coordinates: x east, y up from h0, z south;
// CDN=<npm folder> when the CDNs are blocked; W×H with VW/VH, default 1200×800).
import fs from 'fs';
const D=(process.argv[2]||'.')+'/',id=process.argv[3],mode=process.argv[4]||'A',BASE=process.env.BASE||'http://localhost:8765/';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const ctx=await b.newContext({viewport:{width:Number(process.env.VW||1200),height:Number(process.env.VH||800)},reducedMotion:'reduce'});
const p=await ctx.newPage();p.setDefaultTimeout(180000);p.on('pageerror',e=>console.log('ERR',e.message));
if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
  await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const u=r.request().url();const f=u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?(fs.existsSync(M+'three160')?M+'three160':M+'three')+'/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
await p.goto(BASE+'test.html#'+id);await p.waitForSelector('#dio');await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));
await p.waitForSelector('#dioStage canvas');await p.waitForTimeout(6000);
await p.evaluate(()=>{const s=document.querySelector('#dioStage');s.scrollIntoView({block:'start'});document.querySelectorAll('.dio-l').forEach(e=>e.style.display='none')});
if(mode!=='A'){await p.locator(`#dioBar [data-v="${mode}"]`).click();await p.waitForTimeout(1500)}
const bx=await p.locator('#dioStage canvas').boundingBox(),clip={x:bx.x,y:bx.y,width:bx.width,height:bx.height};
for(const v of (process.env.VIEWS||'').split(';').filter(Boolean)){const [n,s]=v.split(':');const a=s.split(',').map(Number);
  await p.evaluate(([a])=>{__dio.cur.setCam(a.slice(0,6),a[6]);document.querySelectorAll('.dio-l').forEach(e=>e.style.visibility='hidden')},[a]);await p.waitForTimeout(2500);
  await p.screenshot({path:`${D}${id}-view-${n}-${mode}.png`,clip});console.log(n,await p.evaluate(()=>__dio.cur.camPos()))}
await b.close();
