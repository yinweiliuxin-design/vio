const { chromium } = require('playwright-core');
(async()=>{
  const [url,out,w,h]=process.argv.slice(2);
  const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  const p=await b.newPage({viewport:{width:+w,height:+h},deviceScaleFactor:1});
  p.on('pageerror',e=>console.log('pageerror:',e.message)); p.on('console',m=>{if(m.type()==='error')console.log('console:',m.text().slice(0,200))});
  await p.goto('http://localhost:8765/'+url); await p.waitForFunction(()=>window.DONE!==undefined,{timeout:600000});
  await p.screenshot({path:out,omitBackground:true}); await b.close(); console.log('ok');
})();
