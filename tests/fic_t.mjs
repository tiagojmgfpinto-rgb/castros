import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
const D='./';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const [w,h,id,name]=process.argv.slice(2);
const p=await b.newPage({viewport:{width:+w,height:+h}});
p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://localhost:8765/test.html#'+id);await p.waitForTimeout(9000);
const ids=await p.evaluate(()=>[...document.querySelectorAll('#snav button')].map(b=>b.dataset.go));console.log(ids.join(' '));
let i=0;for(const g of ['sec-hist','sec-sab','sec-cro','sec-src']){if(!ids.includes(g))continue;await p.click(`#snav [data-go="${g}"]`);await p.waitForTimeout(1500);await p.screenshot({path:D+name+(i++)+'.png',clip:+w>760?{x:+w-Math.round(Math.min(880,Math.max(460,+w*.46))),y:0,width:Math.round(Math.min(880,Math.max(460,+w*.46))),height:+h}:undefined})}
await b.close();
