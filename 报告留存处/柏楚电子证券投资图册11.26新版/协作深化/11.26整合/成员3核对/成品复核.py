from pathlib import Path
import json,re,hashlib
from bs4 import BeautifulSoup
import mistune
R=Path("D:/投资学/.publish-1126-1795705877581/integrate/报告留存处")
A=R/'柏楚电子证券投资图册11.26新版'
O=Path("D:/投资学/.bochu1126-member3-check")
md=(R/'柏楚电子证券投资分析报告11.26新版.md').read_text(encoding='utf-8')
html=(A/'index.html').read_text(encoding='utf-8')
soup=BeautifulSoup(html,'html.parser');msoup=BeautifulSoup(mistune.create_markdown(plugins=['table'])(md),'html.parser')
def norm(t):
 t=re.sub(r'\([^)]*逐条采用表\.md#[^)]*\)','',t)
 t=re.sub(r'\[E[^\]]*\]','',t)
 t=re.sub(r'〔[^〕]*〕','',t)
 t=re.sub(r'[\[\]\(\)]','',t)
 t=re.sub(r'M1-\d\d','',t)
 t=re.sub(r'E\d\d(?:[、–—-]E?\d\d)*','',t)
 return re.sub(r'[\s·]','',t)
htext=norm(soup.get_text())
paragraphs=[]
for p in msoup.find_all('p'):
 t=norm(p.get_text())
 if len(t)>=50:
  paragraphs.append(dict(length=len(t),start=p.get_text()[:100],matched=t in htext))
sourcechecks=[]
for n in ['01','02','07']:
 src=(A/'第三轮'/'chapters'/(n+'.md')).read_text(encoding='utf-8')
 sm=BeautifulSoup(mistune.create_markdown(plugins=['table'])(src),'html.parser')
 sec=soup.find(id='ch'+n)
 st=norm(sec.get_text()) if sec else ''
 srcpars=[]
 for p in sm.find_all('p'):
  t=norm(p.get_text())
  if len(t)>=50 and '{{' not in t:
   srcpars.append(dict(start=p.get_text()[:80],matched=t in st))
 sourcechecks.append(dict(chapter=n,paragraphs=len(srcpars),failed=[p for p in srcpars if not p['matched']]))
old=json.loads((O/'复核结果.json').read_text(encoding='utf-8'))
hashes=[]
for r in old['model_files']:
 p=A/'第四轮'/r['file'];h=hashlib.sha256(p.read_bytes()).hexdigest();hashes.append(dict(file=r['file'],sha256=h,baseline=r['sha256'],identical=h==r['sha256']))
tables=[]
for tb in msoup.find_all('table'):
 cells=[norm(c.get_text()) for c in tb.find_all(['th','td'])];tables.append(dict(first=cells[:4],cells=len(cells),missing=[t for t in cells if t and t not in htext]))
records=dict(tables=tables,date='2026-11-26',executor='Codex成员三成品复核Agent',model_files=hashes,body_paragraphs=len(paragraphs),paragraph_failures=[p for p in paragraphs if not p['matched']],chapter_source_checks=sourcechecks,snapshot_checks={})
for n in ['第三轮报告留存.md','第三轮图册留存.html']:
 text=(A/'第四轮'/n).read_text(encoding='utf-8');snap=BeautifulSoup(mistune.create_markdown(plugins=['table'])(text),'html.parser') if n.endswith('md') else BeautifulSoup(text,'html.parser')
 txt=norm(snap.get_text());newpars=[]
 for cn in ['01','02','07']:
  sec=soup.find(id='ch'+cn)
  for p in sec.find_all('p',recursive=False):
   t=norm(p.get_text())
   if len(t)>=50:newpars.append(dict(chapter=cn,start=p.get_text()[:100],matched=t in txt))
 records['snapshot_checks'][n]=dict(paragraphs=len(newpars),failed=[p for p in newpars if not p['matched']])
(O/'成品复核结果.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(model_identical=sum(r['identical'] for r in hashes),paragraphs=len(paragraphs),failed=records['paragraph_failures'],source=sourcechecks,snapshots=records['snapshot_checks']),ensure_ascii=False))
