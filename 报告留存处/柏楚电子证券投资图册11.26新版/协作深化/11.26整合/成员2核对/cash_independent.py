import csv,json,sys,re,hashlib
from pathlib import Path
from decimal import Decimal as D
import pymupdf as fitz
B=Path("D:/投资学/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2-codex-collaboration-workbenches/报告留存处/柏楚电子证券投资图册11.25新版");O=Path("D:/投资学/.bochu1126-member2-check")
C=list(csv.DictReader((B/'第一轮/清洗底表.csv').open(encoding='utf-8-sig')));ix={r['单元ID']:r for r in C}
def raw(year,p,label):
 f=next((B/'第四轮/年报原件').glob(f'*_{year}年年度报告_*.pdf'));doc=fitz.open(f)
 for ti,t in enumerate(doc[p-1].find_tables().tables,1):
  for ri,row in enumerate(t.extract(),1):
   if re.sub(r'\s','',str(row[0]))==label:
    print(year,p,ti,ri,row)
    return [v for v in row[1:] if v and re.fullmatch(r'[0-9,.]+',re.sub(r'\s','',v))],ti,ri
 raise Exception((year,p,label))
checks=[]
for year,p,label,cid in [(2024,116,'经营活动产生的现金流量净额','A2024-P116-T1-R27-0373'),(2024,117,'购建固定资产、无形资产和其他长期资产支付的现金','A2024-P117-T1-R03-0387'),(2025,130,'经营活动产生的现金流量净额','A2025-P130-T1-R06-0373'),(2025,130,'购建固定资产、无形资产和其他长期资产支付的现金','A2025-P130-T1-R14-0387'),(2024,113,'三、营业利润（亏损以“－”号填列）','A2024-P113-T1-R10-0261'),(2025,126,'三、营业利润（亏损以“－”号填列）','A2025-P126-T1-R24-0261')]:
 vals,t,r=raw(year,p,label); val=D(vals[0].replace(',',''));assert val==D(ix[cid]['标准值']); checks.append({'year':year,'page':p,'table_index':t,'row':r,'label':label,'column':f'{year}年度','value':str(val),'cell':cid,'difference_to_reviewed_cell':'0','SHA256':ix[cid]['来源SHA256']})
cf24,cap24,cf25,cap25,op24,op25=[D(r['value']) for r in checks]
s24=cf24-cap24;s25=cf25-cap25
results={'现金余量2024':s24,'现金余量2025':s25,'余量增量':s25-s24,'CFO增量':cf25-cf24,'购建减少':cap24-cap25,'现金桥闭合差':s25-s24-(cf25-cf24)-(cap24-cap25),'营业利润增量':op25-op24}
for year in [2024,2025]:
 rev=next(r for r in C if r['报告年度']==str(year) and r['表名']=='营业收入和营业成本附注' and r['原行']=='主营业务' and r['原列']=='本期发生额·收入');cost=next(r for r in C if r['报告年度']==str(year) and r['表名']=='营业收入和营业成本附注' and r['原行']=='主营业务' and r['原列']=='本期发生额·成本')
 r=D(rev['标准值']);c=D(cost['标准值']);results[f'主营毛利{year}']=r-c;results[f'主营毛利率{year}']=100*(r-c)/r
 net=next(D(z['标准值']) for z in C if z['报告年度']==str(year) and z['表名']=='合并利润表' and z['原行'].startswith('五、净利润') and z['列角色']=='本期');results[f'现金转换率{year}']=100*(cf24 if year==2024 else cf25)/net
 results[f'主营收入原格{year}']=rev['单元ID'];results[f'主营成本原格{year}']=cost['单元ID']
results['主营毛利增量']=results['主营毛利2025']-results['主营毛利2024']
results['毛利率变动pp']=results['主营毛利率2025']-results['主营毛利率2024']
dis24=D('94384129.34');dis25=D('114106284.20');pay24=D('6944324.40');pay25=D('18281281.11');tot24=dis24+pay24;tot25=dis25+pay25
results.update({'预提折扣2024':dis24,'预提折扣2025':dis25,'货款2024':pay24,'货款2025':pay25,'合同负债2024':tot24,'合同负债2025':tot25,'折扣占余额pct':100*dis25/tot25,'折扣占增量pct':100*(dis25-dis24)/(tot25-tot24)})
res={'identity':'Codex成员二财务锚点核对Agent，非原成员二本人','date':'2026-11-26','human_confirmation':False,'source_cells':checks,'results':{k:str(v) for k,v in results.items()},'scope':'集团合并；人民币元；现金转换率CFO÷合并净利润；现金余量CFO−购建长期资产付现；非单客户毛利或FCFF'}
(O/'现金桥独立复算.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(res,ensure_ascii=False,indent=2))
