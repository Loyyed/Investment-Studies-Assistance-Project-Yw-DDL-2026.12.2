"""Recompute two cases' supplementary operating and price grids from portable inputs."""
from collections import defaultdict
from pathlib import Path
import csv
import json
from statistics import mean

HERE = Path(__file__).resolve().parent
CODE = HERE.name
BASE = HERE.parent.parent / "research17" / CODE / "model.json"
U = 1_000_000


def csv_table(name, rows):
    cols = list(dict.fromkeys(k for row in rows for k in row))
    with (HERE / (name + ".csv")).open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=cols, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def symmetric(first, second):
    old, new = first["revenue_m"], second["revenue_m"]
    delta = second["gross_m"] - first["gross_m"]
    old_rate, new_rate = first["margin"], second["margin"]
    scale = (new - old) * mean([old_rate, new_rate])
    rate = (new_rate - old_rate) * mean([new, old])
    assert abs(scale + rate - delta) < 1e-8
    return scale, rate


def volumes_bridge(code_input, dimension_rows):
    results = []
    volumes = {r["period"]: r["quantities"] for r in code_input["volumes"]}
    products = defaultdict(lambda: {"revenue_m": 0., "cost_m": 0.})
    for row in dimension_rows:
        if row["view"] != "产品":
            continue
        key = row["period"], row["dimension"]
        products[key]["revenue_m"] += row["revenue_m"]
        products[key]["cost_m"] += row["cost_m"]
    units = []
    for (period, product), amounts in products.items():
        if product not in volumes.get(period, {}):
            continue
        tonnes = volumes[period][product]
        r, c = amounts.values()
        units.append(dict(period=period, product=product, tonnes=tonnes, revenue_m=r, cost_m=c,
                          asp=r*U/tonnes, unit_cost=c*U/tonnes, unit_gross=(r-c)*U/tonnes,
                          tag="算术；每吨同族组均价含结构，不能解释单SKU提价"))
    unit_map = {(r["period"], r["product"]): r for r in units}
    for row in units:
        prev = str(int(row["period"][:4])-1) + row["period"][4:]
        old = unit_map.get((prev, row["product"]))
        if not old:
            continue
        quantity = (row["tonnes"]-old["tonnes"])*mean([old["asp"],row["asp"]])/U
        price_mix = (row["asp"]-old["asp"])*mean([old["tonnes"],row["tonnes"]])/U
        gross_qty = (row["tonnes"]-old["tonnes"])*mean([old["unit_gross"],row["unit_gross"]])/U
        gross_asp = price_mix
        gross_unit_cost = -(row["unit_cost"]-old["unit_cost"])*mean([old["tonnes"],row["tonnes"]])/U
        assert abs(row["revenue_m"]-old["revenue_m"]-quantity-price_mix) < 1e-8
        assert abs((row["revenue_m"]-row["cost_m"])-(old["revenue_m"]-old["cost_m"])-gross_qty-gross_asp-gross_unit_cost) < 1e-8
        results.append(dict(period=row["period"],prior=prev,product=row["product"],quantity_delta_m=quantity,
                            asp_mix_delta_m=price_mix,gross_quantity_delta_m=gross_qty,
                            gross_asp_mix_delta_m=gross_asp,gross_unit_cost_delta_m=gross_unit_cost,
                            method="Q×P中点分配交互；每吨成本含材料、人工、动力等"))
    return units, results


def build_dimensions(src):
    rows = []
    grouped = defaultdict(lambda: [0.,0.])
    for r in src["dimensions"]:
        revenue, cost = float(r["revenue_yuan"])/U, float(r["cost_yuan"])/U
        view = "产品×渠道" if CODE == "002507" else r["view"]
        dim = r["product"] + " / " + r["channel"] if CODE == "002507" else r["dimension"]
        rows.append(dict(period=r["period"],view=view,dimension=dim,revenue_m=revenue,cost_m=cost,gross_m=revenue-cost,
                         margin=1-cost/revenue,source_id=r.get("source_id"),page=r["page"],url=r["url"],column=r["column"]))
        if CODE == "002507":
            for v,name in [("产品",r["product"]),("渠道",r["channel"])]:
                totals=grouped[(r["period"],v,name)]
                totals[0]+=revenue
                totals[1]+=cost
    for (period,view,dim),(r,c) in grouped.items():
        rows.append(dict(period=period,view=view,dimension=dim,revenue_m=r,cost_m=c,gross_m=r-c,margin=1-c/r,
                         column="同一原表交叉行加总"))
    return rows


def reconcile(src, dimensions):
    groups = defaultdict(lambda: [0.,0.])
    for r in dimensions:
        group = groups[r["period"],r["view"]]
        group[0]+=r["revenue_m"]
        group[1]+=r["cost_m"]
    periods = {r["period"]: r["values"] for r in src["annual"]}
    periods.update({r["period"]:r["cumulative"] for r in src["interim"] if r["period"].endswith("H1")})
    rows = []
    for (period,view),(vr,vc) in groups.items():
        report=periods[period]
        rows.append(dict(period=period,view=view,revenue_m=vr,cost_m=vc,
                         consolidated_revenue_m=report["revenue"],consolidated_cost_m=report["cost"],
                         residual_revenue_m=report["revenue"]-vr,residual_cost_m=report["cost"]-vc,
                         scope="主营视图内加总；对账差额单列，视图间重叠"))
    return rows


def cash_and_capital(src):
    rows = []
    prior = None
    for row in src["annual"]:
        v, d = row["values"], row["derived"]
        prior_wc, wc = prior["derived"].get("ncwc_trade_only") if prior else None, d.get("ncwc_trade_only")
        delta = wc - prior_wc if prior_wc is not None and wc is not None else None
        fields = {
            "period":row["period"],"source_id":row["source_id"],"revenue_m":v.get("revenue"),
            "gross_profit_m":v.get("revenue")-v.get("cost") if "revenue" in v and "cost" in v else None,
            "sales_m":v.get("sales"),"admin_m":v.get("admin"),"research_m":v.get("research"),
            "surcharges_m":v.get("tax_surcharge"),"reported_operating_profit_m":v.get("operating_profit"),
            "finance_reported_m":v.get("finance"),"analysis_ebit_m":d.get("adjusted_ebit"),
            "reported_income_tax_rate_proxy":d.get("report_cash_tax_proxy"),
            "analysis_ebit_tax_proxy_m":(d["adjusted_ebit"]-d["nopat_proxy"]) if d.get("adjusted_ebit") is not None and d.get("nopat_proxy") is not None else None,
            "nopat_proxy_m":d.get("nopat_proxy"),
            "da_m":d.get("depreciation_and_amortization"),"wc_end_m":wc,"wc_delta_m":delta,
            "capex_cash_m":v.get("capex"),"cfo_reported_m":v.get("cfo"),
            "cfo_minus_capex_m":d.get("cfo_less_cash_capex"),"lease_adjustment_m":None,
            "capital_subset_m":d.get("operating_capital_subset"),"roic_subset":d.get("store_roic_proxy"),
            "incremental_return_subset":d.get("incremental_return_proxy"),
        }
        da, np, cx = fields["da_m"], fields["nopat_proxy_m"], fields["capex_cash_m"]
        fields["fcff_before_lease_proxy_m"]=np+da-delta-cx if all(z is not None for z in [np,da,delta,cx]) else None
        fields["cfo_cash_proxy_minus_ebit_path_m"]=(fields["cfo_minus_capex_m"]-fields["fcff_before_lease_proxy_m"]
            if fields["cfo_minus_capex_m"] is not None and fields["fcff_before_lease_proxy_m"] is not None else None)
        label="期间现金税与租赁历史不可识别；NOPAT/经营营运和资本子集代理；CFO路径不再扣营运变动"
        fields["scope"]=label
        rows.append(fields)
        prior = row
    return rows


def frozen_value(case, shares, wacc, terminal_fcff=None):
    terminal=case["terminal"]
    if terminal_fcff is None:
        terminal_fcff=terminal["fcff"]
    explicit = sum(r["model_cash_after_date"]/(1+wacc)**r["t"] for r in case["rows"])
    t=case["rows"][-1]["t"]
    pv = terminal_fcff/(wacc-terminal["growth"])/(1+wacc)**t
    return (explicit+pv+case["bridge"]["bridge_net"])/shares


def fuling(src, dims, m):
    v={(r["period"],r["view"],r["dimension"]):r for r in dims}
    current, previous = v["2026-H1","渠道","直销"], v["2025-H1","渠道","直销"]
    gp=current["gross_m"]-previous["gross_m"]
    assert abs(gp-21.0876555)<1e-8
    acc={r["period"]:r["cumulative"] for r in src["interim"]}
    fee=acc["2026-H1"]["sales"]-acc["2025-H1"]["sales"]
    delta=current["revenue_m"]-previous["revenue_m"]
    margins={kind:[] for kind in ("direct_threshold","plant_utilization","capital_overlay")}
    for fee_share in (.25,.35,.50,.60):
        for days in (0,30,60,90):
            for inv_capex_m in (0,5,10):
                returns_m=.01*delta
                receivable_m=delta*days/182.5
                ceiling=gp-returns_m-receivable_m-inv_capex_m
                margins["direct_threshold"].append(dict(fee_share_of_group_delta=fee_share, days=days,
                    assumed_residual_returns_m=returns_m, net_inventory_capex_m=inv_capex_m, gross_gain_m=gp,
                    expense_ceiling_m=ceiling, fee_buffer_m=ceiling-fee_share*fee,
                    cash_surplus_m=ceiling-fee_share*fee, ceiling_days_at_fixed_other_terms=(gp-returns_m-inv_capex_m-fee_share*fee)*182.5/delta,
                    note="半年回款代理；退换条件只计未进净收入的额外实际损失"))
    project=src["project"]
    cash_per_tonne=18117.688015*.35
    for utilization in (.35,.55,.75):
        for substitute in (.5,.65,.8):
            production=project["design_tonnes"]*utilization
            existing=production*substitute
            addition=production-existing
            for saved_per_ton in (0,500,1000):
                saved=existing*saved_per_ton/U
                annual_cash=addition*cash_per_tonne/U-100+saved
                margins["plant_utilization"].append(dict(utilization=utilization,replacement=substitute,
                    design_capacity_tonnes=project["design_tonnes"],production_tonnes=production,old_line_displaced_tonnes=existing,
                    market_incremental_tonnes=addition,cash_per_new_tonne=cash_per_tonne,annual_fixed_and_maint_m=100,
                    assumed_old_line_savings_per_tonne=saved_per_ton,old_line_cash_savings_m=saved,
                    annual_pretax_cash_before_working_capital_and_growth_capex_m=annual_cash,
                    annual_observed_utilization_breakeven=(100*U)/(project["design_tonnes"]*((1-substitute)*cash_per_tonne+substitute*saved_per_ton))))
    base=m["cases"]["base"]
    shares=m["market"]["shares"]/U
    undisclosed_2026=base["rows"][0]["cash_capex"]-base["rows"][0]["disclosed_cash_capex"]
    probable=project["committed_m"]-project["used_lifetime_m"]-undisclosed_2026-sum(r["cash_capex"] for r in base["rows"] if r["year"] in (2027,2028,2029))
    # Reserve the actual group cash capex in the frozen horizon when making the overlay.
    for fraction in (0,.5,1):
        adjustment=sum(probable*fraction*f/(1+base["wacc"])**(i+base["rows"][0]["t"])
                       for i,f in [(1,.5),(2,.3),(3,.2)])
        margins["capital_overlay"].append(dict(conditional_remaining_cash_claim_m=probable,
            fraction_treated_as_unembedded=fraction, cash_capex_2026_remaining_m=undisclosed_2026,
            value_drag_per_share=adjustment/shares, conditional_value_per_share=base["per_share"]-adjustment/shares,
            rule="50/30/20三年现金；金额边界含H1至Q3未单列基地结算与承诺口径差异，不当作实际欠款"))
    h1_split=[]
    for row in dims:
        if row["period"] == "2026-H1" and row["view"] == "产品×渠道":
            old=v["2025-H1",row["view"],row["dimension"]]
            sc,ra=symmetric(old,row)
            h1_split.append(dict(dimension=row["dimension"],revenue_change_m=row["revenue_m"]-old["revenue_m"],
                                 gross_change_m=row["gross_m"]-old["gross_m"],revenue_scale_gross_effect_m=sc,
                                 within_cell_margin_gross_effect_m=ra,formula="收入变化×平均毛利率 + 毛利率变化×平均收入"))
    margins["channel_attribution"]=h1_split
    margin_target=m["critical_points"]["market_case"]["margin"]["roots"][0]
    margins["current_price_bridge"]=[dict(stage17_required_ebit_margin=margin_target,
        stage17_required_stable_fcff_m=m["critical_points"]["market_case"]["normalized_fcff_if_margin_root"],
        capital_overlay_headwind_per_share=margins["capital_overlay"][-1]["value_drag_per_share"],
        allowed_extra_terminal_cash_loss_m=(base["per_share"]-m["price"])*shares*(base["wacc"]-base["terminal"]["growth"])
            *(1+base["wacc"])**base["rows"][-1]["t"],
        note="只改终值FCFF的独立边界；全路径利润率反解另见模型")]
    return margins


def angel(src,m):
    base=m["cases"]["base"]
    shares=m["market"]["shares"]/U
    terminal=base["terminal"]
    out={"project_bridge":[],"capex_and_roic":[], "project_unit_requirements":[], "current_price_bridge":[]}
    for p in src["projects"]:
        v = dict(p)
        if "h1_eop_cip_m" in p:
            change=sum(x or 0 for x in [p["bop_cip_m"],p["h1_addition_m"]])-(p["h1_transfer_m"] or 0)
            assert abs(change-p["h1_eop_cip_m"])<1e-6
            v["opening_plus_additions_less_transfer_m"]=change
            v["ending_cip_to_budget"]=change/p["budget_m"]
        out["project_bridge"].append(v)
    for wacc in (.06,.065,.07,.0725,.075,.0775,.08):
        for roi in (.08,.10,.112,.11755,.13,.15,.18):
            term_cash=terminal["nopat"]*(1-terminal["growth"]/roi)
            price=frozen_value(base,shares,wacc,term_cash)
            out["capex_and_roic"].append(dict(wacc=wacc,terminal_incremental_roic=roi,terminal_fcff_m=term_cash,
                price_cny=price,market_gap_cny=price-m["price"],tag="条件估值；固定显式规划，只变稳定再投资与折现",
                term_pv=term_cash/(wacc-terminal["growth"])/(1+wacc)**base["rows"][-1]["t"]))
    for wacc in (.06,.07,.0725,.075,.0775,.08):
        no_terminal=frozen_value(base,shares,wacc,0)
        target_cash=(m["price"]-no_terminal)*shares*(wacc-terminal["growth"])*(1+wacc)**base["rows"][-1]["t"]
        inverse=(1-target_cash/terminal["nopat"])
        roe=terminal["growth"]/inverse if inverse>0 else None
        round_trip=(frozen_value(base,shares,wacc,terminal["nopat"]*(1-terminal["growth"]/roe))
            if roe and roe>terminal["growth"] else None)
        if round_trip is not None:
            assert abs(round_trip-m["price"])<1e-8
        root_in_bounds=roe is not None and .08 <= roe <= .18
        out["current_price_bridge"].append(dict(wacc=wacc,required_stable_cash_m=target_cash,
            root_in_bounds=root_in_bounds,terminal_incremental_roic_inverse=roe if root_in_bounds else None,
            diagnostic_outside_interval=roe if not root_in_bounds else None,recovered_share_price=round_trip if root_in_bounds else None,
            market_price=m["price"],low_roic=0.08,high_roic=0.18,
            lower_boundary_price=frozen_value(base,shares,wacc,terminal["nopat"]*(1-terminal["growth"]/.08)),
            upper_boundary_price=frozen_value(base,shares,wacc,terminal["nopat"]*(1-terminal["growth"]/.18)),
            scope='固定显式年FCFF及NOPAT；搜索区间0.08–0.18，外推仅显示边界'))
    for p in src["projects"]:
        if p['name'] not in ('印尼2万吨酵母','宜昌2万吨酵母蛋白复配线','酵母蛋白1.1万吨示范线'):
            continue
        for qualified in (.5,.75,.9):
            for utilization in (.7,.85,1.):
                for wc in (0,30,60):
                    saleable=p["design_tonnes"]*qualified*utilization
                    investment=p["budget_m"]+wc
                    returns=.11754713611445602
                    amount=investment*returns
                    out["project_unit_requirements"].append(dict(project=p["name"],qualification_saleable_share=qualified,
                        utilization=utilization,saleable_tonnes=saleable,finance_wc_m=wc,
                        incremental_investment_m=investment,stable_project_nopat_needed_m=amount,
                        required_pretax_ebit_per_tonne=amount*U/(.785*saleable),
                        relation="阶段17固定7.50% WACC的ROIC临界11.7547%作厂级诊断；吨EBIT已需扣折旧、人工、能源及销售归属"))
    return out


def build():
    src=json.loads((HERE / "operating-inputs.json").read_text(encoding="utf-8"))
    model=json.loads(BASE.read_text(encoding="utf-8"))
    assert src["as_of"][:10] == model["valuation_date"]
    dimensions=build_dimensions(src)
    units, prices=volumes_bridge(src,dimensions)
    attributes={"dimension_panel":dimensions,"views_reconciliation":reconcile(src,dimensions),
                "unit_economics":units,"unit_price_volume_bridge":prices,"cash_capital":cash_and_capital(src)}
    cost=[]
    for part in src["cost_slices"]:
        for k,(current,old) in part["amounts"].items():
            cost.append(dict(period=part["period"],prior=part["prior"],scope=part["section"],kind=k,
                             current_m=current/U,prior_m=old/U,effect_on_gross_m=(old-current)/U,
                             source_id=part["source_id"],url=part["url"],page=part["page"],
                             kind_includes_transport_in_cogs="是，若披露；渠道现金不重复扣"))
    attributes["cost_bridge"]=cost
    excluded=[]
    named={"finance","other_income","investment","fair_value","credit","impairment","disposal"}
    for bridge in src["reported_profit_bridge"]:
        for r in bridge["steps"]:
            if r["metric"] in named:
                excluded.append(dict(metric=r["metric"], prior_reported_m=r["start_input"],
                     current_reported_m=r["end_input"], consumption_sign_in_report_ebit=r["sign"],
                     current_report_to_analysis_adjustment_m=-float(r["end_input"])*r["sign"],
                     reason="合并分析EBIT重建为收入减营业成本、税金及三项经营费用；本表只解释报告利润到分析利润，与费用桥不叠加"))
    actual=next(r for r in attributes["cash_capital"] if r["period"]=="2025-FY")
    residual=actual["analysis_ebit_m"]-actual["reported_operating_profit_m"]-sum(r["current_report_to_analysis_adjustment_m"] for r in excluded)
    excluded.append(dict(metric="unallocated_report_profit_difference",current_report_to_analysis_adjustment_m=residual,reason="保留未分配的其它报表行或取整，不归给核心效率"))
    attributes["ebit_adjustments"]=excluded
    for name,c in model["cases"].items():
        price=frozen_value(c,model["market"]["shares"]/U,c["wacc"])
        assert abs(price-c["per_share"])<1e-8, (name,price,c["per_share"])
    attributes.update(fuling(src,dimensions,model) if CODE == "002507" else angel(src,model))
    return attributes


if __name__ == "__main__":
    tables=build()
    for name, rows in tables.items():
        csv_table(name.replace("_","-"),rows)
    (HERE / "operating-analysis.json").write_text(json.dumps(tables,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    print(f"{CODE}: {len(tables)} tables, {sum(map(len,tables.values()))} rows")
