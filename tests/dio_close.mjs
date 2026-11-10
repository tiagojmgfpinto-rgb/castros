import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Close-up captures of each site model: clicks the first visible 3D label (the camera flies to it) and shoots the canvas.
// Use: node tests/dio_close.mjs <out dir> [tag]   (CDN=<npm folder> when the CDNs are blocked; BASE= for another server; IDS=a,b to limit)
import fs from 'fs';
const D=(process.argv[2]||'.')+'/',TAG=process.argv[3]||'new',BASE=process.env.BASE||'http://localhost:8765/';
const IDS=process.env.IDS?process.env.IDS.split(','):['guimaraes-citania-de-briteiros','guimaraes-castro-de-sabroso','guimaraes-castro-de-sao-miguel-o-anjo','braga-castro-de-santa-marta-das-corticas','braga-castro-maximo'];
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const ctx=await b.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
for(const id of IDS){const p=await ctx.newPage();p.setDefaultTimeout(180000);p.on('pageerror',e=>console.log('ERR',e.message));
  if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
    await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const u=r.request().url();const f=u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?(fs.existsSync(M+'three160')?M+'three160':M+'three')+'/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
  await p.goto(BASE+'test.html#'+id);await p.waitForSelector('#dio');await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));
  await p.waitForSelector('#dioStage canvas');await p.waitForTimeout(6000);
  const bx=await p.locator('#dioStage canvas').boundingBox(),clip={x:bx.x,y:bx.y,width:bx.width,height:bx.height};
  const n=Number(process.env.LBL||0),l=p.locator('.dio-l').filter({visible:true}).nth(n);
  if(await l.count()){const t=await l.textContent();await l.dispatchEvent('click');await p.waitForTimeout(2500);console.log(id,'label',t)}
  await p.mouse.move(bx.x+bx.width/2,bx.y+bx.height/2);for(let i=0;i<Number(process.env.ZOOM||0);i++){await p.mouse.wheel(0,-240);await p.waitForTimeout(120)}await p.waitForTimeout(2500);
  console.log(id,await p.evaluate(()=>__dio.cur&&__dio.cur.stats?__dio.cur.stats(2):null));
  await p.screenshot({path:`${D}${id}-close-${TAG}.png`,clip});await p.close()}
await b.close();
