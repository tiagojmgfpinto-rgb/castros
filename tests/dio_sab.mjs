import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Castro de Sabroso diorama: overview, close-up, reconstitution (PNG files written to the folder given as argument)
const D=(process.argv[2]||'.')+'/';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});
// optional: serve the CDN libraries from a local npm folder (CDN=<dir with node_modules>) when the CDNs are not reachable
if(process.env.CDN){const fs=await import('fs');const M=process.env.CDN+'/node_modules/';
 const map=u=>u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?M+'three/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':u.includes('three@0.160.0/')?M+'three/'+u.split('three@0.160.0/')[1]:null;
 await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const f=map(r.request().url());return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/test.html#guimaraes-castro-de-sabroso');await p.waitForTimeout(8000);
await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));await p.waitForTimeout(25000);
const bx=await p.locator('#dioStage canvas').boundingBox();const clip={x:bx.x,y:bx.y,width:bx.width,height:bx.height};
await p.screenshot({path:D+'s0.png',clip});
for(let i=0;i<7;i++){await p.mouse.move(bx.x+bx.width*.45,bx.y+bx.height*.45);await p.mouse.wheel(0,-120);await p.waitForTimeout(200)}
await p.waitForTimeout(2500);await p.screenshot({path:D+'s1.png',clip});
await p.click('#dioBar [data-m="B"]');await p.waitForTimeout(2500);await p.screenshot({path:D+'s2.png',clip});
await b.close();
