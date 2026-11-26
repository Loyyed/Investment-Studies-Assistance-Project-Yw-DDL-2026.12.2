from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import pymupdf,re,json,hashlib
p=Path(__file__).resolve().parent
a=p/'公开补证原件'
d=pymupdf.open(a/'宏石激光_招股书注册稿_2023-10-12.pdf')
r=next(x for x in d[159].get_text(sort=True).splitlines() if '系统控制类' in x)
v=[Decimal(x.replace(',','')) for x in re.findall(r'\d[\d,]*\.\d{2}',r)]
t=next(x for x in d[164].get_text(sort=True).splitlines() if '4,388.51' in x)
tot=[Decimal(x.replace(',','')) for x in re.findall(r'\d[\d,]*\.\d{2}',t)][:4]
checks=[]
for period,n,reported,den in zip(['2023H1','2022','2021','2020'],v[::2],v[1::2],tot):
 calc=n/den*100; rounded=calc.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
 checks.append(dict(period=period,numerator=str(n),denominator=str(den),unit='万元',formula='分子/分母*100',calculated=str(calc),rounded=str(rounded),reported=str(reported),difference_pp=str(rounded-reported),pages=[160,165],scope='系统控制类/系统控制软硬件采购总额（不含税）'))
 assert rounded==reported
j=pymupdf.open(a/'嘉泰激光_招股说明书申报稿_2026-06-22.pdf')
jt=j[99].get_text(sort=True)
for val in ['13,487.95','21.72%','10,873.14','20.40%','9,260.25','16.40%']:
 assert val in jt
reply=pymupdf.open(a/'宏石激光_深交所问询回复.pdf');narrow=next(x for x in reply[95].get_text(sort=True).splitlines() if x.startswith('柏楚电子'))
assert re.search(r'1,300.46\s+40.17\s+2.15\s+-\s+-\s+-',narrow)
result={'date':'2026-11-26','actor':'Codex 子Agent /root/member1_verification（本轮独立内容核对，非原成员一本人，非刘翔宇人工签署）','hongshi_checks':checks,'jiatai_original_cells':{'page':100,'printed_page':'1-1-99','table':'主要供应商情况/前五名供应商','supplier':'上海柏楚电子科技股份有限公司（同一控制下合并）','products':'光纤激光切割头、数控系统等','2023':['9260.25','16.40%'],'2024':['10873.14','20.40%'],'2025':['13487.95','21.72%'],'unit':'万元','denominator':'嘉泰当期采购总额','status':'原表文本与渲染图对读，百分比不反推未披露精确分母'},'narrow_scope':{'page':96,'2022':'原表横线，不改写零','2023H1_calculation':'1300.46/3237.16*100','value':str(Decimal('1300.46')/Decimal('3237.16')*100)},'pdf_fingerprints':[{ 'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'pages':len(pymupdf.open(f))}for f in sorted(a.glob('*.pdf'))]}
(p/'采购原格独立核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))
