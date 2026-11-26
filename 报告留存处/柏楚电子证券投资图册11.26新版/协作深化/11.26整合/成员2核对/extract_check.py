from pathlib import Path
import csv,json,hashlib,sys
import pymupdf as fitz
B=Path("D:/投资学/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2-codex-collaboration-workbenches/报告留存处/柏楚电子证券投资图册11.25新版"); O=Path("D:/投资学/.bochu1126-member2-check")
cells=list(csv.DictReader((B/'第一轮/清洗底表.csv').open(encoding='utf-8-sig')))
selected=[r for r in cells if r['报告年度'] in ['2024','2025'] and r['列角色']=='本期' and (('合并现金流量表'==r['表名'] and ('经营活动产生的现金流量净额' in r['原行'] or '购建固定' in r['原行'])) or ('合并利润表'==r['表名'] and ('营业利润' in r['原行'] or '五、净利润' in r['原行'])))]
print(json.dumps(selected,ensure_ascii=False,indent=2))
(O/'财务原格选择.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf8')
bridges=list(csv.DictReader((B/'第二轮/经营桥明细.csv').open(encoding='utf-8-sig')))
print('BRIDGES',json.dumps([r for r in bridges if r.get('计算段') in ['B01','B02','B04','B09','B10']][:5],ensure_ascii=False))
(O/'经营桥已审锚点.json').write_text(json.dumps([r for r in bridges if r.get('计算段') in ['B01','B02','B04','B09','B10']],ensure_ascii=False,indent=2),encoding='utf8')
for year,pages in [(2024,[116,117]),(2025,[129,130,131,213])]:
 f=next((B/'第四轮/年报原件').glob(f'*_{year}年年度报告_*.pdf')); doc=fitz.open(f)
 texts=[]
 for p in pages:
  pg=doc[p-1]; texts.append(f'\n--- PDF物理页{p} ---\n'+pg.get_text()); pg.get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(O/f'{year}-p{p}.png')
 (O/f'{year}-原文.txt').write_text(''.join(texts),encoding='utf8')
 print('PDF',year,hashlib.sha256(f.read_bytes()).hexdigest(),''.join(texts))
