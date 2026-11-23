"""柏楚第二批逐年经营和估值。标准库运行，金额为百万元人民币。"""
import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE = HERE.parent
PRIOR = CASE / "deep-research-batch-1"
OUT = HERE / "data"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(name, content):
    (OUT / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_csv(name, records):
    with (OUT / name).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, records[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def select(records, **match):
    return next(r for r in records if all(r[k] == v for k, v in match.items()))


def mix(old, new, weight):
    return old + (new - old) * weight


def bounded(value):
    return min(1, max(0, value))


def main():
    OUT.mkdir(exist_ok=True)
    inputs = read_json(HERE / "assumptions.json")
    audit = read_json(PRIOR / "valuation-reproduction.json")
    original = read_json(CASE / "model.json")
    periods = rows(PRIOR / "financial-bridge.csv")
    volume = select(rows(CASE / "volume-and-stock.csv"), period="2025")
    groups = rows(CASE / "product-bridge.csv")
    annual = {year: select(periods, period=f"{year}-FY", column="本期") for year in range(2019, 2026)}
    actual = select(periods, period="2026-YTD9", column="本期")
    y25 = select(periods, period="2026-YTD9", column="比较")
    balances = rows(PRIOR / "working-capital.csv")
    working9 = select(balances, report="2026-YTD9", column="期末")
    wc9 = float(working9["trade_working_subset"])/1e6

    def ml(row, key):
        return float(row[key])/1e6

    anchor = inputs["cohort"]
    control_units = float(volume["control_units"])
    hardware_units = float(volume["hardware_units"])
    control_rev = sum(float(row["revenue_25"]) for row in groups[:3])
    hardware_rev = float(groups[-1]["revenue_25"]) * anchor["other_main_hardware_proxy"]
    residual_rev = ml(annual[2025], "revenue") - control_rev - hardware_rev
    control_price = control_rev / control_units
    head_price = hardware_rev / hardware_units
    season_base = ml(annual[2025], "revenue") - ml(y25, "revenue")
    season = season_base / ml(annual[2025], "revenue")
    last_day = date(2026, 12, 31)
    stub_t = (last_day - date.fromisoformat(inputs["date"])).days / 365
    stub_fraction = stub_t * 365 / 92
    rate = audit["wacc"]
    tax = inputs["cash_tax"]
    shares = inputs["shares"] / 1e6
    old = audit["base"]
    stage17 = read_json(CASE.parent.parent / "research17/688188/model.json")
    equity_items = stage17["cases"]["base"]["bridge"]
    signs = {"financial_cash": 1, "eligible_short_long_investments": 1, "working_cash_reserve": -1,
             "notified_buyback_cash_or_buffer": -1, "financial_debt": -1, "finance_treated_lease": -1,
             "non_controlling_deduction": -1, "litigation_separate_pv": -1}
    frozen_bridge = sum(equity_items[k]*sign for k, sign in signs.items())
    assert math.isclose(frozen_bridge, old["bridge"], abs_tol=1e-9)
    cash_original = read_json(HERE/"supplement.json")
    restricted_proxy = round(cash_original["monetary_funds_p5_yuan"]-cash_original["cash_equivalents_p12_yuan"],2)/1e6
    assert math.isclose(equity_items["financial_cash"]*1e6,cash_original["monetary_funds_p5_yuan"],abs_tol=.01)
    equity_items["cash_not_equivalent"] = restricted_proxy
    signs["cash_not_equivalent"] = -1
    equity_bridge = frozen_bridge - restricted_proxy

    def operating(rev, controls, heads, residual, c, year, stress_margin=0):
        # Three book-closed revenue groups. Head proxy denotes hardware already in the group.
        cogs = controls*(1-c["control_gm"]) + heads*(1-c["hardware_gm"]) + residual*(1-c["residual_gm"])
        sales = rev*c["sales_rate"]
        admin = rev*c["admin_rate"]
        rd = rev*c["rd_rate"]
        sur = rev*0.0115
        service = heads*c["addon_service"]
        runrate = (rev-cogs-sales-admin-rd-sur-service)/rev
        # Stable EBIT scenario changes normalized operating expenses. First affected FY is 2030.
        normalize = rev*stress_margin*bounded((year-2029)/6)
        return dict(revenue=rev,cost=cogs,sales=sales,admin=admin,research=rd,surcharge=sur,
                    incremental_service=service,normalized_operating_saving=normalize,
                    core_ebit=rev*runrate+normalize)

    def account(rec, c, year, prev_wc, prev_rev, prev_nopat, capital_add):
        rev, cost = rec["revenue"], rec["cost"]
        ar = rev*c["ar_days"]/365
        inv = cost*c["inventory_days"]/365
        ap = cost*c["ap_days"]/365
        other = rev*c["reserve_wc"]
        nwc = ar+inv-ap+other
        da = rev*c["da"]
        lease = rev*0.002
        nopat = rec["core_ebit"]*(1-tax)
        project = c["project_capex"][year-2027] if 2027 <= year <= 2029 else 0
        gross_capex = rev*c["capex"]+project
        delta_wc = nwc-prev_wc
        # Late explicit years converge to the same physical reinvestment as terminal.
        if year >= 2031:
            g = c["cash_growth"]
            reinvestment = max((nopat-prev_nopat)/c["incremental_roic"],
                               nopat*g/c["incremental_roic"])
            fade = (year-2030)/5
            normal_capex = max(da, da+reinvestment-delta_wc-lease)
            gross_capex = mix(gross_capex,normal_capex,fade)
        gross_capex += capital_add
        fcff = nopat + da - delta_wc - gross_capex - lease
        return dict(ar=ar,inventory=inv,ap=ap,other_nwc=other,nwc=nwc,delta_nwc=delta_wc,
                    cash_tax=rec["core_ebit"]*tax,nopat=nopat,da=da,lease_net_cash=lease,
                    cash_capex=gross_capex,project_cash_capex=project,fcff=fcff,
                    ebit_margin=rec["core_ebit"]/rev,revenue_growth=rev/prev_rev-1)

    def scenario(c, qty_shift=0, margin_shift=0, inventory_shift=0, extra_service=0):
        c = dict(c, inventory_days=c["inventory_days"]+inventory_shift,
                 addon_service=c["addon_service"]+extra_service)
        n26 = anchor["new_addressable_2025"]*(1+c["q4_new"])
        new26 = n26*anchor["new_fit_2025"]*anchor["new_win_2025"]
        repl26 = control_units*anchor["installed_exposure_multiple"]/anchor["replacement_cycle"]*c["renew"]
        q4_ratio = (new26+repl26)/control_units
        units = control_units*((1-season)*(1+c["ytd_unit_proxy"])+season*q4_ratio)
        q4_units = control_units*season*q4_ratio
        attach = anchor["attach_2025"]+c["attach_gain"]
        single0 = hardware_units - anchor["attach_2025"]*control_units
        head_units = q4_units*attach+single0*season*(1+c["single_rate"])
        q4_control = q4_units*control_price*(1+c["q4_net"])
        q4_head = head_units*head_price*(1+c["head_price"])
        q4_residual = residual_rev*season*(1+c["other_growth"])
        q4_revenue = q4_control+q4_head+q4_residual
        q4 = operating(q4_revenue,q4_control,q4_head,q4_residual,c,2026)
        actual_annual = {k: ml(actual, source) for k,source in {
            "revenue":"revenue","cost":"cost","sales":"sales","admin":"admin","research":"rd",
            "surcharge":"surcharge","core_ebit":"core_ebit"}.items()}
        rec26 = {k: q4[k]+actual_annual.get(k,0) for k in q4}
        old_actual = original["cases"]["base"]["rows"][0]
        known_capex = ml(actual,"capex")
        q4_da = (old_actual["depreciation"]-old["stub"]["da"])*q4_revenue/actual_annual["revenue"]
        q4_capex = q4_revenue*c["capex"]
        q4_lease = q4_revenue*.002
        wc_25 = float(select(balances,report="2025-FY",column="期末")["trade_working_subset"])/1e6
        # No known year-end balance at cutoff. Gradually rotate the Q3 inventory build.
        level = min(1, 0.4*min(1, max(0.3, 1.35-c["inventory_days"]/180)))
        full = account(rec26,c,2026,wc_25,ml(annual[2025],"revenue"),0,0)
        for item in ("ar","inventory","ap"):
            full[item] = mix(ml(working9,item),full[item],level)
        full["other_nwc"] *= level
        end_wc = full["ar"]+full["inventory"]-full["ap"]+full["other_nwc"]
        q4_cash = q4["core_ebit"]*(1-tax)+q4_da-q4_capex-q4_lease-(end_wc-wc9)
        annual_da = old_actual["depreciation"]-old["stub"]["da"]+q4_da
        annual_lease = ml(actual,"revenue")*.002+q4_lease
        full.update(nwc=end_wc,delta_nwc=end_wc-wc_25,da=annual_da,cash_capex=known_capex+q4_capex,
                    lease_net_cash=annual_lease)
        full["fcff"] = full["nopat"]+annual_da-full["delta_nwc"]-full["cash_capex"]-annual_lease
        first = dict(year=2026,**rec26,**full,valued_cash=q4_cash*stub_fraction,t=stub_t,
                      control_units=units,control_new=None,control_replacements=None,market_addressable=n26,
                      fit=anchor["new_fit_2025"],win=anchor["new_win_2025"],renew=c["renew"],
                      net_price_control_cny=(1+c["q4_net"])*control_price*1e6,attach=attach,
                      accepted_attached=None,head_single=None,hardware_units=None,
                      net_price_head_cny=(1+c["head_price"])*head_price*1e6,
                      control_revenue=None,hardware_revenue=None,residual_revenue=None,
                      arc_weld_increment=0,battery_laser_increment=0,precision_increment=0)
        hardware26 = hardware_units*(1-season)*(1+c["ytd_unit_proxy"]) + head_units
        implied_residual26 = rec26["revenue"]-units*control_price*(1+c["q4_net"])-hardware26*head_price*(1+c["head_price"])
        q4.update(full_residual_proxy=implied_residual26,control_units=q4_units,hardware_units=head_units,control_revenue=q4_control,
                  hardware_revenue=q4_head,residual_revenue=q4_residual,da_proxy=q4_da,capex=q4_capex,
                  lease_cash=q4_lease,opening_trade_wc=wc9,closing_modeled_wc=end_wc,
                  fcff_proxy=q4_cash,stub_fraction=stub_fraction,
                  control_price_cny=(1+c["q4_net"])*control_price*1e6,
                  hardware_price_cny=(1+c["head_price"])*head_price*1e6)
        path = [first]
        addressable, nfit, win = n26,anchor["new_fit_2025"],anchor["new_win_2025"]
        ctrl_price, hard_price = control_price*(1+c["q4_net"]),head_price*(1+c["head_price"])
        single = single0*(1+c["single_rate"])
        residual = mix(residual_rev*(1+c["other_growth"]),implied_residual26,c["residual_bridge_retention"])
        for year in range(2027,inputs["year_end"]+1):
            prev = path[-1]
            fade = bounded((year-2030)/5)
            lag = 1-fade
            g = c["cash_growth"]
            addressable *= 1+mix(c["new_growth"],g,fade)
            nfit = min(.91,nfit+c["fit_gain"]*lag)
            win = min(.77,max(.43,win+c["win_gain"]*lag))
            wins = addressable*nfit*win
            replacements = prev["control_units"]*anchor["installed_exposure_multiple"]/anchor["replacement_cycle"]*c["renew"]
            preliminary = wins+replacements+prev["control_units"]*qty_shift*lag
            delivered = mix(preliminary,prev["control_units"]*(1+g),fade)
            # Split constrained total between disjoint new and replacement pools.
            replacement_units = delivered*replacements/(wins+replacements)
            new_units = delivered-replacement_units
            attach = min(.86,attach+c["attach_gain"]*lag)
            # Stations scheduled in the year either pass the acceptance gate or slip. The
            # prior slipped cohort may return as a separate fulfillment entry once.
            planned_attach = delivered*attach
            accept = mix(c["acceptance"],1,fade)
            prior_slipped = path[-1].get("slipped_attachment",0)
            attached = planned_attach*accept + prior_slipped
            slipped = planned_attach*(1-accept)
            single *= 1+mix(c["single_rate"],g,fade)
            hardware = attached+single
            ctrl_price *= 1+c["control_price"]*lag
            hard_price *= 1+c["head_price"]*lag
            residual *= 1+mix(c["other_growth"],g,fade)
            ctrl, head = delivered*ctrl_price, hardware*hard_price
            rev = ctrl+head+residual
            if year == inputs["year_end"]:
                normalizer = prev["revenue"]*(1+g)/rev
                ctrl *= normalizer
                head *= normalizer
                residual *= normalizer
                ctrl_price *= normalizer
                hard_price *= normalizer
                rev = ctrl+head+residual
            rec = operating(rev,ctrl,head,residual,c,year,margin_shift)
            cap = account(rec,c,year,prev["nwc"],prev["revenue"],prev["nopat"],0)
            path.append(dict(year=year,**rec,**cap,valued_cash=cap["fcff"],t=year-2026+stub_t,
                 control_units=delivered,control_new=new_units,control_replacements=replacement_units,
                 market_addressable=addressable,fit=nfit,win=win,renew=c["renew"],
                 net_price_control_cny=ctrl_price*1e6,attach=attach,
                 accepted_attached=attached,head_single=single,hardware_units=hardware,
                 net_price_head_cny=hard_price*1e6,control_revenue=ctrl,hardware_revenue=head,
                 residual_revenue=residual,arc_weld_increment=0,battery_laser_increment=0,precision_increment=0,
                 slipped_attachment=slipped))
        return value(path,c,rate,equity_bridge,shares,q4,actual_annual)

    results = {n: scenario(c) for n,c in inputs["cases"].items()}
    base = results["base"]
    terminals = []
    for w in (rate-.01,rate,rate+.01):
        for g in (.013,.023,.029,.035):
            for roic in (.14,.235,.32):
                c=dict(inputs["cases"]["base"],cash_growth=g,incremental_roic=roic)
                rp=scenario(c)
                rr=value(rp["path"],c,w,equity_bridge,shares,rp["q4"],rp["actual_ytd9"])
                terminals.append(dict(wacc=w,g=g,incremental_roic=roic,price=rr["price"],
                                      terminal_share=rr["terminal_share"],retention=g/roic))

    grid = []
    audit_paths=[]
    for inv, service in ((25,.02),(0,0),(-25,-.006)):
        for delta in (-.04,-.02,0,.02,.04,.06,.08):
            f = lambda x: scenario(inputs["cases"]["base"],delta,x,inv,service)["price"]
            answer = solve(f,inputs["close"],-.12,.14)
            solved = answer["root"]
            b = scenario(inputs["cases"]["base"],delta,solved or 0,inv,service)
            grid.append(dict(inventory_days_shift=inv,add_on_service_shift=service,
                 control_new_shock_of_prior_units=delta,computed_2027_volume_growth=
                 b["path"][1]["control_units"]/b["path"][0]["control_units"]-1,
                 stable_margin_shift=solved,stable_core_ebit_margin=b["path"][-1]["ebit_margin"],
                 **answer))
            if solved is not None and delta==.06:
                audit_paths.append(dict(inventory_days_shift=inv,additional_service=service,margin_shift=solved,
                                        price=b["price"],terminal=b["stable_2036"],rates=[b["wacc"],b["growth"],b["roic"]],
                                        path=b["path"]))
    swing = {}
    for name,q,m,inv,service in (("up",.025,.02,-25,-.006),("down",-.025,-.02,25,.02)):
        x=scenario(inputs["cases"]["base"],q,m,inv,service)
        swing[name]=dict(price=x["price"],change=x["price"]-base["price"],shock_of_prior_units=q,
                         stable_ebit_shift=m,inventory_days_change=inv,extra_service_rate=service,
                         growth_2027=x["path"][1]["control_units"]/x["path"][0]["control_units"]-1,
                         stable_margin=x["path"][-1]["ebit_margin"])
    explicit_nopat = sum((row["nopat"]-oldrow["nopat"])/(1+rate)**row["t"]
                         for row,oldrow in zip(base["path"][1:],old["flows"][1:]))
    changes = [
        ("冻结基准",audit["frozen_value"]),("估值日后桩段",base["path"][0]["pv"]-old["flows"][0]["pv"]),
        ("显性期经营NOPAT",explicit_nopat),
        ("显性期净再投资",(base["explicit_pv"]-old["explicit_pv"])-
          (base["path"][0]["pv"]-old["flows"][0]["pv"])-explicit_nopat),
        ("终值路径",base["terminal_pv"]-old["terminal_pv"]),("同日WACC",0),
        ("货币资金与现金等价物差额",-restricted_proxy)]
    bridge = []
    total=0
    for i,(item,amount) in enumerate(changes):
        delta = amount if i==0 else amount/shares
        total+=delta
        bridge.append(dict(item=item,share_delta=delta,price_after=total))
    assert abs(total-base["price"])<1e-11

    equity = [dict(item=k,source_balance_m=equity_items[k],sign=v,delta_m=v*equity_items[k],
                   delta_per_share=v*equity_items[k]/shares,
                   locator=("2026Q3 p5与p12；2026H1 p137与p154旁证" if k=="cash_not_equivalent" else
                            "2026Q3 p5、p7；阶段17权益桥与留存假设")) for k,v in signs.items()]
    receipts={"ancestor":"f354d3c65baabc77e8760c3bf277ca10d7d75755","date":inputs["date"],
              "market":inputs["close"],"wacc":rate,"shares":inputs["shares"],
              "frozen_baseline":audit["frozen_value"],"frozen_roots":[audit["control"],audit["margin"]],
              "cash_bridge":equity_bridge,"major_changes":swing,"q4_25":season_base,"q4_25_weight":season,
              "anchors":dict(control_2025=control_units,hardware_2025=hardware_units,historical_control_group_revenue=control_rev,
                 assigned_hardware_2025=hardware_rev,residual= residual_rev,control_unit_proxy_yuan=control_price*1e6,
                 hardware_unit_proxy_yuan=head_price*1e6,actual_2026_nwc9=wc9),
              "input_sha256":{f.relative_to(CASE).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in
                 [HERE/"assumptions.json",HERE/"supplement.json",CASE/"model.json",CASE/"volume-and-stock.csv",CASE/"product-bridge.csv",
                  PRIOR/"financial-bridge.csv",PRIOR/"working-capital.csv",PRIOR/"valuation-reproduction.json"]}}
    write_csv("forecast.csv",[dict(scenario=n,**row) for n,c in results.items() for row in [
        {**c["path"][0],"slipped_attachment": None},*c["path"][1:]]])
    write_csv("value-bridge.csv",bridge)
    write_csv("equity-bridge.csv",equity)
    write_csv("price-contours.csv",grid)
    write_csv("terminal-sensitivity.csv",terminals)
    dump("model.json",dict(receipt=receipts,scenarios=results))
    dump("price-witnesses.json",audit_paths)
    print({n:round(x["price"],6) for n,x in results.items()})


def solve(function, target, lo, hi):
    low, high = function(lo), function(hi)
    if (low-target)*(high-target)>0:
        return dict(root=None,reprice=None,residual=None,lower=lo,upper=hi,lower_price=low,upper_price=high)
    a,b=lo,hi
    for _ in range(64):
        x=(a+b)/2
        if (function(x)-target)*(low-target)>0:
            a=x
        else:
            b=x
    root=(a+b)/2
    price=function(root)
    return dict(root=root,reprice=price,residual=price-target,lower=lo,upper=hi,lower_price=low,upper_price=high)


def value(path, c, w, equity, shares, q4, actual):
    g, roic=c["cash_growth"],c["incremental_roic"]
    assert 0 < g < w and roic > g
    projected=[dict(row,pv=row["valued_cash"]/(1+w)**row["t"]) for row in path]
    pv=sum(row["pv"] for row in projected)
    end=path[-1]
    terminal_nopat=end["nopat"]*(1+g)
    reinvestment=terminal_nopat*g/roic
    fcff=terminal_nopat-reinvestment
    terminal_pv=fcff/(w-g)/(1+w)**end["t"]
    ev=pv+terminal_pv
    return dict(price=(ev+equity)/shares,explicit_pv=pv,terminal_pv=terminal_pv,
                terminal_share=terminal_pv/ev,enterprise_value=ev,equity_value=ev+equity,terminal_fcff=fcff,
                stable_2036=dict(year=2036,revenue=end["revenue"]*(1+g),core_ebit=end["core_ebit"]*(1+g),
                                 nopat=terminal_nopat,reinvestment=reinvestment,fcff=fcff,retention=g/roic),
                growth=g,roic=roic,wacc=w,q4=q4,actual_ytd9=actual,path=projected)


if __name__ == "__main__":
    main()
