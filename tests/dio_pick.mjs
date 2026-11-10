import {chromium, devices} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Picking and state test of the viewer: taps on a grid until a structure record opens, then evidence colours and reconstitution mode.
// Use: node tests/dio_pick.mjs <out dir> [id]   (CDN=<npm folder> when the CDNs are blocked). Writes pick-*.png and prints what happened.
import fs from 'fs';
const D=(process.argv[2]||'.')+'/', id=process.argv[3]||'guimaraes-citania-de-briteiros';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const ctx=await b.newContext({...devices['iPhone 13'],deviceScaleFactor:1,reducedMotion:'reduce'});
const p=await ctx.newPage();p.setDefaultTimeout(180000);
if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
  const map=u=>u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?(fs.existsSync(M+'three160')?M+'three160':M+'three')+'/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;
  await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const f=map(r.request().url());return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto((process.env.BASE||'http://localhost:8765/')+'test.html#'+id);
await p.waitForSelector('#dio');await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));
await p.waitForSelector('#dioStage canvas');await p.waitForTimeout(5000);
const bx=await p.locator('#dioStage canvas').boundingBox();
const stats=()=>p.evaluate(()=>__dio.cur.stats(1));
console.log('start',await stats());
let name=null;
outer:for(let gy=.35;gy<=.75;gy+=.08)for(let gx=.3;gx<=.7;gx+=.08){
  await p.mouse.click(bx.x+bx.width*gx,bx.y+bx.height*gy);await p.waitForTimeout(250);
  if(await p.locator('.dio-card').isVisible()){name=await p.locator('.dio-card b').textContent();console.log('picked at',gx.toFixed(2),gy.toFixed(2),'->',name);break outer}}
await p.waitForTimeout(1500);console.log('selected',await stats());
await p.screenshot({path:D+'pick-sel.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
await p.locator('#dioBar [data-a="ev"]').click();await p.waitForTimeout(1500);
console.log('evidence legend visible',await p.locator('#dioLegend').isVisible(),await stats());
await p.screenshot({path:D+'pick-ev.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
const B=p.locator('#dioBar [data-m="B"]');
if(await B.count()){await B.click();await p.waitForTimeout(1500);console.log('B',await stats());await p.screenshot({path:D+'pick-evB.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}})}
await p.locator('#dioBar [data-a="ev"]').click();await p.locator('.dio-card .x').click().catch(()=>{});await p.waitForTimeout(800);console.log('B plain',await stats());
await b.close();
