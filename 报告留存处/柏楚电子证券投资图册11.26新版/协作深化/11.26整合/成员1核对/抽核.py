import pymupdf,json,re
from pathlib import Path
p=Path(r'D:/投资学/.bochu1126-member1-check')
rows={}
for fn,pages in [('宏石激光_招股书注册稿_2023-10-12.pdf',[156,160,165]),('嘉泰激光_招股说明书申报稿_2026-06-22.pdf',[100,111])]:
 d=pymupdf.open(p/'公开补证原件'/fn)
 for n in pages:
  text=d[n-1].get_text(sort=True);(p/f'{fn[:-4]}_p{n}.txt').write_text(text,encoding='utf8');rows[f'{fn} p{n}']=text
print(json.dumps(rows,ensure_ascii=False))
