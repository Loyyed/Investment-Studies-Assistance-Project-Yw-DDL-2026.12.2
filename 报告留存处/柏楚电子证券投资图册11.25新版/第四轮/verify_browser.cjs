const fs=require('node:fs/promises'),path=require('node:path'),{createRequire}=require('node:module'),{pathToFileURL,fileURLToPath}=require('node:url');
const req=createRequire('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/runtime.cjs');
const {chromium}=req('playwright'),{calculate}=require('./calculator.js');
(async()=>{
 const here=__dirname,stage=path.dirname(here),M=JSON.parse(await fs.readFile(path.join(here,'模型.json'),'utf8')),samples=JSON.parse(await fs.readFile(path.join(here,'交互比对样本.json'),'utf8'));
 const comparison=[];
 for(const x of samples){const r=calculate(M,x.name,x.wacc,x.g,x.margin,x.days,x.cap);
  const delta=Math.abs(r.price-x.price);if(delta>1e-9||Math.abs(r.years[0].fcff-x.fcff)>1e-8)throw Error('Python/JS mismatch');
  comparison.push({name:x.name,delta});
 }
 const browser=await chromium.launch({executablePath:'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1097/chrome-win/chrome.exe',headless:true});
 const ctx=await browser.newContext();await ctx.setOffline(true);const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const results=[];
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:950});await page.goto(pathToFileURL(path.join(stage,'index.html')).href);
  const r=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,images:[...document.images].filter(i=>i.complete&&i.naturalWidth).length,chapters:document.querySelectorAll('section[id^="ch"]').length}));
  if(r.documentWidth!==width||r.images!==14||r.chapters!==11)throw Error(JSON.stringify(r));
  await page.locator('#case').selectOption('压力');if(!(await page.locator('#calcResult').textContent()).includes('38.81'))throw Error('stress');
  await page.locator('#reset').click();if(!(await page.locator('#calcResult').textContent()).includes('85.09'))throw Error('reset');
  await page.locator('#days').fill('30');if(!(await page.locator('#calcResult').textContent()).includes('84.07'))throw Error('days');
  await page.locator('#reset').click();await page.locator('#calcResult').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(here,'验收-'+width+'.png')});
  results.push(r);
 }
 const links=await page.locator('a[href]').evaluateAll(a=>a.map(x=>x.href));let count=0;
 for(const h of links){if(h.startsWith('file:')){let u=new URL(h);u.hash='';await fs.stat(fileURLToPath(u));count++}}
 await page.locator('button[data-select="cash2022"]').click();await page.locator('button[data-select="structure2024"]').click();
 if(!await page.locator('figure[data-chart="cash2022"]').isVisible())throw Error('history switch');
 if(errors.length)throw Error(errors.join('\n'));
 await browser.close();
 const data={browser:'Chromium121',offline:true,widths:results,links:count,pythonJS:comparison,controls:'情景、回款参数与恢复基准通过',errors};
 await fs.writeFile(path.join(here,'浏览器验收.json'),JSON.stringify(data,null,2));console.log(JSON.stringify(data));
})().catch(e=>{console.error(e);process.exit(1)});
