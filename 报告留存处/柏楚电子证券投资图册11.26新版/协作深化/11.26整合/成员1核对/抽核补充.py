import pymupdf,json,re
from pathlib import Path
p=Path(r'D:/投资学/.bochu1126-member1-check')
rows={}
for fn,pages in [('宏石激光_深交所问询回复.pdf',[68,96,97,98]),('嘉泰激光_审核问询函回复_2025-08-05.pdf',[68]),('柏楚_FSCUT8000装机手册_V1.6.pdf',[5,6])]:
 d=pymupdf.open(p/'公开补证原件'/fn)
 for n in pages:
  text=d[n-1].get_text(sort=True);(p/f'{fn[:-4]}_p{n}.txt').write_text(text,encoding='utf8');rows[f'{fn} p{n}']=text
print(json.dumps(rows,ensure_ascii=False))
