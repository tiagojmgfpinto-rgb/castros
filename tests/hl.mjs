import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
const D='./';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/test.html');await p.waitForTimeout(16000);
await p.mouse.move(600,440);await p.waitForTimeout(300);await p.mouse.move(603,441,{steps:3});await p.waitForTimeout(800);
const n1=await p.locator('.mhl').count(),k1=await p.evaluate(()=>[...document.querySelectorAll('.mhl')].map(x=>x.dataset.id).join());
await p.screenshot({path:D+'hl.png',clip:{x:380,y:240,width:560,height:400}});
// move the pointer onto the first tag: set must stay the same
const bb=await p.locator('.mhl').first().boundingBox();await p.mouse.move(bb.x+bb.width/2,bb.y+bb.height/2,{steps:12});await p.waitForTimeout(500);
const k2=await p.evaluate(()=>[...document.querySelectorAll('.mhl')].map(x=>x.dataset.id).join());console.log(n1,'stable:',k1===k2);
await p.mouse.click(bb.x+bb.width/2,bb.y+bb.height/2);await p.waitForTimeout(2500);console.log(await p.evaluate(()=>document.querySelector('h2.title')?.textContent));
await p.evaluate(()=>{const o=MQ.marks.find(m=>m.s.id==='guimaraes-citania-de-briteiros');Object.assign(MQ.v,{tx:o.X-8,tz:o.Z,dist:60,tilt:.6,az:.3});MQ.g={...MQ.v};MQ.lastSz=0;MQ.needs=true});
await p.waitForTimeout(3000);await p.screenshot({path:D+'z1.png'});
await b.close();
