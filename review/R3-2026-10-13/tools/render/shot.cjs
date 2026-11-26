const { chromium } = require('playwright-core');
(async()=>{
  const jobs = JSON.parse(process.argv[2]);
  const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  for (const j of jobs) {
    const t0=Date.now();
    const p=await b.newPage({viewport:{width:j.w||1600,height:j.h||1000},deviceScaleFactor:j.dsf||2});
    p.on('console',m=>{ if(m.type()==='error'||m.type()==='warning') console.log('console:',m.text().slice(0,300)); });
    p.on('pageerror',e=>console.log('pageerror:',e.message));
    await p.goto('http://localhost:8765/'+j.url); await p.waitForFunction(()=>window.DONE!==undefined,{timeout:900000});
    await p.screenshot({path:j.out}); await p.close();
    console.log('ok',j.out,((Date.now()-t0)/1000).toFixed(1)+'s');
  }
  await b.close();
})();
