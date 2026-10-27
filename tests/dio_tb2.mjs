import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
const D='./';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/test.html#guimaraes-citania-de-briteiros');await p.waitForTimeout(8000);
await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));await p.waitForTimeout(20000);
const bx=await p.locator('#dioStage canvas').boundingBox();
// zoom towards the acropolis centre
for(let i=0;i<9;i++){await p.mouse.move(bx.x+bx.width*.42,bx.y+bx.height*.45);await p.mouse.wheel(0,-120);await p.waitForTimeout(200)}
await p.waitForTimeout(2500);await p.screenshot({path:D+'b1.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
await p.click('#dioBar [data-m="B"]');await p.waitForTimeout(2500);await p.screenshot({path:D+'b2.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
await b.close();
