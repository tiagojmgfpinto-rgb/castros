import { chromium } from 'playwright';
const b = await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
const out=process.argv[2];
for (const [name,vp,scheme] of [['desk',{width:1400,height:860},'light'],['dark',{width:1400,height:860},'dark'],['phone',{width:400,height:820},'light']]) {
  const p = await b.newPage({viewport:vp,colorScheme:scheme});
  const errs=[]; p.on('console',m=>{if(m.type()==='error')errs.push(m.text())}); p.on('pageerror',e=>errs.push(e.message));
  await p.goto('http://localhost:8765/index.html'); await p.waitForTimeout(2500);
  await p.screenshot({path:`${out}/${name}-1.png`});
  if(name==='desk'){
    await p.click('.item >> nth=3'); await p.waitForTimeout(1500); await p.screenshot({path:`${out}/${name}-2.png`});
    await p.click('[data-tab=diary]'); await p.waitForTimeout(500); await p.click('#play'); await p.waitForTimeout(6000); await p.screenshot({path:`${out}/${name}-3.png`});
  }
  if(name==='phone'){ await p.click('.item >> nth=0'); await p.waitForTimeout(1500); await p.screenshot({path:`${out}/${name}-2.png`});}
  console.log(name,errs);
}
await b.close();
