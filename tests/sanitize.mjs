import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
// Dados maliciosos na base de dados simulada: nada pode correr nem partir a página. Use: CDN=<pasta npm> node tests/sanitize.mjs
import fs from 'fs';
const B=process.env.BASE||'http://localhost:8765/', BR='guimaraes-citania-de-briteiros';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1440,height:900}});
const errs=[];p.on('pageerror',e=>errs.push(e.message));
if(process.env.CDN){const M=process.env.CDN+'/node_modules/';
  const map=u=>u.includes('leaflet/1.9.4/')?M+'leaflet/dist/leaflet.js':u.includes('three.js/0.160.0/')?M+'three160/build/three.min.js':u.includes('topojson/3.0.2/')?M+'topojson/dist/topojson.min.js':/three@0\.1\d\d\.\d\//.test(u)?M+'three/'+u.split(/three@0\.1\d\d\.\d\//)[1].split('?')[0]:null;
  await p.route(/cdnjs|jsdelivr|unpkg/,r=>{const f=map(r.request().url());return f&&fs.existsSync(f)?r.fulfill({path:f,contentType:'application/javascript',headers:{'access-control-allow-origin':'*'}}):r.abort()})}
const X='"><img src=x onerror="window.__pwned=1">';
const bad={
 [`comments/u_mau`]:{items:[{id:X,site:BR,text:'olá',ts:Date.now()},{id:'ok1',site:BR,text:{a:1},ts:Date.now()},{id:'ok2',site:BR,text:'comentário válido',ts:Date.now()-5e3},null,'lixo',{id:'ok3',site:'nao-existe',text:'x',ts:Date.now()}]},
 [`comments/${X}`]:{items:[{id:'z1',site:BR,text:'uid malicioso',ts:Date.now()}]},
 [`comments/u_lixo`]:{items:'nao-e-lista'},
 [`history/${BR}`]:{text:{}},
 [`extra/x-mau`]:{name:'Castro <b>mau</b>',coords:[41.5,-8.3],kind:'<script>',distrito:'Braga',municipio:'Braga',text:'texto',hist:'h',src:[{t:'fonte',u:'javascript:window.__pwned=2'},{t:'boa',u:'https://example.org/a'}],photos:['../../x',X]},
 [`extra/x-coords`]:{name:'Sem coords',coords:['41','x']},
 [`extra/${X}`]:{name:'id mau',coords:[41.5,-8.3]},
};
await p.route(/test\.html/,async r=>{const res=await r.fetch();let h=await res.text();
  h=h.replace('const store={','const store={...'+JSON.stringify(bad)+',');r.fulfill({response:res,body:h})});
await p.goto(B+'test.html#'+BR);await p.waitForTimeout(6000);
if(errs.length)console.log('erros iniciais:',errs);
// separador Comentários: só os dois comentários válidos (dono + u_mau/ok2)
await p.evaluate(()=>document.querySelector('[data-tab="comments"]').click());await p.waitForTimeout(1500);
const coms=await p.$$eval('#clist .citem p',l=>l.map(x=>x.textContent));
const attrs=await p.$$eval('#clist [data-del],#clist [data-hide]',l=>l.map(x=>x.dataset.del||x.dataset.hide));
// ficha do castro acrescentado: a fonte javascript: é descartada, a https fica
await p.goto(B+'test.html');await p.reload();await p.waitForTimeout(5000);
await p.evaluate(()=>document.querySelector('[data-tab="add"]').click());await p.waitForTimeout(800);
await p.evaluate(()=>document.querySelector('[data-xo="x-mau"]').click());await p.waitForTimeout(2000);
const links=await p.$$eval('a[href]',l=>l.map(x=>x.getAttribute('href')).filter(h=>/example|javascript/i.test(h)));
const nome=await p.evaluate(()=>document.body.innerText.includes('Castro <b>mau</b>'));
// comentário legítimo continua a funcionar (com caracteres de controlo retirados)
await p.goto(B+'test.html');await p.reload();await p.waitForTimeout(5000);
await p.evaluate(()=>document.querySelector('[data-tab="comments"]').click());await p.waitForTimeout(800);
await p.evaluate(()=>{const s=document.querySelector('#csite');s.value=s.options[1].value;const t=document.querySelector('#ctext');t.value='  Teste\u0000 legítimo  ';document.querySelector('#csend').click()});
await p.waitForTimeout(1500);
const coms2=await p.$$eval('#clist .citem p',l=>l.map(x=>x.textContent));
const pw=await p.evaluate(()=>window.__pwned||0);
console.log(JSON.stringify({pw,coms,attrs,links,nome,coms2,errs},null,1));
const fail=pw||errs.length||coms.length!==4||attrs.some(a=>/[<>"]/.test(a))||links.some(h=>/javascript/i.test(h))||!links.length||!nome||!coms2.includes('Teste legítimo');
console.log(fail?'FALHOU':'OK');await b.close();process.exit(fail?1:0);
