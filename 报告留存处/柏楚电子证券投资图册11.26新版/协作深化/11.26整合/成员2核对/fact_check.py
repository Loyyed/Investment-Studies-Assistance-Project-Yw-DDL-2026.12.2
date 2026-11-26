import csv,json,sys
from pathlib import Path
B=Path("D:/投资学/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2-codex-collaboration-workbenches/报告留存处/柏楚电子证券投资图册11.25新版");sys.path.insert(0,str(B/'第一轮'));from recalculate import fact_audit
cells=list(csv.DictReader((B/'第一轮/清洗底表.csv').open(encoding='utf-8-sig')))
for r in cells:
 for k in ['报告年度','数据年度','PDF物理页']:r[k]=int(r[k])
idx=list(csv.DictReader((B/'第一轮/年报索引.csv').open(encoding='utf-8-sig')))
facts,counts=fact_audit(cells,idx)
Path("D:/投资学/.bochu1126-member2-check/动态Fact核验.json").write_text(json.dumps({'actor':'Codex成员二财务核对Agent','human_confirmation':False,'date':'2026-11-26','counts':counts,'facts':facts},ensure_ascii=False,indent=2),encoding='utf8')
print(counts)
print(json.dumps([r for r in cells if r['报告年度'] in [2024,2025] and r['表名']=='营业收入和营业成本附注' and '主营业务' in r['原行']],ensure_ascii=False,indent=2))
