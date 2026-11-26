import pymupdf,json
from pathlib import Path
p=Path(r'D:/投资学/.bochu1126-member1-check')
for fn in ['嘉泰激光_招股说明书申报稿_2026-06-22.pdf','嘉泰激光_审核问询函回复_2025-08-05.pdf']:
 d=pymupdf.open(p/'公开补证原件'/fn)
 for i,page in enumerate(d):
  t=page.get_text(sort=True)
  if any(x in t for x in ['技术交流','80000','80kW','80KW','80KW','多家供应','多供']):
   print(fn,i+1,t[:6000])
