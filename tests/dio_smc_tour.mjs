import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Castro de Santa Marta das Cortiças: one screenshot per step of the guided tour, current state then reconstitution (t<step><A|B>.png)
const D=(process.argv[2]||'.')+'/';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});
if(process.env.CDN){const fs=await import('fs');const M=process.env.CDN+'/node_modules/';
 const map=u=>u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?M+'three/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':u.includes('three@0.160.0/')?M+'three/'+u.split('three@0.160.0/')[1]:null;
 await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const f=map(r.request().url());return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/test.html#braga-castro-de-santa-marta-das-corticas');await p.waitForTimeout(8000);
await p.evaluate(()=>document.querySelector('#dio').scrollIntoView({block:'center'}));await p.waitForTimeout(25000);
await p.click('#dioBar [data-a="full"]');await p.waitForTimeout(3000);
await p.click('[data-a="tour"]');await p.waitForTimeout(4000);
for(let i=0;i<6;i++){await p.screenshot({path:D+`t${i}A.png`});
 await p.click('#dioBar [data-m="B"]');await p.waitForTimeout(1800);await p.screenshot({path:D+`t${i}B.png`});
 await p.click('#dioBar [data-m="A"]');await p.waitForTimeout(800);
 await p.click('.dio-tour [data-t="1"]');await p.waitForTimeout(4000)}
await b.close();
