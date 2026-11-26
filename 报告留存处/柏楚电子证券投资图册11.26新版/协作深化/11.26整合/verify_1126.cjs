const fs=require('node:fs/promises'),path=require('node:path'),{pathToFileURL,fileURLToPath}=require('node:url'),{createRequire}=require('node:module');
const req=createRequire('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/runtime.cjs');
const {chromium}=req('playwright');
(async()=>{
const stage=path.resolve(process.argv[2]||path.join(__dirname,'../..')),out=process.argv[3]||__dirname;
const model=JSON.parse(await fs.readFile(path.join(stage,'第四轮/模型.json'),'utf8'));
const {calculate}=require(path.join(stage,'第四轮/calculator.js'));
const browser=await chromium.launch({executablePath:'C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1097/chrome-win/chrome.exe',headless:true});
const ctx=await browser.newContext();await ctx.setOffline(true);const p=await ctx.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
const widths=[];
for(const width of [1440,390,320]){
 await p.setViewportSize({width,height:1000});await p.goto(pathToFileURL(path.join(stage,'index.html')).href);
 await p.waitForFunction(()=>[...document.images].every(i=>i.complete&&i.naturalWidth));
 const s=await p.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,images:document.images.length,chapters:document.querySelectorAll('section[id^=ch]').length,moatNavigation:[...document.querySelectorAll('nav a')].some(a=>a.hash==='#ch07'&&a.textContent.includes('护城河')),responsive:[...document.querySelectorAll('picture img')].map(i=>i.currentSrc)}));
 if(s.width!==s.documentWidth||s.images!==17||s.chapters!==11||!s.moatNavigation)throw Error(JSON.stringify(s));
 if(width<850&&!s.responsive.every(x=>x.endsWith('-mobile.svg')))throw Error('mobile flow source');
 for(const name of ['压力','基准','改善']){await p.locator('#case').selectOption(name);const expect=calculate(model,name,model.cases[name].wacc,model.cases[name].g).price.toFixed(2);if(!(await p.locator('#calcResult').textContent()).includes(expect))throw Error('scenario '+name)}
 await p.locator('#reset').click();await p.locator('#days').fill('30');if(!(await p.locator('#calcResult').textContent()).includes('84.07'))throw Error('days');
 await p.locator('#reset').click();await p.locator('#margin').fill('-2');await p.locator('#cap').fill('2');const r=calculate(model,'基准',.085,.02,-.02,0,2);if(!(await p.locator('#calcResult').textContent()).includes(r.price.toFixed(2)))throw Error('combined control');
 await p.locator('#reset').click();await p.locator('#wacc').fill('1');await p.locator('#growth').fill('2');if(!(await p.locator('#calcResult').textContent()).includes('保持WACC'))throw Error('invalid parameter guard');await p.locator('#reset').click();
 await p.locator('button[data-select=structure2024]').click();await p.locator('button[data-select=cash2022]').click();if(!await p.locator('figure[data-chart=cash2022]').isVisible())throw Error('year switch');
 await p.locator('#query').evaluate(e=>e.closest('details').open=true);await p.locator('#query').fill('B09');const visible=await p.locator('#raw-data tbody tr:not([hidden])').count();if(!visible||visible>=435)throw Error('filter');
 await p.locator('#ch07').scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,'阅读-'+width+'.png')});await p.locator('[data-chart=moat]').screenshot({path:path.join(out,'护城河-'+width+'.png')});
 widths.push(s);
}
const links=await p.locator('a[href]').evaluateAll(a=>a.map(x=>({url:x.href,text:x.textContent})));let local=0;const broken=[];
for(const x of links){if(x.url.startsWith('file:')){let u=new URL(x.url),anchor=decodeURIComponent(u.hash.slice(1));u.hash='';try{await fs.stat(fileURLToPath(u));if(fileURLToPath(u)===path.join(stage,'index.html')&&anchor&&!await p.locator('[id="'+anchor+'"]').count())broken.push(x);local++}catch(e){broken.push(x)}}}
if(broken.length||errors.length)throw Error(JSON.stringify({broken,errors}));
await browser.close();const res={date:'2026-11-26',stage,browser:'Chromium121',offline:true,widths,images:17,localLinks:local,links:links.length,controls:'三情景、联合参数、无效折现保护、恢复、年份切换、筛选均通过',errors};await fs.writeFile(path.join(out,'浏览器验收.json'),JSON.stringify(res,null,2));console.log(JSON.stringify(res));
})().catch(e=>{console.error(e);process.exit(1)});
