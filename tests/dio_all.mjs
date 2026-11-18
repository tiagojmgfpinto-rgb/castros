import {chromium, devices} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Captures of every site diorama (current state + reconstitution where it exists), on desktop or phone.
// Use: node tests/dio_all.mjs <out dir> [desk|phone]   (CDN=<npm folder> when the CDNs are blocked)
// NODRACO=1 blocks the Draco decoder (app/draco/ and the CDN copy), to check the fallback to the plain model.
// Writes <id>-<vp>-A.png / -B.png and a times.json with the load time of each model (ms, from opening the record).
import fs from 'fs';
const D=(process.argv[2]||'.')+'/', VP=process.argv[3]||'desk';
const IDS=process.env.IDS?process.env.IDS.split(','):['guimaraes-citania-de-briteiros','guimaraes-castro-de-sabroso','guimaraes-castro-de-sao-miguel-o-anjo','braga-castro-de-santa-marta-das-corticas','braga-castro-maximo'];
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const ctx=await b.newContext(VP==='phone'?{...devices['iPhone 13'],deviceScaleFactor:1,reducedMotion:'reduce'}:{viewport:{width:1440,height:900},reducedMotion:'reduce'});
const times={};
for(const id of IDS){
  const p=await ctx.newPage();p.setDefaultTimeout(180000);
  if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
    const map=u=>u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?(fs.existsSync(M+'three160')?M+'three160':M+'three')+'/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;
    await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const f=map(r.request().url());return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
  if(process.env.NODRACO)await p.route(/draco_(decoder|wasm_wrapper)/,r=>r.abort());
  p.on('pageerror',e=>console.log(id,'ERR',e.message));
  p.on('console',m=>{if(m.type()==='error')console.log(id,'console',m.text().slice(0,200))});
  const t0=Date.now();
  await p.goto((process.env.BASE||'http://localhost:8765/')+'test.html#'+id);
  await p.waitForSelector('#dio',{timeout:60000});
  await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));
  await p.waitForSelector('#dioStage canvas',{timeout:120000});
  times[id]=Date.now()-t0;
  await p.waitForTimeout(6000);
  times[id+':fmt']=await p.evaluate(()=>document.querySelector('.dio-wrap')?.dataset.fmt);
  times[id+':stats']=await p.evaluate(()=>window.__dio&&__dio.cur&&__dio.cur.stats?__dio.cur.stats():null).catch(()=>null);
  const bx=await p.locator('#dioStage canvas').boundingBox();const clip={x:bx.x,y:bx.y,width:bx.width,height:bx.height};
  await p.screenshot({path:`${D}${id}-${VP}-A.png`,clip,timeout:120000});
  // close-up: 7 wheel steps towards the centre of the view
  for(let i=0;i<7;i++){await p.mouse.move(bx.x+bx.width*.5,bx.y+bx.height*.5);await p.mouse.wheel(0,-120);await p.waitForTimeout(150)}
  await p.waitForTimeout(3000);await p.screenshot({path:`${D}${id}-${VP}-Z.png`,clip});
  const B=p.locator('#dioBar [data-v="C"]');
  if(await B.count()){await B.click();await p.waitForTimeout(4000);await p.screenshot({path:`${D}${id}-${VP}-B.png`,clip})}
  await p.close();
}
fs.writeFileSync(`${D}times-${VP}.json`,JSON.stringify(times,null,1));
console.log(times);
await b.close();
