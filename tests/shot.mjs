import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const [w,h,name,hash,act]=process.argv.slice(2);
const p=await b.newPage({viewport:{width:+w,height:+h}});
const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
await p.goto('http://localhost:8765/test.html'+(hash||''));
await p.waitForTimeout(14000);
if(act) {await p.evaluate(act);await p.waitForTimeout(4000);}
await p.screenshot({path:name});console.log(errs.join('\n'));await b.close();
