from pathlib import Path
import re,json,csv,hashlib,html
import mistune,pymupdf
H=Path(__file__).resolve().parent;ST=H.parents[1]
report=(ST.parent/'柏楚电子证券投资分析报告11.26新版.md').read_text(encoding='utf8')
page=(ST/'index.html').read_text(encoding='utf8')
renderer=mistune.create_markdown(escape=False,plugins=['table'])
def plain(s):return re.sub(r'\s+','',html.unescape(re.sub(r'<[^>]*>','',s)))
def norm(s):
 s=re.sub(r'〔[^〕]+〕','',s);s=re.sub(r'\[E[^\]]+\]','',s)
 s=re.sub(r'(?<![A-Za-z])(?:E\d{2}|M1-\d{2})','',s)
 return plain(s).replace('·','')
ph=norm(page);pm=norm(renderer(report));out=[]
files=sorted((ST/'第三轮/chapters').glob('*.md'))+[ST/'第四轮'/('chapter'+str(n)+'.md') for n in [9,10,11]]
for f in files:
 for i,p in enumerate(f.read_text(encoding='utf8').split('\n\n'),1):
  if p.startswith(('#','|','{{','![')) or p.strip().startswith('*图') or len(p)<20:continue
  txt=norm(renderer(p));a=txt in pm;b=txt in ph
  out.append(dict(章节=f.name,段号=i,字符数=len(txt),Markdown=a,HTML=b,摘要=txt[:90]))
errors=[r for r in out if not r['Markdown'] or not r['HTML']]
with (H/'逐段一致性.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,out[0].keys());w.writeheader();w.writerows(out)
# Formal HTML links and exact physical page bounds, with paths relative to atlas root.
checked=[]
for href in re.findall(r'href="([^"]+\.pdf#page=\d+)"',page):
 from urllib.parse import unquote
 name,pg=unquote(href).split('#page=');p=ST/name
 d=pymupdf.open(p);assert 1<=int(pg)<=len(d),href
 checked.append(dict(path=name,page=int(pg),pages=len(d),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
# Every identifier has an actual destination; all ten original handoffs preserve bytes.
adopts=json.loads((H/'逐条采用表.json').read_text(encoding='utf8'));assert len(adopts)==18
assert len(json.loads((H/'八篇文章采用表.json').read_text(encoding='utf8')))==8
for a in adopts:assert a['编号'] in report and ('id="'+a['编号']+'"') in page,a['编号']
for x in json.loads((H/'起点.json').read_text(encoding='utf8'))['member1Files']:
 assert hashlib.sha256((ST/'协作深化/成员一'/x['name']).read_bytes()).hexdigest()==x['sha256']
result=dict(paragraphs=len(out),errors=errors,pdfPhysicalLinks=len(checked),claims=18,articles=8,originalMemberFiles=10)
(H/'内容与原页验收.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
(H/'PDF原页链接验收.json').write_text(json.dumps(checked,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False));assert not errors,'substantive paragraph mismatch'
