const fs=require('node:fs/promises');
const path=require('node:path');
const {createRequire}=require('node:module');
const requireRuntime=createRequire('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/runtime.cjs');
const {chromium}=requireRuntime('playwright');
const {pathToFileURL,fileURLToPath}=require('node:url');
(async()=>{
const here=__dirname, stage=path.dirname(here);
const browser=await chromium.launch({executablePath:'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1097/chrome-win/chrome.exe',headless:true});
const context=await browser.newContext();
await context.setOffline(true);
const page=await context.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const results=[];
for(const width of [1440,390,320]){
 await page.setViewportSize({width,height:950});
 await page.goto(pathToFileURL(path.join(stage,'index.html')).href);
 const result=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
  loadedImages:[...document.images].filter(i=>i.complete&&i.naturalWidth>0).length,
  chapters:document.querySelectorAll('section[id^="ch"]').length}));
 if(result.documentWidth!==width||result.loadedImages!==9||result.chapters!==8)throw Error(JSON.stringify(result));
 for(const key of ['structure2024','structure2025','cash2022','cash2025']){
  await page.locator('button[data-select="'+key+'"]').click();
  if(!await page.locator('figure[data-chart="'+key+'"]').isVisible())throw Error(key);
 }
 await page.locator('nav a[href="#ch06"]').click();
 if(!page.url().endsWith('#ch06'))throw Error('navigation');
 await page.waitForTimeout(250);
 await page.screenshot({path:path.join(here,'验收-'+width+'.png')});
 results.push(result);
}
await page.locator('a.citation').first().click();
if(!page.url().endsWith('#E01'))throw Error('citation');
const links=await page.locator('a[href]').evaluateAll(links=>links.map(a=>a.href));
let checked=0;
for(const url of links){
 if(url.startsWith('file:')){
  const clean=new URL(url);clean.hash='';
  await fs.stat(fileURLToPath(clean));
  checked++;
 }
}
const pdf=await page.locator('#E15 a').getAttribute('href');
if(!decodeURIComponent(pdf).includes('1225091045.pdf#page=213'))throw Error('physical page link');
await page.locator('details summary').click();
await page.locator('#query').fill('平面解决方案');
const shown=await page.locator('#raw-data tbody tr:visible').count();
if(!shown||shown>=435)throw Error('filter');
if(errors.length)throw Error(errors.join('\n'));
await browser.close();
const record={browser:'Chromium 121（本机已有运行时）',offline:true,results,checkedLinks:checked,yearSwitch:true,sourcePage213:true,dataFilter:shown,errors};
await fs.writeFile(path.join(here,'浏览器验收.json'),JSON.stringify(record,null,2)+'\n');
console.log(JSON.stringify(record));
})().catch(e=>{console.error(e);process.exit(1)});
