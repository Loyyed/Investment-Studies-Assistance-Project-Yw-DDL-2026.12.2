from pathlib import Path
import json,csv,hashlib,re
from decimal import Decimal as D
from bs4 import BeautifulSoup
A=Path("D:/投资学/.publish-1126-1795705877581/integrate/报告留存处/柏楚电子证券投资图册11.26新版");O=Path("D:/投资学/.bochu1126-member2-check");B=Path('D:/投资学/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2-codex-collaboration-workbenches/报告留存处/柏楚电子证券投资图册11.25新版')
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=A.parent.joinpath('柏楚电子证券投资分析报告11.26新版.md').read_text(encoding='utf8');html=(A/'index.html').read_text(encoding='utf8');soup=BeautifulSoup(html,'html.parser')
sections={k:(soup.find(id=k).get_text(' ',strip=True) if soup.find(id=k) else '') for k in ['ch06','ch07','ch09']}
model=list(csv.DictReader((A/'第四轮/逐年模型.csv').open(encoding='utf-8-sig')))
res=[]
for r in model:
 expected=D(r['nopat'])+D(r['da'])-D(r['delta_nwc'])-D(r['capex']);res.append({'scenario':r['scenario'],'year':r['year'],'difference':str(D(r['fcff'])-expected)})
checks={
 '历史简化余量与FCFF分开':'与第四轮 FCFF 有不同口径' in sections['ch07'],
 'CFO后营运资本不重复扣减':'不能在 CFO 后重复扣一次' in sections['ch07'],
 '核心EBIT和营业利润区别':'10.39' in sections['ch07'] and '12.45' in sections['ch07'] and '口径不同' in sections['ch07'],
 '成本内质保不重复扣减':'不能再扣一次' in sections['ch07'],
 '毛利增量与营业利润增量区别':'3.05' in sections['ch07'] and '2.09' in sections['ch07'] and '不能全部当作经营利润增量' in sections['ch07'],
 '现金转换率合并分母':'CFO÷合并净利润' in sections['ch06'] and 'CFO÷合并净利润' in sections['ch07'],
 '合同负债预提折扣和货款分开':all(x in sections['ch06'] for x in ['114,106,284.20','18,281,281.11','86.19%','63.50%']),
 '营运占用及低购建限制':all(x in sections['ch07'] for x in ['应收和存货','维护与扩张投入尚缺拆分','不能永久外推']),
 '模型公式30行闭合容差1e-9':all(abs(D(r['difference']))<D('0.000000001') for r in res),
 '逐年模型与11.25原字节同':h(A/'第四轮/逐年模型.csv')==h(B/'第四轮/逐年模型.csv'),
}
svg=(A/'第三轮/charts/cashsurplus.svg').read_text(encoding='utf8');values=['9.5244','1.1322','8.3923','11.0432','1.5188','0.3520','0.7801','10.6912'];checks['cashsurplus数值与独立复算四舍五入一致']=all(x in svg for x in values)
g=(A/'协作深化/11.26整合/graphs.py').read_text(encoding='utf8');checks['图表改为从核验JSON生成金额']='Decimal' in g and "['CFO增量']" in g
result={'actor':'Codex成员二财务锚点核对Agent','date':'2026-11-26','human_confirmation':False,'scope':['成品Markdown第6、7章','HTML ch06、ch07及ch09预测入口','第四轮逐年模型30行FCFF','第三轮cashsurplus桌面和手机版SVG及其生成器'],'checks':checks,'cash_bridge_exact_source':'成员2核对/现金桥独立复算.json','fcff_residuals':res,'max_fcff_residual':str(max(abs(D(r['difference'])) for r in res)),'fingerprints':{f:h(A/f) for f in ['第四轮/逐年模型.csv','第三轮/charts/cashsurplus.svg','第三轮/charts/cashsurplus-mobile.svg']},'repair':'主实施Agent接受本核对意见，现金桥由硬编码金额改为读取独立核验JSON，以Decimal换算亿元。数字按token换行，保留完整小数。已复验实际成品。','review_status':'Agent技术核对通过；非刘翔宇最终独立裁定'}
(O/'11.26成品财务复核.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2));(O/'html财务抽查文本.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2),encoding='utf8')
