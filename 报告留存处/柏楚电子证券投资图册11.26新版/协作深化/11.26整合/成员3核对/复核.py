from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from decimal import Decimal as D,getcontext
import json,csv,pymupdf
getcontext().prec=45
B=Path("D:/投资学/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2-codex-collaboration-workbenches/报告留存处/柏楚电子证券投资图册11.25新版/第四轮")
O=Path("D:/投资学/.bochu1126-member3-check")
m=json.loads((B/'模型.json').read_text(encoding='utf-8'))
names=[p.name for p in B.iterdir() if p.suffix=='.csv' or p.name in ['model.py','calculator.js','模型.json']]
fingerprints=[]
with ZipFile(B/'审核时离线包_ac71f8ae.zip') as z:
 for n in sorted(names):
  matches=[x for x in z.namelist() if x.endswith('/第四轮/'+n)]
  assert len(matches)==1,(n,matches)
  old=z.read(matches[0]);now=(B/n).read_bytes()
  fingerprints.append(dict(file=n,sha256=sha256(now).hexdigest(),audit_sha256=sha256(old).hexdigest(),identical=old==now))
assert len(fingerprints)==19 and all(x['identical'] for x in fingerprints)
pins=[]
for n,h in json.loads((B/'输入指纹.json').read_text(encoding='utf-8')).items():
 actual=sha256((B/n).read_bytes()).hexdigest();assert actual==h;pins.append(dict(file=n,expected=h,actual=actual))
d=lambda x:D(str(x))
base=m['base'];results=[]
for s in m['results']:
 c=m['cases'][s['scenario']];years=s['years'];r=years[0]
 rv=sum(d(x)*(1+d(g)) for x,g in zip(base['revenue'],c['g0']))
 gm=[d(x)+(d(t)-d(x))/5 for x,t in zip(base['gm'],c['gmEnd'])]
 cost=sum(d(x)*(1+d(g))*(1-margin) for x,g,margin in zip(base['revenue'],c['g0'],gm))
 core=rv-cost-rv*sum(d(c[k]) for k in ['sales','admin','rd'])-rv*d('.015')
 first=dict(revenue=float(rv),cost=float(cost),core_ebit=float(core),revenue_difference=float(rv-d(r['revenue'])),core_difference=float(core-d(r['core_ebit'])))
 cferrors=[abs(d(r['nopat'])+d(r['da'])-d(r['capex'])-d(r['delta_nwc'])-d(r['fcff'])) for r in years]
 pv=sum(d(r['fcff'])/(1+d(s['wacc']))**(i+1) for i,r in enumerate(years))
 tv=d(years[-1]['nopat'])*(1+d(s['g']))*(1-d(s['g'])/d(s['roic']))/(d(s['wacc'])-d(s['g']))/(1+d(s['wacc']))**10
 bridge=d(base['cash'])-d(base['cashReserve'])+d(base['financial'])-d(base['debt'])-d(base['minority'])
 price=(pv+tv+bridge)/d(base['shares'])
 results.append(dict(scenario=s['scenario'],first_year=first,independent_price=float(price),stored_price=s['price'],difference=float(price-d(s['price'])),max_cash_identity_error=float(max(cferrors)),bridge=float(bridge)))
assert max(abs(x['difference']) for x in results)<1e-10
pdf=next((B/'年报原件').glob('*2025年年度报告*'))
doc=pymupdf.open(pdf)
for page in [8,28,219]:
 (O/('年报2025_p'+str(page)+'.txt')).write_text(doc[page-1].get_text(sort=True),encoding='utf-8')
actual=[D('2195632312.92')/D('1e8'),D('1112547607.75')/D('1e8'),D('63892666.55')/D('1e8')]
forecasts=[dict(source='华创机械公众号',date='2025-04-08',metric='合并营业收入',forecast='21.45',actual=str(actual[0])),dict(source='华创机械公众号',date='2025-04-08',metric='归母净利润',forecast='10.90',actual=str(actual[1])),dict(source='华创机械公众号',date='2025-04-08',metric='三维解决方案收入',forecast='1.40',actual=str(actual[2])),dict(source='浙商机械公众号',date='2023-10-11',metric='归母净利润',forecast='12.70',actual=str(actual[1]))]
for r in forecasts:
 r['conditional_error_pct']=float((D(r['actual'])/D(r['forecast'])-1)*100)
 r['forecast_source_identity']='成员一已提交摘录，本轮未独立取得公众号正文，日期与预测原格待原文复核'
 r['actual_source']='2025年报物理p28三维收入／p8合并收入及归母净利，复核原文TXT另存'
report=dict(date='2026-11-26',executor='Codex成员三预测连接复核Agent；非原成员三本人，未代刘翔宇签署',model_files=fingerprints,input_pins=pins,model_parameters=dict(shares=288729927,financial_date='2025-12-31',annual_available='2026-04-10',base_wacc=.085,g=.02,roic=.20,identity='研究条件假设，不是行情参数或已实现经营事实'),dcf_recalculation=results,pdf_sha256=sha256(pdf.read_bytes()).hexdigest(),forecast_comparison=forecasts)
(O/'复核结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(fingerprints),identical=sum(x['identical'] for x in fingerprints),results=results,forecasts=forecasts),ensure_ascii=False))
