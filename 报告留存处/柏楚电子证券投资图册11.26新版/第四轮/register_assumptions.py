import sys,csv,json
from pathlib import Path
p=Path(sys.argv[1]);M=json.loads((p/'模型.json').read_text(encoding="utf-8"))
data=[]
anchors={"g0":"2024–2025分场景收入成本表p25、p27–28；十年线性退坡至g，需求或净价走弱则下修",
"gmEnd":"同表分组毛利；五年过渡，规格、搭配、折扣及成本改变则重估","sales":"2025p126销售费率；现场支持支出高则上调",
"admin":"2025p126管理费率；组织成本超支则上调","rd":"2025p126研发费率；新场景投入延长则上调","tax":"2025p167各主体税率；优惠变化则重算",
"days":"p121应收账款+票据+融资／收入×365；逾期则上调","inv":"p121、188存货／成本×365；硬件库龄恶化则上调",
"ap":"p122应付账款／成本×365；付款加快则下调","disc":"p213折扣余额／净收入；结算条款变化则修订",
"dep":"p213货款余额／净收入；预收条件变化则修订","sc":"多年资本支出与固定资产p121–122、129–131；Δ收入/增长净固定资本假设",
"roic":"Lec05 g/ROIC再投资约束；假设，新增资本回报恶化则下调","g":"稳定期条件增长；长期需求不支持则下调",
"wacc":"Rf、β、ERP及市场权重缺可核输入，研究条件；风险上升则上调"}
for key,ex in anchors.items():
 for c,s in M["cases"].items():data.append(dict(parameter=key,scenario=c,value=json.dumps(s[key]),identity="研究假设，以历史作锚",anchor_and_falsification=ex))
with (p/'关键假设来源.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,data[0].keys());w.writeheader();w.writerows(data)
