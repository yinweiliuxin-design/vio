const fs=require('node:fs');const path=require('node:path');const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const errors=[],runs=[];
 for(const [label,width,height] of [['desktop',1440,1050],['mobile',390,844]]){
  const p=await browser.newPage({viewport:{width,height},deviceScaleFactor:1});p.on('pageerror',e=>errors.push(String(e)));
  await p.goto(pathToFileURL(path.join(root,'index.html')).href);await p.waitForLoadState('load');
  const result=await p.evaluate(()=>({title:document.title,overflow:document.documentElement.scrollWidth>innerWidth,
   missingImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.src),
   links:[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')),imageCount:document.images.length}));
  result.label=label;result.viewport={width,height};
  if(result.overflow||result.missingImages.length)throw new Error(JSON.stringify(result));
  await p.screenshot({path:path.join(root,'review',`index-${label}.png`),fullPage:true});
  runs.push(result);await p.close();
 }
 await browser.close();if(errors.length)throw new Error(errors.join('\n'));
 fs.writeFileSync(path.join(root,'review','index-layout-qa.json'),JSON.stringify({pass:true,runs,pageErrors:errors,scope:'Delivery navigation only; not hardware/browser audio test'},null,2));
 console.log(JSON.stringify({pass:true,viewports:runs.map(x=>x.viewport),links:runs[0].links.length,images:runs[0].imageCount}));
})().catch(e=>{console.error(e);process.exitCode=1});
