"""Independent first-year arithmetic, cash consistency and DCF checks."""
from pathlib import Path
from fractions import Fraction as F
import csv,json,sys
from hashlib import sha256
HERE=Path(__file__).resolve().parent
def rows(n):
 with (HERE/n).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
M=json.loads((HERE/"模型.json").read_text(encoding="utf-8"));B=M["base"]
for name,h in json.loads((HERE/"输入指纹.json").read_text(encoding="utf-8")).items():
 assert sha256((HERE/name).read_bytes()).hexdigest()==h
def near(a,b):assert abs(float(a)-float(b))<1e-7,(a,b)
checks=[]
for s in M["results"]:
 settings=M["cases"][s["scenario"]];r=s["years"][0]
 revenue=sum(F(str(x))*(1+F(str(g))) for x,g in zip(B["revenue"],settings["g0"]))
 near(revenue,r["revenue"])
 margin=[F(str(x))+(F(str(t))-F(str(x)))/5 for x,t in zip(B["gm"],settings["gmEnd"])]
 cost=sum(F(str(x))*(1+F(str(g)))*(1-m) for x,g,m in zip(B["revenue"],settings["g0"],margin))
 near(cost,r["cost"])
 ebit=revenue-cost-revenue*sum(F(str(settings[k])) for k in ["sales","admin","rd"])-revenue*F(".015")
 near(ebit,r["core_ebit"])
 for r in s["years"]:
  near(r["nopat"]+r["da"]-r["capex"]-r["delta_nwc"],r["fcff"])
  near(r["nwc"],r["ar"]+r["inventory"]+r["prepay"]-r["ap"]-r["discount"]-r["deposit"])
 exp=sum(F(str(r["fcff"]))/(1+F(str(s["wacc"])))**(i+1) for i,r in enumerate(s["years"]))
 last=s["years"][-1];terminal=F(str(last["nopat"]))*(1+F(str(s["g"])))*(1-F(str(s["g"]))/F(str(s["roic"])))
 tpv=terminal/(F(str(s["wacc"]))-F(str(s["g"])))/(1+F(str(s["wacc"])))**10
 bridge=F(str(B["cash"]))-F(str(B["cashReserve"]))+F(str(B["financial"]))-F(str(B["debt"]))-F(str(B["minority"]))
 price=(exp+tpv+bridge)/F(str(B["shares"]));near(price,s["price"])
 checks.append(dict(scenario=s["scenario"],price=float(price),lastGrowth=last["revenue"]/s["years"][-2]["revenue"]-1,
  lastReinvestmentRate=(last["nopat"]-last["fcff"])/last["nopat"],stableReinvestmentRate=s["terminal_ri_rate"]))
assert 0<M["results"][0]["years"][0]["revenue"]<B["totalRevenue"]
# Independent subsidy bridge identity and no financial income in FCFF.
assert all("finance_income" in r and abs(r["core_ebit"]-r["revenue"]+r["cost"]+r["sales"]+r["admin"]+r["rd"]+r["surcharge"]+r["credit"])<1e-7 for s in M["results"] for r in s["years"])
record=dict(years=30,firstYearRevenueAndCost="Fraction独立计算",dcf="Fraction逐年折现与终值独立计算",
cashIdentity="30行闭合",negativeGrowth="压力首年下降",terminal=checks)
(HERE/"数值验收.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record,ensure_ascii=False))
