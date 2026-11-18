import {chromium, devices} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Picking and state test of the viewer: taps on a grid until a structure record opens, then evidence colours and reconstitution mode.
// Use: node tests/dio_pick.mjs <out dir> [id]   (CDN=<npm folder> when the CDNs are blocked). Writes pick-*.png and prints what happened.
import fs from 'fs';
const D=(process.argv[2]||'.')+'/', id=process.argv[3]||'guimaraes-citania-de-briteiros';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const ctx=await b.newContext(process.env.VP==='desk'?{viewport:{width:1440,height:900},reducedMotion:'reduce'}:{...devices['iPhone 13'],deviceScaleFactor:1,reducedMotion:'reduce'});
const p=await ctx.newPage();p.setDefaultTimeout(180000);
if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
  const map=u=>u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?(fs.existsSync(M+'three160')?M+'three160':M+'three')+'/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;
  await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const f=map(r.request().url());return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
  if(process.env.NODRACO)await p.route(/draco_(decoder|wasm_wrapper)/,r=>r.abort());
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
const clip={x:bx.x,y:bx.y,width:bx.width,height:bx.height},V=async v=>{const b=p.locator(`#dioBar [data-v="${v}"]`);if(!await b.count())return false;await b.click();await p.waitForTimeout(1500);return true};
const leg=()=>p.evaluate(()=>{const l=document.querySelector('#dioLegend');return l.hidden?'(hidden)':l.textContent.trim().slice(0,90)});
// layers A–E
await V('B');console.log('B interpretação | legend:',await leg(),await stats());await p.screenshot({path:D+'pick-B.png',clip});
if(await V('C')){console.log('C reconstituição | legend:',await leg(),await stats());await p.locator('#dioLegend [data-x="evC"]').check();await p.waitForTimeout(1000);console.log('C + evidência | legend:',await leg(),await stats());await p.screenshot({path:D+'pick-C.png',clip})}
await V('D');console.log('D relevo | legend:',await leg(),'card hidden',await p.locator('.dio-card').isHidden(),await stats());await p.screenshot({path:D+'pick-D.png',clip});
await p.locator('#dioLegend [data-x="ex2"]').click();await p.waitForTimeout(1500);console.log('D ×2',await stats());await p.screenshot({path:D+'pick-D2.png',clip});
await V('E');console.log('E sem seleção | legend:',await leg(),await stats());
name=null;for(let gy=.35;gy<=.75&&!name;gy+=.08)for(let gx=.3;gx<=.7;gx+=.08){await p.mouse.click(bx.x+bx.width*gx,bx.y+bx.height*gy);await p.waitForTimeout(250);if(await p.locator('.dio-card').isVisible()){name=await p.locator('.dio-card b').textContent();break}}
await p.waitForTimeout(1500);console.log('E isolada:',name,'| legend:',await leg(),await stats());
await p.evaluate(()=>document.querySelector('.dio-card .x')&&(document.querySelector('.dio-card').hidden=true));await p.screenshot({path:D+'pick-E.png',clip});
await V('A');console.log('A',await stats());
// label click flies the camera; north button turns the view
const cp=()=>p.evaluate(()=>{const c=__dio.cur;return c&&c.camPos?c.camPos():null});
const l0=p.locator('.dio-l').filter({visible:true}).first();if(await l0.count()){const t=await l0.textContent();const a=await cp();await l0.dispatchEvent('click');await p.waitForTimeout(1600);console.log('label',t,'camera',a,'->',await cp())}
await p.locator('.dio-n').dispatchEvent('click');await p.waitForTimeout(4000);console.log('north camera',await cp());await p.screenshot({path:D+'pick-N.png',clip});
await b.close();
