import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
const D='./';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/test.html');await p.waitForTimeout(16000);
await p.screenshot({path:D+'z0.png'});
// fly to Briteiros at close distance
await p.evaluate(()=>{const s=D_s=null;});
await p.evaluate(()=>{const o=MQ.marks.find(m=>m.s.id==='guimaraes-citania-de-briteiros');MQ.anim=null;Object.assign(MQ.v,{tx:o.X,tz:o.Z,dist:55,tilt:.62,az:.3});MQ.g={...MQ.v};MQ.lastSz=0;MQ.needs=true});
await p.waitForTimeout(3000);await p.screenshot({path:D+'z1.png'});
await p.evaluate(()=>{const o=MQ.marks.find(m=>m.s.kind==='balneario');const m2=MQ.marks.find(m=>m.s.kind==='museu'&&Math.hypot(m.X-o.X,m.Z-o.Z)<60)||MQ.marks.find(m=>m.s.kind==='museu');Object.assign(MQ.v,{tx:o.X,tz:o.Z,dist:30,tilt:.5,az:0});MQ.g={...MQ.v};MQ.lastSz=0;MQ.needs=true;window._m=[o.s.name,m2.s.name]});
await p.waitForTimeout(3000);await p.screenshot({path:D+'z2.png'});
await p.evaluate(()=>{const o=MQ.marks.find(m=>m.s.kind==='museu'&&m.s.municipio==='Guimarães')||MQ.marks.find(m=>m.s.kind==='museu');Object.assign(MQ.v,{tx:o.X,tz:o.Z,dist:30,tilt:.5,az:0});MQ.g={...MQ.v};MQ.lastSz=0;MQ.needs=true});
await p.waitForTimeout(3000);await p.screenshot({path:D+'z3.png'});
// wheel zoom smoothness: zoom in at a point
await p.evaluate(()=>{document.querySelector("#bHome").click()});await p.waitForTimeout(1500);await p.waitForTimeout(500);
for(let i=0;i<6;i++){await p.mouse.move(640,450);await p.mouse.wheel(0,-100);await p.waitForTimeout(60)}
await p.waitForTimeout(1500);await p.screenshot({path:D+'z4.png'});
await b.close();
