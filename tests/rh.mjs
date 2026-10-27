import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
const D='./';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/test.html#guimaraes-citania-de-briteiros');await p.waitForTimeout(8000);
await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));await p.waitForTimeout(22000);
const bx=await p.locator('#dioStage canvas').boundingBox();
const shots=JSON.parse(process.argv[2]);
for(const [n,tx,ty,tz,px,py,pz] of shots){
  await p.evaluate(([tx,ty,tz,px,py,pz])=>{const c=DIO.cur;c.ctl.target.set(tx,ty,tz);c.cam.position.set(px,py,pz);c.ctl.update()},[tx,ty,tz,px,py,pz]);
  await p.waitForTimeout(1500);await p.screenshot({path:D+n+'.png',clip:{x:bx.x,y:bx.y,width:bx.width,height:bx.height}});
}
await b.close();
