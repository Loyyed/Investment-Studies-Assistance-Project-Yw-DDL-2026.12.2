"""Capture source-tagged quarterly and acquisition economics, separate from the forecast."""
from forecast import CASE, HERE, OUT, PRIOR, read_json, rows, select, write_csv

ISSUER = "上海柏楚电子科技股份有限公司"
Q3 = "688188-fed67b607fa475a7"
H1 = "688188-20b73bb3528dbdbe"
SRC = "2026Q3／2026H1 本期与比较，均为合并渠道"
M = 1e6


def main():
    s=read_json(HERE/"supplement.json")
    financial=rows(PRIOR/"financial-bridge.csv")
    ytd=[select(financial,period="2026-YTD9",column=x) for x in ("本期","比较")]
    q3=[select(financial,period=x,column="本期相减") for x in ("2026-Q3","2025-Q3")]
    rec=[]
    for x in ("revenue","cost","gross","surcharge","sales","admin","rd","core_ebit","reported_ebit",
              "income_tax","net_profit","parent_profit","minority_profit","cfo","capex","cfo_less_capex"):
        a,b=(float(r[x]) for r in ytd)
        c,d=(float(r[x]) for r in q3)
        rec.append(dict(item=x,ytd26=a,ytd25=b,q3_26=c,q3_25=d,q3_change=c-d,ytd_change=a-b,
                    unit="CNY元",source=f"{Q3}／{H1}",locator="Q3 p8–11；中报p65–70；方法见财务桥",
                    role="原量及AgentCalculated，单季按本期／上年同期各差分"))
    for x,a,b,c,d,l,n in s["income"]:
        rec.append(dict(item=x,ytd26=a,ytd25=b,q3_26=a-c,q3_25=b-d,q3_change=a-c-b+d,ytd_change=a-b,
                    unit="CNY元",source=f"{Q3}／{H1}",locator=l,role=n))
    a,yp,b,yp9=s["q3_parent_deduction"]
    rec.append(dict(item="扣非归母",ytd26=b,ytd25=None,q3_26=a,q3_25=None,q3_change=None,ytd_change=None,
                    unit="CNY元",source=Q3,locator="p1 主要财务数据，单季／累计本期",
                    role=f"发行人给定同比分别{yp}%与{yp9}%，金额同比未由舍入百分比逆算"))
    write_csv("recent-income-bridge.csv",rec)
    cf=[["销售商品、提供劳务收到的现金",1907681633.97,1635897385.56],*s["cashflow_ytd"]]
    calc=[]
    for i,(m,a,b) in enumerate(cf):
        flow_sign=1 if i<=2 else -1
        calc.append(dict(item=m,ytd26=a,ytd25=b,change=a-b,cfo_effect=flow_sign*(a-b),
                    locator=f"{Q3} p{10 if i==0 else 11} 合并现金流",unit="CNY元"))
    assert abs(sum(z["cfo_effect"] for z in calc)-58802313.68)<.02
    write_csv("cfo-change.csv",calc)
    liab=[]
    for period,stock in s["liability"].items():
        liab.append(dict(period=period,contract_liability_yuan=stock,report_id=Q3,loc="Q3 p7 合并期末或上年末",
                      scope="合同负债不等订单额，金额包含公司不同预收项目"))
    write_csv("contract-liabilities.csv",liab)
    prod=[]
    for k,r,c in s["product23"]:
        prod.append(dict(classification=k,revenue=r,cost=c,gross=r-c,unit="CNY元",
                 locator="2023年报p24 分产品原表，本期；重列前",source="688188-d931e02dd1c67f13"))
    assert abs(sum(x["revenue"] for x in prod)-1395893984.50)<.01
    write_csv("2023-product-original.csv",prod)
    mdl=read_json(OUT/"model.json")
    value=mdl["scenarios"]["base"]
    end=value["path"][-1]
    def retention_per_head(price,gm,field,days_ar,days_inv):
        return (price*gm-price*field)*.87-price*days_ar/365-price*(1-gm)*(days_inv-50)/365
    projects=[]
    for name,price,vols,gm,stage,locator in (
      ("切割头增量",4500,(3000,10000),.50,"已可证产品批量销售，集团智能硬件为代理","2023年报p24；2025年报p29；结项公告p6、p9–11"),
      ("免示教弧焊",50000,(50,400),.42,"可证方案与行业合作；缺匹配订单回款","2025年报经营讨论、2026-001 p9–11、路演Q2/Q4"),
      ("锂电激光焊",110000,(20,160),.39,"可证项目预算与技术路径","2026-001 p18–19，项目基本情况／投资计划"),
      ("超快精密微加工",35000,(100,700),.50,"可证产品功能与研发，不同于终端设备销量","发行人 FSCUT7000；2025年报经营讨论；2026-001 p9–10")):
        for n in vols:
            projects.append(dict(project=name,condition_units=n,conditional_net_price_yuan=price,gross_condition=gm,
                                 condition_revenue_yuan=n*price,
                                 first_cohort_cash_before_special_capex=n*retention_per_head(price,gm,.12,60,120),
                                 highest_evidence=stage,locator=locator,
                                 scope="条件测试的订单规模及净价，无现实量分母；12%适配售后、应收60天、库存120天、应付50天、税13%"))
    write_csv("project-conditional-scale.csv",projects)
    comparables=[]
    for d,price,shares,profit,origin in (
      ("2025-04-08",170.87,205.4551,882.71021715,"华创 p1 原股本和报价、2024年报归母"),
      ("2026-11-12",96.2,405.984426,1308.69970298,"冻结股本与行情，FY25＋26前三季－25前三季归母")):
        comparables.append(dict(date=d,price_unadjusted=price,shares_m=shares,market_cap_m=price*shares,
                                trailing_parent_profit_m=profit,pe=(price*shares)/profit,
                                origin=origin,scope="以当日已知同股权未复权价格×当日总股数／最近披露滚动归母"))
    write_csv("own-relative.csv",comparables)
    tests=[]
    for multiple in (15,25,35):
        eq=(value["explicit_pv"]+end["core_ebit"]*multiple/(1+value["wacc"])**end["t"]+
            mdl["receipt"]["cash_bridge"])/(mdl["receipt"]["shares"]/M)
        tests.append(dict(style="S8方法对照，参数为本报告压力选点",terminal_year=2035,ev_ebit=multiple,
                          terminal_core_m=end["core_ebit"],implied_price=eq,
                          convention="用末年核心 EBIT×EV/EBIT替换Gordon终值，仍折现至同一日期，不同时加两套TV"))
    write_csv("exit-sensitivity.csv",tests)


if __name__=="__main__":
    main()
