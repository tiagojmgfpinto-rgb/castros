import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Castro de São Paio: the model seen from the viewpoints of the comparison photographs (lidar/spa/views.json, from
// lidar/spa_views.py) and from above (for the orthophoto). Use: node tests/dio_spa_views.mjs <out dir>  (CDN=<npm folder>)
import fs from 'fs';
const D=(process.argv[2]||'.')+'/', id='vila-do-conde-castro-de-sao-paio';
const V=JSON.parse(fs.readFileSync('lidar/spa/views.json'));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1200,height:900},reducedMotion:'reduce'});p.setDefaultTimeout(180000);
if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
  const map=u=>u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?(fs.existsSync(M+'three160')?M+'three160':M+'three')+'/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;
  await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const f=map(r.request().url());return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto((process.env.BASE||'http://localhost:8765/')+'test.html#'+id);
await p.waitForSelector('#dio',{timeout:60000});
await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));
await p.waitForSelector('#dioStage canvas',{timeout:120000});await p.waitForTimeout(6000);
const bx=await p.locator('#dioStage canvas').boundingBox();const clip={x:bx.x,y:bx.y,width:bx.width,height:bx.height};
const shot=async(n,c,t,f)=>{await p.evaluate(([c,t,f])=>__dio.cur.setCam([...c,...t],f),[c,t,f]);await p.waitForTimeout(3500);await p.screenshot({path:D+n+'.png',clip})};
await p.addStyleTag({content:'.dio-lbls{display:none!important}'});
for(const [k,v] of Object.entries(V)){await shot(k+'-A',v.cam,v.tgt,v.fov)}
await shot('top-A',[0,260,0.01],[0,0,0],40);
await p.click('#dioBar [data-v="C"]').catch(()=>p.click('#dioBar [data-m="B"]'));await p.waitForTimeout(3000);
for(const [k,v] of Object.entries(V)){await shot(k+'-B',v.cam,v.tgt,v.fov)}
await b.close();
