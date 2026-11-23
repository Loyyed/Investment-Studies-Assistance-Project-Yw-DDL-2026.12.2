"""生成财务勾稽和研报留出。金额使用 Decimal，缺项保留空值。"""
from decimal import Decimal as D
import argparse
import csv
from pathlib import Path

from extract_history import HERE, csv_write


def read_csv(folder, file):
    with (folder/file).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def derive(folder):
    original = read_csv(folder,"filing-cells.csv")
    raw = {(r["report"],r["metric"],r["column"]):D(r["raw_value"]) for r in original}
    loc = {(r["report"],r["metric"],r["column"]):r for r in original}

    def value(period,metric,column="本期"):
        return raw.get((period,metric,column))

    def data(period,column):
        return {m:value(period,m,column) for m in (
            "revenue","cost","surcharge","sales","admin","rd","reported_ebit","income_tax",
            "net_profit","parent_profit","cfo","capex","cash_taxes_all")}

    def calc(row):
        def net(keys):
            seen = [row.get(k) for k in keys]
            return seen[0]-sum(seen[1:]) if None not in seen else None
        rev,cost=row["revenue"],row["cost"]
        gross=net(("revenue","cost"))
        core=net(("revenue","cost","surcharge","sales","admin","rd"))
        return dict(gross=gross,gross_margin=gross/rev if None not in (gross,rev) and rev else None,
                    core_ebit=core,core_margin=core/rev if None not in (core,rev) and rev else None,
                    reported_minus_core=(
                        row["reported_ebit"]-core if None not in (row["reported_ebit"],core) else None),
                    minority_profit=net(("net_profit","parent_profit")),
                    cfo_less_capex=net(("cfo","capex")))

    def record(period,column):
        numbers=data(period,column)
        return dict(period=period,column=column,unit="人民币元（比率为小数）",**numbers,
                    **calc(numbers),input_scope="见 filing-cells.csv 同报告、列和指标",
                    label="原表及AgentCalculated")

    periods=list(dict.fromkeys(r["report"] for r in original))
    annual=[p for p in periods if p.endswith("-FY")]
    historic=[record(p,c) for p in periods for c in ("本期","比较")]
    for y in (2025,2026):
        for part,high,low in [("Q3","YTD9","H1"),("Q2","H1","Q1")]:
            if f"{y}-{high}" not in periods or f"{y}-{low}" not in periods:
                continue
            h,l=data(f"{y}-{high}","本期"),data(f"{y}-{low}","本期")
            numbers={k:h[k]-l[k] if None not in (h[k],l[k]) else None for k in h}
            historic.append(dict(period=f"{y}-{part}",column="本期相减",unit="人民币元（比率为小数）",
                                 **numbers,**calc(numbers),
                                 input_scope=f"{y}-{high}本期－{y}-{low}本期",label="AgentCalculated"))
    assert all(r["cfo_less_capex"] is not None for r in historic if r["period"].endswith("-FY"))
    assert next(r for r in historic if r["period"]=="2026-Q3")["revenue"]==D("601316609.49")
    csv_write(folder,"financial-bridge.csv",historic)

    # Stock balances are kept separately from cumulative and single-period flows.
    balance=[]
    for period in periods:
        for column in ("期末","上年末"):
            ar, inv, ap=(value(period,m,column) for m in ("ar","inventory","ap"))
            delta=ar+inv-ap if None not in (ar,inv,ap) else None
            balance.append(dict(report=period,column=column,ar=ar,inventory=inv,ap=ap,
                                trade_working_subset=delta,
                                note="应收账款+存货−应付账款，未含其他经营资产负债；见原表长期资本和租赁"))
    csv_write(folder,"working-capital.csv",balance)

    comparisons=[]
    for current,following in list(zip(annual,annual[1:]))+[
        ("2025-YTD9","2026-YTD9"),("2025-H1","2026-H1")]:
        for metric in sorted({r["metric"] for r in original}):
            is_balance=metric in ("ar","inventory","ap","fixed","cip","shares")
            if is_balance and "FY" not in current:
                continue
            a="期末" if is_balance else "本期"
            b="上年末" if is_balance else "比较"
            first=loc.get((current,metric,a))
            second=loc.get((following,metric,b))
            if first is None or second is None:
                continue
            old,new=D(first["raw_value"]),D(second["raw_value"])
            meaning = ("转增后每股基数变化，回看发行人重列说明" if metric=="eps" and old!=new
                       else "保证类质保费用重分类；2024年报p153" if current=="2023-FY" and metric in ("cost","sales") and abs(old-new)==D("4426692.62")
                       else "等值" if old==new else "可比版本差待核")
            comparisons.append(dict(period=current,metric=metric,original=old,later_comparison=new,
                                    difference=new-old,bridged_value=new if metric=="eps" or old==new or meaning.startswith("保证类") else None,
                                    original_source=first["source_id"],original_page=first["physical_page"],
                                    original_available=first["available"],original_sha=first["sha256"],
                                    comparative_source=second["source_id"],comparison_page=second["physical_page"],
                                    comparison_available=second["available"],comparison_sha=second["sha256"],
                                    unit=first["unit"],note=meaning))
    csv_write(folder,"restatement-bridge.csv",comparisons)

    product=read_csv(folder,"classification-cells.csv")
    index={(r["report"],r["table"],r["metric"],r["column"]):D(r["raw_value"]) for r in product}
    checks=[]
    for period in annual+["2025-H1","2026-H1"]:
        for kind,metric in (("收入","revenue"),("成本","cost")):
            for basis in ("本期","比较"):
                sub="营业收入和营业成本附注"
                part=lambda n:index.get((period,sub,n,basis+kind))
                parts=[part("主营业务"),part("其他业务")]
                if None in parts:
                    continue
                summed=sum(parts)
                target=value(period,metric,basis)
                allowed=D("0.01")
                assert target is not None and abs(summed-target)<=allowed,(period,kind,basis,summed,target)
                checks.append(dict(report=period,dimension="附注主营＋其他业务",column=basis,metric=kind,
                                   subtotal=summed,independent_total=target,residual=summed-target,
                                   independent_source="filing-cells.csv 合并利润表",label="AgentCalculated"))
            if period not in ("2024-FY","2025-FY"):
                continue
            for view in ("主营业务分产品情况","主营业务分地区情况","主营业务分销售模式情况"):
                detail=[v for (p,t,_,c),v in index.items() if p==period and t==view and c=="本期"+kind]
                target=index[(period,sub,"主营业务","本期"+kind)]
                assert detail and sum(detail)==target,(period,view,kind,sum(detail),target)
                checks.append(dict(report=period,dimension=view,column="本期",metric=kind,
                                   subtotal=sum(detail),independent_total=target,residual=sum(detail)-target,
                                   independent_source="classification-cells.csv 收入和成本附注",label="AgentCalculated"))
    csv_write(folder,"classification-check.csv",checks)


    old_base={r["period"]:r for r in read_csv(HERE.parent,"history.csv")}
    capital=[]
    balance_map={(r["report"],r["column"]):r["trade_working_subset"] for r in balance}
    for p in annual:
        row=next(x for x in historic if x["period"]==p and x["column"]=="本期")
        summary=old_base[p]
        for k,b in [("revenue","revenue"),("cost","cost"),("cfo_reported","cfo"),("cash_capex","capex")]:
            assert abs(D(summary[k])*D(10**6)-row[b])<D("0.05"),(p,k,summary[k],row[b])
        nopat=D(summary["nopat_proxy"])*D(10**6)
        da=D(summary["da"])*D(10**6) if summary["da"] else None
        wc=balance_map[(p,"期末")]
        old=balance_map[(p,"上年末")]
        delta=wc-old if None not in (wc,old) else None
        proxy=nopat+da-delta-row["capex"] if None not in (nopat,da,delta,row["capex"]) else None
        residual=proxy-row["cfo_less_capex"] if proxy is not None else None
        capital.append(dict(period=p,core_ebit_yuan=row["core_ebit"],income_tax_expense_yuan=row["income_tax"],
                            cash_paid_all_taxes_yuan=row["cash_taxes_all"],
                            assumed_operating_tax_yuan=row["core_ebit"]-nopat,
                            nopat_proxy_yuan=nopat,da_yuan=da,trade_wc_yuan=wc,trade_wc_change_yuan=delta,
                            ar_yuan=value(p,"ar","期末"),inventory_yuan=value(p,"inventory","期末"),
                            ap_yuan=value(p,"ap","期末"),fixed_yuan=value(p,"fixed","期末"),
                            cip_yuan=value(p,"cip","期末"),capex_cash_yuan=row["capex"],
                            fcff_proxy_before_lease_yuan=proxy,cfo_less_capex_yuan=row["cfo_less_capex"],
                            proxy_minus_cfo_less_capex=residual,frozen_history_source=summary["source_id"],
                            note="D&A、经营税代理取冻结年表，贸易营运资本使用本报告两列；残差含租赁／其他经营范围等未识别项"))
    csv_write(folder,"capital-and-cash-bridge.csv",capital)

    actual=next(r for r in historic if r["period"]=="2025-FY" and r["column"]=="本期")
    forecast=[]
    def add(firm,metric,prediction,observed,source,start,page,scope):
        predicted=D(prediction)*D(1_000_000)
        error=predicted-observed
        forecast.append(dict(firm=firm,published_as_of=start,metric=metric,predicted_yuan=predicted,
                             actual_yuan=observed,error_yuan=error,error_pct=100*error/observed,
                             forecast_location=page,forecast_source=source,actual_source="2025年报 p8、p27–28、p125–126",
                             scope=scope,state="AgentCalculated，原预测为外部预测"))
    z="https://pdf.dfcfw.com/pdf/H3_AP202310111601221123_1.PDF"
    h="https://www.sdyanbao.com/detail/870226"
    add("浙商","集团营业收入","2314",actual["revenue"],z,"2023-10-11","p1、p20，封面10月10日","三表百万元精度")
    add("浙商","集团营业收入","2310",actual["revenue"],z,"2023-10-11","p18","原报告正文舍入并保留旧回测")
    add("浙商","归母净利润","1267",actual["parent_profit"],z,"2023-10-11","p1、p20","百万元精度")
    add("浙商","合并净利润","1274",actual["net_profit"],z,"2023-10-11","p20","集团净利润，含少数股东损益")
    add("华创","集团营业收入","2145",actual["revenue"],h,"2025-04-08","p1、p23 图49","总收入")
    add("华创","归母净利润","1090",actual["parent_profit"],h,"2025-04-08","p1、p24","百万元精度")
    for kind,n in (("平面解决方案","1229"),("管材解决方案","511"),
                   ("三维解决方案","140"),("其他","265")):
        actual_cell=index[("2025-FY","主营业务分产品情况",kind,"本期收入")]
        add("华创",kind,n,actual_cell,h,"2025-04-08","p23 图49","按显示精度，其他桶范围待核，归并误差另计")
    csv_write(folder,"forecast-holdout.csv",forecast)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output",type=Path,default=HERE)
    derive(cli.parse_args().output)
