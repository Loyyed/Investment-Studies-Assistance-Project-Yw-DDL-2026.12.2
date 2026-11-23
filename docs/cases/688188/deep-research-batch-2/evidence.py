"""Build scope-labeled evidence tables, indexed to the issuer's physical PDF pages."""
import statistics
from datetime import date
from forecast import CASE, HERE, OUT, PRIOR, rows, read_json, select, write_csv, dump

OFFICIAL = {
    "POST-01": "https://roadshow.sseinfo.com/activityDetails/42275",
    "PRODUCT-01": "https://www.bochu.com/ch/product/fscut4000e/",
    "PRODUCT-02": "https://www.bochu.com/ch/product/bcs210e/",
    "PRODUCT-03": "https://www.bochu.com/ch/product/fscut7000/",
    "PEER-01": "https://static.sse.com.cn/stock/disclosure/announcement/c/202209/001048_20220906_D9NX.pdf",
    "POST-MIRROR": "https://financialfilings.com/filings/shanghai-bochu-electronic-technology-corporation-limited/call-meeting-transcript/2026/76423776/",
    "RIGHTS-01": "https://static.cninfo.com.cn/finalpage/2026-11-10/1225663640.PDF",
}


def main():
    OUT.mkdir(exist_ok=True)
    originals=rows(PRIOR/"originals.csv")
    source=rows(PRIOR/"filing-cells.csv")
    history=rows(PRIOR/"financial-bridge.csv")
    inventory=rows(PRIOR/"working-capital.csv")
    classifications=rows(PRIOR/"classification-cells.csv")
    product=rows(CASE/"product-bridge.csv")
    cap=rows(PRIOR/"capital-and-cash-bridge.csv")
    sources={x["period"]:x for x in originals}
    operating_notes={
       2019:("上市首年、招股书2018比较列及合并报表","p87–89、p160","三、上市前与上市起点；2018同口径接续"),
       2020:("扩张延续，现金购建先高后回落","合并利润表及现金流；附注主营、其他","三、扩张阶段；资本投入时差"),
       2021:("高增长与购建增加，建立压力测试的前一年","合并利润表及现金流；附注主营、其他","三、四、五；核心率与购建的周期对照"),
       2022:("收入回撤，利润和购建下降；CFO上升","p98、p102–103、p107","三、五；量价与现金可分离"),
       2023:("原产品表为随动、板卡、总线、切割头和其他，次年重列保证类质保","p24–26、p184；2024年报p153","三、四；锁定主营合计与分类断点"),
       2024:("应用解决方案分组、出货同名起点、2023成本重列","p25–27、p112–117、p153","三、四、七；框定分组、毛利和留出"),
       2025:("智能硬件量增快于控制量，成本性质比较列挪项","p8、p27–30、p121、p125–130","四、五、七；校准组价、库存和2025Q4季节"),
    }
    items=[]
    for period,s in sources.items():
        find={r["metric"]:r for r in source if r["report"]==period and r["column"]=="本期"}
        year=int(period[:4])
        label,note,use=operating_notes[year] if period.endswith("FY") else (
            "中报或季报累计；当季差分及现金解读",
            "首张主要财务数据、合并财务报表及可用附注",
            "四、五、七；累计与单季对照、余额另列")
        items.append(dict(period=period,available=s["available"],entity=find["revenue"]["entity"],
             source_id=s["source_id"],sha256=s["sha256"],url=find["revenue"]["url"],unit="人民币元；套数及费率另列",
             revenue_page=find["revenue"]["physical_page"],cost_page=find["cost"]["physical_page"],
             cash_page=find["cfo"]["physical_page"],statement_columns="本期／上年同期或本年末／上年末",
             event_or_adjustment=label,locator=note,report_use=use))
    write_csv("annual-evidence.csv",items)
    cost23=[183693827.33,31517779.97,839785.04,57621836.92]
    rates24=[11.83,38.19,409.90,63.45]
    main23=float(select(classifications,report="2023-FY",metric="主营业务",column="本期收入")["raw_value"])
    estimates=[]
    for p,cost,rate in zip(product,cost23,rates24):
        r=float(p["revenue_24"])*1e6
        low=r/(1+(rate+.005)/100)
        high=r/(1+(rate-.005)/100)
        estimates.append((low,high,(low+high)/2))
    assert sum(x[0] for x in estimates)<=main23<=sum(x[1] for x in estimates)
    gap=main23-sum(x[2] for x in estimates)
    range_weight=sum(x[1]-x[0] for x in estimates)
    reco=[]
    for p,cost,rate,(low,high,middle) in zip(product,cost23,rates24,estimates):
        adopted=middle+(high-low)/range_weight*gap
        reco.append(dict(group=p["group"],revenue_growth_24_disclosed_pct=rate,revenue23_lower=low,
                    revenue23_upper=high,revenue23_adopted=adopted,cost23_reclassified=cost,
                    revenue24=float(p["revenue_24"])*1e6,cost24=float(p["cost_24"])*1e6,
                    revenue25=float(p["revenue_25"])*1e6,cost25=float(p["cost_25"])*1e6,
                    locator="2024年报p25分组同比及p27精确比较成本；2023年报p24主营合计",
                    scope="2023分组收入为约束估计，采用值均在披露同比的舍入相容区间"))
    assert abs(sum(r["revenue23_adopted"] for r in reco)-main23)<1e-6
    assert abs(sum(cost23)-273673229.26)<1e-6
    write_csv("group-restatement.csv",reco)
    margins=[]
    for a,b in (("23","24"),("24","25"),("23","25")):
        keys={"23":"revenue23_adopted","24":"revenue24","25":"revenue25"}
        ckeys={"23":"cost23_reclassified","24":"cost24","25":"cost25"}
        ta,tb=(sum(x[keys[y]] for x in reco) for y in (a,b))
        for x in reco:
            ra,rb=(x[keys[y]] for y in (a,b))
            ca,cb=(x[ckeys[y]] for y in (a,b))
            ma,mb=(1-ca/ra,1-cb/rb)
            wa,wb=ra/ta,rb/tb
            margins.append(dict(period=a+"→"+b,group=x["group"],gross_delta_m=((rb-cb)-(ra-ca))/1e6,
              revenue_delta_m=(rb-ra)/1e6,margin_mix_pp=(wb-wa)*(ma+mb)/2*100,
              margin_inside_pp=(mb-ma)*(wa+wb)/2*100,
              contribution_pp=(wb*mb-wa*ma)*100,
              identity="中点分解，交互均摊；使用主营业收入权重，含2023时收入为区间采用值"))
    write_csv("gross-contribution.csv",margins)
    costs=[
       ("原材料",231380170.58,259870773.16,265572370.79,382696763.43),
       ("人工",13535446.81,18160132.01,18160132.01,27484865.74),
       ("制造",26727378.93,54248739.14,48547141.51,64330419.13),
       ("运输",1813270.15,2162482.31,2162482.31,3878713.16),
       ("实施",216962.79,2991.68,2991.68,0)]
    attributed=[]
    for group,v23,v24,v24r,v25 in costs:
        attributed.append(dict(name=group,year23_comparison=v23,year24_original=v24,year24_comparison=v24r,
                year25=v25 or None,delta_reclassification=v24r-v24,locator="2024年报p27、2025年报p29；合并主营成本分析"))
    known25=sum(r[4] for r in costs)
    cost25=sum(float(x["cost_25"]) for x in product)*1e6
    attributed.append(dict(name="2025其余直接成本合计",year23_comparison=None,year24_original=None,year24_comparison=None,
               year25=cost25-known25,delta_reclassification=None,locator="2025年报p29；总额减已单列的材料、人工、制造；不分配到质保"))
    write_csv("cost-attribution.csv",attributed)

    # A common trade subset, with stock averages across the matching seasonal endpoint.
    cash=[]
    historical_capital=[]
    for x in cap:
        year=int(x["period"][:4]); f=select(history,period=x["period"],column="本期")
        invest=float(x["trade_wc_yuan"])+sum(float(x[k] or 0) for k in ("fixed_yuan","cip_yuan"))
        nopat=float(x["nopat_proxy_yuan"])
        prior=historical_capital[-1] if historical_capital else None
        avg=(invest+prior["closing_capital_m"]*1e6)/2 if prior else None
        delta=invest-prior["closing_capital_m"]*1e6 if prior else None
        historical_capital.append(dict(year=year,closing_capital_m=invest/1e6,avg_capital_m=avg/1e6 if avg else None,
                  nopat_m=nopat/1e6,roic_proxy=(nopat/avg if avg else None),
                  incremental_roic_proxy=((nopat-prior["nopat_m"]*1e6)/delta if delta and delta>0 else None),
                  delta_capital_m=delta/1e6 if delta is not None else None,
                  scope="经营资本窄代理=贸易资本+固定资产+可提取在建；D&A与税用历史代理；无研发资本化"))
        cash.append(dict(year=year,cfo_m=float(f["cfo"])/1e6,capex_m=float(f["capex"])/1e6,
                    cfo_less_capex_m=float(f["cfo_less_capex"])/1e6,fcff_proxy_m=float(x["fcff_proxy_before_lease_yuan"])/1e6,
                    nopat_m=nopat/1e6,da_m=float(x["da_yuan"])/1e6,change_trade_m=float(x["trade_wc_change_yuan"])/1e6,
                    bridge_residue_m=float(x["proxy_minus_cfo_less_capex"])/1e6))
    write_csv("capital-returns.csv",historical_capital)
    write_csv("cash-history.csv",cash)
    days=[]
    for period in ("2025-FY","2025-YTD9","2026-H1","2026-YTD9"):
        days_elapsed=365 if period.endswith("FY") else (181 if period.endswith("H1") else 273)
        cur=select(inventory,report=period,column="期末")
        old=select(inventory,report=period,column="上年末")
        f=select(history,period=period,column="本期")
        for item,den in (("ar","revenue"),("inventory","cost"),("ap","cost")):
            avg=(float(cur[item])+float(old[item]))/2
            days.append(dict(period=period,item=item,opening=float(old[item]),closing=float(cur[item]),
                 average=avg,numerator_currency="CNY 元",flow_denom=float(f[den]),days_elapsed=days_elapsed,
                 approximate_days=days_elapsed*avg/float(f[den]),scope="期初期末均值，季内路径未知; 季末合同负债未并入窄口径"))
    write_csv("trade-days.csv",days)

    # Two independent as-of reconstructions using only original prior annual filings.
    h={int(x["period"][:4]):x for x in history if x["period"].endswith("FY") and x["column"]=="本期"}
    backs=[]
    for target in (2022,2023,2024,2025):
        tr=list(range(target-3,target))
        last=float(h[tr[-1]]["revenue"])
        r=[float(h[y]["revenue"])/float(h[y-1]["revenue"])-1 for y in tr[1:]]
        flag=f'{target-1}-FY'
        actual=float(h[target]["revenue"])
        for name,pred in (("三份年报增长中位数",last*(1+statistics.median(r))),("原规模持平",last)):
            backs.append(dict(target=target,cutoff=sources[flag]["available"],input_reports="／".join(str(y) for y in tr),
                        input_ids="／".join(sources[f"{y}-FY"]["source_id"] for y in tr),method=name,
                        predicted_yuan=pred,actual_yuan=actual,error_yuan=pred-actual,error_pct=(pred/actual-1)*100,
                        target_source=sources[f"{target}-FY"]["source_id"],target_available=sources[f"{target}-FY"]["available"],
                        definition="首次披露原列。发布当时只训练年报，先封存信息集再比对目标；无散户或研报信息偷渡"))
    write_csv("annual-holdouts.csv",backs)
    analyst=[]
    actual_3d=float(product[2]["revenue_25"])*1e6
    # Sum of reported 2025E segment costs after independently converting only the ambiguous cell.
    # Segment values are independently recorded from the source page in analyst-units.json.
    units=read_json(HERE/"analyst-units.json")
    sign=float(units["printed"]); other=float(units["other_segments_cost_100m"]); total=float(units["group_cost_100m"])
    for mode,mult in (("按图注亿元原印值",1),("仅此格按万元条件换算",1e-4)):
        value=sign*mult
        analyst.append(dict(mode=mode,printed=sign,cost_100m=value,revenue_100m=1.4,
                        margin=1-value/1.4,remaining_group_cost_100m=total-(value+other),
                        other_segments_cost_100m=other,reported_group_cost_100m=total,
                        actual_2025_3d_revenue_yuan=actual_3d,locator=units["locator"],
                        caveat="单位条件诊断；公司三维实际成本与券商预测不同；待券商原工作底表"))
    write_csv("analyst-unit-test.csv",analyst)

    # 100 yuan of incremental net hardware sales, a matched-OEM sensitivity, not actual margin.
    attach=[]
    for GM in (.41,.50,.55):
        for days_inv, days_ar in ((150,65),(110,45),(85,29)):
            sales=100; costs=sales*(1-GM); tax=.13; carrying=costs*days_inv/365+sales*days_ar/365-costs*50/365
            install=4; capex=3; opportunity=2; service=5
            net=(sales-costs-install-opportunity-service)*(1-tax)-carrying-capex
            room=(sales-costs-install-opportunity)-(carrying+capex)/(1-tax)
            attach.append(dict(gross_margin=GM,net_sales=sales,cost=costs,installation=install,
                               control_allowance=opportunity,cash_tax=tax,inventory_days=days_inv,ar_days=days_ar,
                               ap_days=50,opening_trade_cash_cost=carrying,gross_capex=capex,service_scenario=service,
                               first_cohort_cash=net,maximum_service_for_positive_cash=room,
                               scope="每100元增量硬件净收入；初始建立占款一次，次批补付的增量仅按占款变化走"))
    write_csv("bundle-cash-thresholds.csv",attach)
    dump("links.json",OFFICIAL)


if __name__ == "__main__":
    main()
