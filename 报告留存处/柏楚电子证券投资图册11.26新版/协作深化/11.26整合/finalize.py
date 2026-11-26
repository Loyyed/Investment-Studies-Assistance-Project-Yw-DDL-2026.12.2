from pathlib import Path
import re,json,hashlib,mistune
H=Path(__file__).resolve().parent;ST=H.parents[1];D4=ST/'第四轮';report=ST.parent/'柏楚电子证券投资分析报告11.26新版.md'
s=report.read_text(encoding='utf8')
s=re.sub(r'\](?=〔M1-)','] ',s)
s=re.sub(r'〔(M1-[^〕]+)〕',lambda m:' · '.join('['+i+'](柏楚电子证券投资图册11.26新版/协作深化/11.26整合/逐条采用表.md#'+i+')' for i in re.findall(r'M1-\d{2}',m[1])),s)
s+='\n\n'+(H/'依据与路线_报告源.md').read_text(encoding='utf8')
# Explicit linked table of contents covers all eleven chapters.
headings=re.findall(r'^## (.+)$',s,re.M)
toc='\n\n阅读目录：'+ ' · '.join('['+t+'](#'+t.replace('，','').replace('、','').replace('？','')+')' for t in headings if t not in ['依据与来源','11.26采用、依据与复算路线'])+'\n\n'
s=s.replace('署名 刘翔宇','署名 刘翔宇'+toc,1)
report.write_text(s,encoding='utf8')
p=ST/'index.html';t=p.read_text(encoding='utf8')
t=t.replace('href="第三轮/验收记录.md">审核与复算','href="协作深化/11.26整合/验收记录.md">11.26验收与复算')
t=t.replace('<a href="#m1-evidence">成员一18项与八文</a>','<a href="#m1-evidence">成员一18项与八文</a>')
t=t.replace('<p>11.26 新版 · 成员一成果完整整合</p>','<p>11.26 新版 · 成员一成果完整整合</p><p>从加工与采购，读到护城河怎样兑现为订单、利润和现金。版本2026-11-26；11.25四轮已审基线。估值仍为2025年末财务及288,729,927股的条件测算，年报2026-04-10可得；38.81／85.09／150.25元，基准WACC8.5%、g2%、新增ROIC20%均为假设。</p>')
t=t.replace('</header>','<p><a href="https://raw.githubusercontent.com/Loyyed/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2/main/%E6%8A%A5%E5%91%8A%E7%95%99%E5%AD%98%E5%A4%84/%E6%9F%8F%E6%A5%9A%E7%94%B5%E5%AD%90%E8%AF%81%E5%88%B8%E6%8A%95%E8%B5%84%E5%9B%BE%E5%86%8C11.26%E6%96%B0%E7%89%88/%E6%9F%8F%E6%A5%9A%E7%94%B5%E5%AD%90%E8%AF%81%E5%88%B8%E6%8A%95%E8%B5%84%E5%9B%BE%E5%86%8C11.26%E6%96%B0%E7%89%88_%E7%A6%BB%E7%BA%BF%E5%8C%85.zip">11.26离线包（GitHub下载）</a> · <a href="README.md">使用与重建</a> · <a href="https://github.com/Loyyed/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2/blob/main/报告留存处/柏楚电子证券投资分析报告11.25新版.md">11.25历史报告（仓库中）</a></p></header>',1)
# Sources lead to exact evidence instead of a generic source drawer.
for key,eid in [('process','M1-01'),('contract','M1-03'),('moat','M1-04'),('memberoriginal','M1-09'),('cashsurplus','E13')]:
 pattern=r'(<figure data-chart="'+key+r'">.*?<figcaption>.*?<a href=")#sources'
 t=re.sub(pattern,lambda m:m[1]+'#'+eid,t,flags=re.S)
# Readable original drawing stays scrollable on small screens; new diagrams stack vertically.
t=t.replace('</style>','picture .flowgraph{min-width:0!important} .chapter h2{margin-top:1.7em} @media(max-width:850px){picture .flowgraph{width:100%;height:auto}} </style>',1)
renderer=mistune.create_markdown(escape=False,plugins=['table'])
route=(H/'依据与路线_报告源.md').read_text(encoding='utf8').replace('](柏楚电子证券投资图册11.26新版/','](')
t=t.replace('</main>','<section class="chapter" id="methods-route">'+renderer(route)+'</section></main>',1)
p.write_text(t,encoding='utf8')
# Add stable anchors to actual adoption rows.
f=H/'逐条采用表.md';q=f.read_text(encoding='utf8')
q=re.sub(r'\| (M1-\d{2}) \|',lambda m:'| <a id="'+m[1]+'"></a>'+m[1]+' |',q);f.write_text(q,encoding='utf8')
# All 19 audited financial files must remain identical.
audit=json.loads((H/'成员3核对/复核结果.json').read_text(encoding='utf8'))
checks=[]
for r in audit['model_files']:
 got=hashlib.sha256((D4/r['file']).read_bytes()).hexdigest();assert got==r['sha256'],r['file'];checks.append(dict(file=r['file'],sha256=got,unchanged=True))
(H/'模型继承核验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
(H/'依据与路线.md').write_text((H/'依据与路线_报告源.md').read_text(encoding='utf8').replace('](柏楚电子证券投资图册11.26新版/','](../../'),encoding='utf8')
print('11.26 final sources and 19 frozen model files verified')
