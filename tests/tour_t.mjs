import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
const D='./';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});p.on('pageerror',e=>console.log('ERR',e.message));
const reqs=[];p.on('response',r=>{if(r.url().includes('/dio/'))reqs.push(r.status()+' '+r.url().split('/').pop())});
await p.goto('http://localhost:8765/test.html#'+process.argv[2]);await p.waitForTimeout(8000);
await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));await p.waitForTimeout(22000);
console.log(reqs.join(' | '));
const bx=await p.locator('#dioStage canvas').boundingBox();
await p.screenshot({path:D+'t0.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
await p.click('#dioBar [data-a="tour"]');await p.waitForTimeout(3500);await p.screenshot({path:D+'t1.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
await p.click('.dio-tour [data-t="1"]');await p.waitForTimeout(3500);await p.screenshot({path:D+'t2.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
for(let i=0;i<3;i++){await p.click('.dio-tour [data-t="1"]');await p.waitForTimeout(2000)}
await p.waitForTimeout(1500);await p.screenshot({path:D+'t3.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
await b.close();
