"""2025 year-end conditional FCFF model. All amounts in CNY million."""
import csv,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
STAGE=HERE.parent
FIRST=STAGE/"第一轮"
def rows(f):
 with f.open(encoding="utf-8-sig",newline="") as h:return list(csv.DictReader(h))
def csvout(f,data):
 with f.open("w",encoding="utf-8-sig",newline="") as h:
  w=csv.DictWriter(h,list(dict.fromkeys(k for r in data for k in r)),lineterminator="\n");w.writeheader();w.writerows(data)
from hashlib import sha256
for name,expected in json.loads((HERE/"输入指纹.json").read_text(encoding="utf-8")).items():
 assert sha256((HERE/name).read_bytes()).hexdigest()==expected,name
R=rows(FIRST/"清洗底表.csv")
sources=[]
def get(y,t,k,col=None,role="本期"):
 found=[r for r in R if r["报告年度"]==str(y) and r["表名"]==t and r["原行"]==k and r["列角色"]==role and (col is None or r["原列"]==col)]
 assert len(found)==1,(y,t,k,col)
 r=found[0];assert r["标准值"]!="",(y,k)
 sources.append(r)
 return float(r["标准值"])/1e6
IS="合并利润表";BS="合并资产负债表";CF="合并现金流量表";SUP="现金流量表补充资料";P="管理层讨论与分析·主营业务分产品情况"
GROUPS=["平面解决方案","管材解决方案","三维解决方案","其他主营","其他业务"]
base_rev=[];base_gm=[]
for g in GROUPS[:4]:
 label="其他" if g=="其他主营" else g
 r=get(2025,P,label,"营业收入");c=get(2025,P,label,"营业成本");base_rev.append(r);base_gm.append(1-c/r)
r=get(2025,"营业收入和营业成本附注","其他业务","本期发生额·收入");c=get(2025,"营业收入和营业成本附注","其他业务","本期发生额·成本")
base_rev.append(r);base_gm.append(1-c/r)
revenue=sum(base_rev)
BSK=["货币资金","交易性金融资产","其他非流动金融资产","长期股权投资","应收账款","应收票据","应收款项融资","预付款项","存货","应付账款","短期借款","租赁负债","一年内到期的非流动负债","少数股东权益","实收资本（或股本）","归属于母公司所有者权益（或股东权益）合计"]
balance={k:get(2025,BS,k) for k in BSK}
# Cash equivalents excludes the ETC frozen balance. Payables do not include unidentified balances.
cash=get(2025,SUP,"现金的期末余额","本期金额")
shares=balance["实收资本（或股本）"] # Shares total independently checked at 2025 annual report p219
discount=114.10628420;deposit=18.28128111
nw0=sum(balance[k] for k in ["应收账款","应收票据","应收款项融资","预付款项","存货"])-balance["应付账款"]-discount-deposit
da0=sum(get(2025,SUP,k,"本期金额") for k in ["固定资产折旧、油气资产折耗、生产性生物资产折旧","使用权资产摊销","无形资产摊销","长期待摊费用摊销"])
history=[]
for y in range(2019,2026):
 rv=get(y,IS,"一、营业总收入");co=get(y,IS,"其中：营业成本")
 exps=[get(y,IS,k) for k in ["税金及附加","销售费用","管理费用","研发费用"]]
 creditrow=next(r for r in R if r["报告年度"]==str(y) and r["表名"]==IS and r["列角色"]=="本期" and r["原行"].startswith("信用减值损失"))
 core=rv-co-sum(exps)+get(y,IS,creditrow["原行"])
 history.append(dict(year=y,revenue=rv,cost=co,core_ebit=core,sales=exps[1],admin=exps[2],rd=exps[3],
  capex=get(y,CF,"购建固定资产、无形资产和其他长期资产支付的现金"),
  cfo=get(y,CF,"经营活动产生的现金流量净额"),net=get(y,IS,"五、净利润（净亏损以“－”号填列）")))
net0=history[-1]["net"];parent0=get(2025,IS,"1.归属于母公司股东的净利润（净亏损以“-”号填列）") if any(r["报告年度"]=="2025" and r["原行"]=="1.归属于母公司股东的净利润（净亏损以“-”号填列）" for r in R) else get(2025,IS,"1.归属于母公司所有者的净利润（净亏损以“-”号填列）")
CASES={
"压力":dict(g0=[-.08,.02,.08,.03,0],gmEnd=[.77,.78,.78,.45,.45],sales=.075,admin=.075,rd=.18,tax=.17,days=65,inv=220,ap=50,disc=.045,dep=.006,sc=2,roic=.12,g=.01,wacc=.10),
"基准":dict(g0=[.10,.16,.25,.20,.06],gmEnd=[.80,.83,.82,.51,.50],sales=.063,admin=.068,rd=.155,tax=.13,days=48,inv=185,ap=60,disc=discount/revenue,dep=deposit/revenue,sc=3,roic=.20,g=.02,wacc=.085),
"改善":dict(g0=[.16,.23,.35,.30,.08],gmEnd=[.83,.86,.85,.55,.55],sales=.060,admin=.063,rd=.145,tax=.11,days=40,inv=150,ap=65,disc=.052,dep=.01,sc=4,roic=.28,g=.025,wacc=.075)}
B={"revenue":base_rev,"gm":base_gm,"nwc":nw0,"da":da0,"totalRevenue":revenue,"arDays":sum(balance[k] for k in ["应收账款","应收票据","应收款项融资"])/revenue*365,
"invDays":balance["存货"]/history[-1]["cost"]*365,"apDays":balance["应付账款"]/history[-1]["cost"]*365,"prepayRate":balance["预付款项"]/history[-1]["cost"],
"discount":discount,"deposit":deposit,"cash":cash,"financial":balance["交易性金融资产"]+balance["其他非流动金融资产"]+balance["长期股权投资"],
"debt":sum(balance[k] for k in ["短期借款","租赁负债","一年内到期的非流动负债"])+14.35057043,"minority":balance["少数股东权益"],
"shares":shares,"book":balance["归属于母公司所有者权益（或股东权益）合计"],"net":net0,"parent":parent0,"core":history[-1]["core_ebit"],
"cashReserve":revenue*.08,"financeYield":.015}
def run(name="基准",wacc=None,g=None,margin=0,days=0,cap=1,project=False):
 s=CASES[name];w=s["wacc"] if wacc is None else wacc;g=s["g"] if g is None else g
 assert 0<=g<w and s["roic"]>g
 rev=B["revenue"][:];prevNW=B["nwc"];prevNOP=None;prevRev=B["totalRevenue"];a=[]
 for i in range(10):
  fade=i/9
  grows=[s["g0"][j]*(1-fade)+g*fade for j in range(5)]
  rev=[rev[j]*(1+grows[j]) for j in range(5)]
  gm=[B["gm"][j]+(s["gmEnd"][j]-B["gm"][j])*min((i+1)/5,1)+margin for j in range(5)]
  total=sum(rev);costs=[rev[j]*(1-gm[j]) for j in range(5)];cost=sum(costs)
  sales=total*s["sales"];admin=total*s["admin"];rd=total*s["rd"]
  surcharge=total*.013
  credit=total*.002 # recurring credit loss provision treated as cash-equivalent economic expense
  ebit=total-cost-sales-admin-rd-surcharge-credit
  # Independent new activity case is included inside other-main total, then incremental costs charged here.
  venture=0 if not project else max(0,(i-1))*2
  extra=0 if not project else (8 if i<3 else 3)
  ebit+=venture*(.25-gm[3])-extra
  tax=max(ebit,0)*s["tax"];nop=ebit-tax
  ar=total*(s["days"]+days)/365;inv=cost*s["inv"]/365;ap=cost*s["ap"]/365;pre=cost*B["prepayRate"]
  disc=total*s["disc"];dep=total*s["dep"]
  nw=ar+inv+pre-ap-disc-dep;dn=nw-prevNW
  da=total*(B["da"]/B["totalRevenue"])
  expansion=max(total-prevRev,0)/s["sc"]
  capex=(da+expansion)*cap+(5 if project and i<3 else 0)
  # Fade reinvestment into the terminal incremental return constraint in the last three explicit years.
  mix=max(0,(i-6)/3)
  if prevNOP is not None:
   desired=max(nop-prevNOP,0)/s["roic"]
   capex=capex*(1-mix)+(da+desired-dn)*mix
  assert capex>=0
  fcff=nop+da-capex-dn
  finance=max(B["cash"]-B["cashReserve"]+B["financial"],0)*B["financeYield"]
  fullnet=nop+finance*(1-s["tax"])-B["debt"]*.035*(1-s["tax"])
  parent=fullnet*.98
  row=dict(scenario=name,year=2026+i,**{f"rev_{j}":rev[j] for j in range(5)},revenue=total,cost=cost,gross=total-cost,sales=sales,admin=admin,rd=rd,
   surcharge=surcharge,credit=credit,core_ebit=ebit,cash_tax=tax,nopat=nop,da=da,ar=ar,inventory=inv,prepay=pre,ap=ap,
   discount=disc,deposit=dep,nwc=nw,delta_nwc=dn,capex=capex,fcff=fcff,finance_income=finance,net=fullnet,parent=parent,
   eps=parent/B["shares"],pv=fcff/(1+w)**(i+1),project_reallocated_revenue=venture,project_expense=extra)
  a.append(row);prevNW=nw;prevNOP=nop;prevRev=total
 last=a[-1];stable_nop=last["nopat"]*(1+g);ri=g/s["roic"]
 terminal_fcff=stable_nop*(1-ri);tv=terminal_fcff/(w-g);tpv=tv/(1+w)**10
 explicit=sum(r["pv"] for r in a);ev=explicit+tpv
 bridge=B["cash"]-B["cashReserve"]+B["financial"]-B["debt"]-B["minority"]
 equity=ev+bridge;price=equity/B["shares"]
 return dict(scenario=name,wacc=w,g=g,roic=s["roic"],explicit_pv=explicit,terminal_pv=tpv,terminal_fcff=terminal_fcff,
  terminal_reinvestment=stable_nop*ri,terminal_nopat=stable_nop,terminal_weight=tpv/ev,ev=ev,bridge=bridge,equity=equity,price=price,
  terminal_ri_rate=ri,explicit_last_ri=last["nopat"]-last["fcff"],years=a)
def build():
 out=[run(n) for n in CASES];csvout(HERE/"逐年模型.csv",[r for s in out for r in s["years"]])
 (HERE/"模型.json").write_text(json.dumps(dict(base=B,cases=CASES,results=out,history=history),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 csvout(HERE/"估值汇总.csv",[{k:v for k,v in s.items() if k!="years"} for s in out])
 sens=[dict(wacc=w,g=g,price=run(wacc=w,g=g)["price"]) for w in [.07,.08,.085,.09,.10,.11] for g in [.01,.02,.025,.03]]
 csvout(HERE/"折现与增长敏感性.csv",sens)
 csvout(HERE/"资本回报敏感性.csv",[dict(roic=r,price=(sum(x["pv"] for x in out[1]["years"])+out[1]["terminal_nopat"]*(1-.02/r)/(.085-.02)/(1.085)**10+out[1]["bridge"])/B["shares"]) for r in [.10,.15,.20,.25,.30]])
 csvout(HERE/"利润现金联合阈值.csv",[dict(margin_shift=m,ar_days_shift=d,price=run(margin=m,days=d)["price"]) for m in [-.04,-.02,0,.02,.04] for d in [0,15,30,60]])
 csvout(HERE/"购建与经营现金保留.csv",[dict(capex_multiplier=c,cash_reserve_rate=r,price=run(cap=c)["price"]-(revenue*r-B["cashReserve"])/B["shares"]) for c in [1,1.5,2] for r in [.05,.08,.15]])
 mult=[]
 base=out[1];f=base["years"][0];eps0=B["parent"]/B["shares"];eps3=base["years"][2]["eps"];growth=(eps3/eps0)**(1/3)-1
 for price in [40,60,80,100,120,base["price"]]:
  mc=price*B["shares"];ev=mc-B["cash"]+B["cashReserve"]-B["financial"]+B["debt"]+B["minority"]
  mult.append(dict(price=price,identity="研究假设价格网格" if price!=base["price"] else "基准DCF条件值",
   PE_FY2025_TTM_at_20251231=mc/B["parent"],forwardPE2026=price/f["eps"],PB=mc/B["book"],PS=mc/revenue,
   PEG_PE2026_EPS2025to28=price/f["eps"]/(growth*100) if growth>0 else "",EPS_CAGR=growth,
   EV_coreEBIT=ev/B["core"],ROE_ending=B["parent"]/B["book"]))
 csvout(HERE/"条件倍数.csv",mult)
 csvout(HERE/"倍数条件价格.csv",[dict(PE2026=pe,price=pe*f["eps"],identity="研究条件，非市场估值带") for pe in [15,20,25,30]])
 checks=[dict(case="负增长",revenue_change=out[0]["years"][0]["revenue"]/revenue-1,fcff=out[0]["years"][0]["fcff"]),
 dict(case="应收延迟30天",price=run(days=30)["price"],firstFCFF=run(days=30)["years"][0]["fcff"]),
 dict(case="购建翻倍",price=run(cap=2)["price"],firstFCFF=run(cap=2)["years"][0]["fcff"]),
 dict(case="焊接微加工投入条件",price=run(project=True)["price"],delta=run(project=True)["price"]-base["price"])]
 assert run(days=30)["years"][0]["fcff"]<f["fcff"] and run(cap=2)["price"]<base["price"]
 for s in out:
  for r in s["years"]:assert abs(r["fcff"]-(r["nopat"]+r["da"]-r["capex"]-r["delta_nwc"]))<1e-8
 csvout(HERE/"压力一致性检查.csv",checks)
 refund=[]
 for rate in [0,.02,.04]:
  pv=sum(r["revenue"]*rate*(1-CASES["基准"]["tax"])/(1+base["wacc"])**(i+1) for i,r in enumerate(base["years"]))
  tv=base["years"][-1]["revenue"]*(1+base["g"])*rate*(1-CASES["基准"]["tax"])*(1-base["g"]/base["roic"])/(base["wacc"]-base["g"])/(1+base["wacc"])**10
  refund.append(dict(refund_rate=rate,explicit_support_pv=pv,terminal_support_pv=tv,price=base["price"]+(pv+tv)/B["shares"],identity="按净收入比例的条件经营支持，额外营运资本及资格差异留缺"))
 csvout(HERE/"税返延续敏感性.csv",refund)
 equity=[dict(item=k,amount=v,source=src) for k,v,src in [
 ("经营现金",B["cash"],"2025年报p230–231现金等价物"),
 ("金融及长期股权资产",B["financial"],"2025年报p121–122，见输入原格"),
 ("保留经营现金",-B["cashReserve"],"假设为2025净收入8%，区间5%–15%"),
 ("融资负担",-B["debt"],"短借p122＋租赁p123及216＋票据p217"),
 ("少数权益",-B["minority"],"2025年报p123，账面代理"),
 ("股数百万股",B["shares"],"2025年报p219股份总数")]]
 csvout(HERE/"股权桥来源.csv",equity)
 # Historical blind one-step rule, only prior year growth used.
 hold=[]
 for i in range(2,len(history)):
  y=history[i];prev=history[i-1];older=history[i-2]
  forecast=prev["revenue"]*(1+prev["revenue"]/older["revenue"]-1)
  hold.append(dict(year=y["year"],forecast=forecast,actual=y["revenue"],error=forecast/y["revenue"]-1,rule="只延续上年原列营收增速，跨范围描述性留出"))
 csvout(HERE/"历史留出.csv",hold)
 unique={r["单元ID"]:r for r in sources};csvout(HERE/"输入原格.csv",list(unique.values()))
 print([(s["scenario"],round(s["price"],2),round(s["terminal_weight"],3)) for s in out])
if __name__=="__main__":build()
