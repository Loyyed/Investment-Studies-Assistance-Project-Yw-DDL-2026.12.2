"""独立恢复桩段、显性 FCFF、终值和权益，另求价格临界点。"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
INPUTS=("docs/research17/valuation.json","docs/cases/688188/model.json",
        "companies/688188_柏楚电子/work/research14/calculation.json",
        "docs/cases/688188/operating.py","docs/cases/688188/inputs.json",
        "docs/cases/688188/reverse.csv","docs/long-atlas/688188/valuation-receipt.json")


def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))


def check(actual, expected, tolerance=1e-7):
    assert math.isclose(actual,expected,abs_tol=tolerance,rel_tol=0),(actual,expected)


def roots(fn,lower,upper,target):
    assert fn(lower)<target<fn(upper)
    for _ in range(74):
        mid=(lower+upper)/2
        if fn(mid)<target:
            lower=mid
        else:
            upper=mid
    return (lower+upper)/2


def valuation(case,security,actual,shift=0,margin=None,wc_share=.122):
    wacc=case["wacc"]
    terminal=case["terminal"]
    g,roi=terminal["growth"],terminal["incremental_return"]
    assert g<wacc and 0<g/roi<1
    m=terminal["margin"] if margin is None else margin
    first,*years=case["rows"]
    tax=first["cash_tax"]/first["operating_profit"]
    rev=first["revenue"]
    wc=max(actual["wc_subset_last_public"]*.91,rev*wc_share)
    stub_operating=(first["operating_profit"]-actual["actual_ebit"])*(1-tax)
    stub_da=first["depreciation"]-actual["actual_da_proxy"]
    stub_capex=first["cash_capex"]-actual["actual_capex"]
    stub_delta_wc=wc-actual["wc_subset_last_public"]
    stub_other_wc=first["extra_wc"]
    stub_lease=first["lease_cash"]-actual["lease_cash_actual"]
    # The non-leased Bochu base carries no incremental leased equipment.
    assert first["incremental_equipment_cash"]==0
    stub_cash=stub_operating+stub_da-stub_capex-stub_delta_wc-stub_other_wc-stub_lease
    explicit=[dict(year=first["year"], t=first["t"], undiscounted=stub_cash*actual["stub_fraction"])]
    flows=[]
    for row in years:
        fade=max(0,(row["year"]-2029)/(terminal["year"]-2029))
        driver=row["driver_1"]+shift*(1-fade)
        rev *= (1+driver)*(1+row["driver_2"])
        nopat=rev*(row["margin"]+fade*(m-terminal["margin"]))*(1-tax)
        new_wc=max(rev*wc_share,wc*.91)
        plant_cash=(row["cash_capex"]-row["depreciation"]+row["lease_cash"]
                    +row["incremental_equipment_cash"])*rev/row["revenue"]
        flows.append((row,rev,driver,nopat,plant_cash,new_wc-wc))
        wc=new_wc
    next_nopat=rev*(1+g)*m*(1-tax)
    terminal_cash=next_nopat*(1-g/roi)
    tail=next_nopat
    annual=[]
    for row,rev,driver,nopat,plant,delta_wc in reversed(flows):
        blend=max(0,(row["year"]-2029)/(terminal["year"]-1-2029))
        net=(plant+delta_wc)*(1-blend)+max(0,(tail-nopat)/roi)*blend
        annual.append(dict(year=row["year"],t=row["t"],revenue=rev,control_driver=driver,
                           nopat=nopat,plant_lease_net=plant,trade_wc_delta=delta_wc,
                           net_reinvestment=net,undiscounted=nopat-net))
        tail=nopat
    explicit.extend(reversed(annual))
    for row in explicit:
        row["pv"]=row["undiscounted"]/(1+wacc)**row["t"]
    terminal_pv=terminal_cash/(wacc-g)/(1+wacc)**explicit[-1]["t"]
    ev=sum(row["pv"] for row in explicit)+terminal_pv
    b=case["bridge"]
    excess=b["financial_cash"]+b["eligible_short_long_investments"]-b["working_cash_reserve"]-b["notified_buyback_cash_or_buffer"]
    bridge=excess-b["financial_debt"]-b["finance_treated_lease"]-b["non_controlling_deduction"]-b["litigation_separate_pv"]
    check(bridge,b["bridge_net"])
    equity=ev+bridge
    return dict(value=equity*1e6/security["shares"]/security["fx"],ev=ev,bridge=bridge,
                equity=equity,explicit_pv=ev-terminal_pv,terminal_pv=terminal_pv,
                terminal_share_of_ev=terminal_pv/ev,terminal_nopat=next_nopat,
                terminal_fcff=terminal_cash,terminal_reinvestment_rate=g/roi,
                stub=dict(operating=stub_operating,da=stub_da,capex=stub_capex,trade_wc=stub_delta_wc,
                          other_wc=stub_other_wc,lease=stub_lease,pre_proration=stub_cash,
                          proration=actual["stub_fraction"]),flows=explicit)


def run():
    stage=next(x for x in load(INPUTS[0]) if x["company"].startswith("688188"))
    published=load(INPUTS[1])
    case=stage["cases"]["base"]
    prev=load(INPUTS[2])["cases"]["base"]["rows"][0]
    market=stage["market"]
    cutoff=stage["price"]
    base=valuation(case,market,prev)
    check(base["value"],published["cases"]["base"]["per_share"],1e-11)
    check(base["terminal_pv"],case["terminal"]["pv"])
    check(base["stub"]["pre_proration"],case["rows"][0]["cash_remaining_after_statement"])
    for o,n in zip(case["rows"],base["flows"]):
        check(o["model_cash_after_date"],n["undiscounted"])
        check(o["present_value"],n["pv"])
    volume0=case["rows"][1]["driver_1"]
    search=(-.06,.08)
    v=roots(lambda x: valuation(case,market,prev,shift=x)["value"],*search,cutoff)
    m=roots(lambda x: valuation(case,market,prev,margin=x)["value"],.02,.8,cutoff)
    check(v,stage["critical_points"]["volume_reverse"]["roots"][0],1e-12)
    check(m,stage["critical_points"]["margin_threshold"],1e-12)
    vprice=valuation(case,market,prev,shift=v)["value"]
    mprice=valuation(case,market,prev,margin=m)["value"]
    cogs=stage["critical_points"]["turnover"][0]["cogs_ratio"]
    joint=[]
    for days in (15,30,45):
        wc=.122-cogs*days/365
        fn=lambda x: valuation(case,market,prev,shift=x,wc_share=wc)["value"]
        x=roots(fn,*search,cutoff)
        joint.append(dict(inventory_days_less=days,wc_share=wc,value_with_base_volume=fn(0),
                          control_growth_2027=volume0+x,root_shift=x,price=fn(x),residual=fn(x)-cutoff))
    return dict(window=stage["valuation_date"],market_close=cutoff,shares=market["shares"],wacc=case["wacc"],
                stable_growth=case["terminal"]["growth"],incremental_roic=case["terminal"]["incremental_return"],
                source_sha256={i:sha256((ROOT/i).read_bytes()).hexdigest() for i in INPUTS},
                frozen_value=published["cases"]["base"]["per_share"],
                difference=base["value"]-published["cases"]["base"]["per_share"],base=base,
                control=dict(root_growth_2027=volume0+v,base_growth_2027=volume0,shift=v,
                             search_shift=search,price=vprice,residual=vprice-cutoff,
                             fixed="稳定核心营业利润率、周转比例及其余冻结参数；2030起平移逐年退坡，2036归零"),
                margin=dict(root=m,search=(.02,.8),price=mprice,residual=mprice-cutoff,
                            fixed="控制量路径、周转比例及其余冻结参数；利润率调整自2030起逐步纳入"),
                inventory_and_volume=joint,status="AgentCalculated")


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output",type=Path,default=HERE/"valuation-reproduction.json")
    result=run()
    cli.parse_args().output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                                       encoding="utf-8",newline="\n")
    print(result["base"]["value"],result["control"],result["margin"])
