"""Rebuild ISRG primary-source bridges and isolated reversal checks.

USD millions except per-share, procedure yield and unit counts. Financial model
inputs and stage 17 results remain frozen in docs/research17/US/model.json.
"""
import csv
import json
import math
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(filename):
    return json.loads(filename.read_text(encoding="utf-8"))


def write_csv(filename, rows):
    fields = list(dict.fromkeys(name for row in rows for name in row))
    with filename.open("w", encoding="utf-8-sig", newline="") as handle:
        out = csv.DictWriter(handle, fieldnames=fields)
        out.writeheader()
        out.writerows(rows)


def close(a, b, tol=1e-8):
    assert math.isclose(a, b, rel_tol=tol, abs_tol=tol), (a, b)


def revenue_views(inputs):
    raw = inputs["quarter_revenue"]
    parents = []
    for idx, period in enumerate(inputs["columns_quarter"]):
        d = {key: value[idx] for key, value in raw.items()}
        parents.append(dict(period=period, kind="披露列", **d))
    for period, end, start in (("2026H1", 2, 0), ("2025H1", 3, 1)):
        parents.append(dict(period=period, kind="累计减单季", **{
            key: value[end] - value[start] for key, value in raw.items()
        }))
    views = []
    for d in parents:
        us = sum(d[f"us_{line}"] for line in ("instruments", "systems", "services"))
        ous = sum(d[f"ous_{line}"] for line in ("instruments", "systems", "services"))
        instruments = d["us_instruments"] + d["ous_instruments"]
        services = d["us_services"] + d["ous_services"]
        systems = d["us_systems"] + d["ous_systems"]
        operating = d["systems_operating_lease"]
        vari = d["operating_variable"]
        buyout = d["systems_buyout_rounded"]
        sales_type = d["systems_sales_type_lease"]
        difference = systems - operating - buyout - sales_type
        close(us + ous, d["total_reported"])
        close(instruments + services + difference + buyout + sales_type + operating, d["total_reported"])
        views.append(dict(**d, us_total=us, ous_total=ous, instruments_total=instruments,
                          services_total=services, systems_total=systems, lease_fixed_proxy=operating-vari,
                          systems_direct_residual=difference, recurring_share=(instruments+services+operating)/d["total_reported"]))
    return views


def drivers(inputs):
    rows = inputs["annual"]
    result = []
    for row in rows:
        new = dict(row)
        procedure_count = row["da_vinci_proc"] + row["ion_proc"]
        installed_average = (row["da_vinci_open"] + row["da_vinci_close"]) / 2
        new["combined_procedures"] = procedure_count
        new["instruments_per_combined_case_usd"] = row["instruments"] * 1e6 / procedure_count
        new["dv_procedures_per_average_installed"] = row["da_vinci_proc"] / installed_average
        new["systems_direct_and_buyouts_residual"] = row["systems"] - row["operating_lease"] - row["sales_type_lease"]
        new["systems_fixed_proxy"] = row["operating_lease"] - row["variable_lease_rounded"]
        new["consolidated_gross"] = row["revenue"] - row["product_cogs"] - row["service_cogs"]
        new["product_gm"] = 1 - row["product_cogs"] / (row["instruments"] + row["systems"])
        new["service_gm"] = 1 - row["service_cogs"] / row["services"]
        close(new["consolidated_gross"] - row["sga"] - row["rnd"], row["ebit"])
        close(row["us"] + row["ous"], row["revenue"])
        new["cfo_after_ppe_only"] = row["cfo"] + row["cash_ppe"]
        result.append(new)
    midpoints = []
    for a,b in zip(result,result[1:]):
        q0, q1 = a["combined_procedures"], b["combined_procedures"]
        p0, p1 = a["instruments_per_combined_case_usd"], b["instruments_per_combined_case_usd"]
        quantity = (q1-q0)*(p1+p0)/2e6
        yield_mix = (p1-p0)*(q1+q0)/2e6
        dv_volume_same_mix = (b["da_vinci_proc"]-a["da_vinci_proc"])*(p1+p0)/2e6
        ion_volume_same_mix = (b["ion_proc"]-a["ion_proc"])*(p1+p0)/2e6
        close(quantity, dv_volume_same_mix + ion_volume_same_mix)
        close(quantity + yield_mix, b["instruments"] - a["instruments"])
        midpoints.append(dict(period=f"{a['period']}→{b['period']}", revenue_change=b["instruments"]-a["instruments"],
                              volume_at_mean_realization=quantity, da_vinci_vol_common_yield=dv_volume_same_mix,
                              ion_vol_common_yield=ion_volume_same_mix, realization_and_mix=yield_mix))
    return result, midpoints


def profit_cash_bridge(inputs, revenue):
    cfg = inputs["forecast_context"]
    tax = cfg["tax_rate_operating_proxy"]
    records = []
    fields = inputs["quarter_profit"]
    for i, r in enumerate(revenue[:4]):
        d = {key: values[i] for key, values in fields.items()}
        product_rev = r["instruments_total"] + r["systems_total"]
        gross = product_rev + r["services_total"] - d["product_cogs"] - d["service_cogs"]
        ebit = gross - d["sga"] - d["rnd"] - d["settlement_charge_expense"]
        close(ebit, d["ebit_reported"])
        normalized = ebit + d["settlement_charge_expense"] - d["tariff_refund_benefit"]
        rec = dict(period=r["period"], **d, gross_profit=gross,
                   product_gross_margin=1 - d["product_cogs"]/product_rev,
                   service_gross_margin=1 - d["service_cogs"]/r["services_total"],
                   ebit_normalized=normalized, operating_cash_tax_proxy=normalized*tax,
                   normalized_nopat_proxy=normalized*(1-tax))
        if r["period"] in inputs["ytd_cash"]:
            cash = inputs["ytd_cash"][r["period"]]
            nc = sum(cash[k] for k in ("ar_cf", "inventory_cf", "prepaids_other_assets_cf", "ap_cf", "comp_cf", "def_revenue_cf", "other_liabilities_cf"))
            noncash = sum(cash[k] for k in ("ppe_depreciation_and_disposal", "amortization", "investment_results", "business_gain", "deferred_tax", "sbc"))
            close(cash["net_income"] + nc + noncash, cash["cfo"])
            # Settled in periods unknown. CFO sensitivity assumes the entire settlement charge
            # is offset in the reported liability subtotal. Positive adjustment removes accrual.
            working_cash_before_litigation = nc - d["settlement_charge_expense"]
            da = cash["ppe_depreciation_and_disposal"] + cash["amortization"]
            operating_cf_proxy = normalized*(1-tax) + da + working_cash_before_litigation
            rec.update(**cash, operating_asset_liability_cash_change=nc, total_noncash_cf=noncash,
                       other_liabs_ex_settlement_if_full= cash["other_liabilities_cf"]-d["settlement_charge_expense"],
                       working_cash_ex_settlement_if_full=working_cash_before_litigation,
                       da_including_disposals_proxy=da, operating_cf_proxy=operating_cf_proxy,
                       fcff_proxy_before_residual_tax_allocation=operating_cf_proxy+cash["cash_ppe"],
                       reported_cfo_less_cash_ppe=cash["cfo"]+cash["cash_ppe"],
                       cfo_less_cash_ppe_sbc_proxy=cash["cfo"]+cash["cash_ppe"]-cash["sbc"],
                       cfo_vs_operating_cf_proxy_residual=cash["cfo"]-operating_cf_proxy)
        records.append(rec)
    return records


def lease_cash(inputs, revenue):
    cfg = inputs["forecast_context"]
    stock = inputs["period_stock"]
    actual = []
    for year in (2025,2026):
        d = next(row for row in revenue if row["period"] == f"{year}YTD9")
        s = stock[f"{year}-09-30"]
        for contract, rev in (("fixed",d["lease_fixed_proxy"]),("usage",d["operating_variable"])):
            vehicles = s[f"da_vinci_{contract}"] + s[f"ion_{contract}"]
            actual.append(dict(period=f"{year}YTD9", contract=contract, contract_revenue_m=rev,
                               da_vinci_units=s[f"da_vinci_{contract}"], ion_units=s[f"ion_{contract}"],
                               yearized_revenue_per_end_unit_m=rev*4/3/vehicles))
    result = []
    by_contract = {row["contract"]:row["yearized_revenue_per_end_unit_m"] for row in actual if row["period"] == "2026YTD9"}
    discount = cfg["lease_discount_screen"]
    maintenance = cfg["lease_maintenance_m_per_year_assumption"]
    term = cfg["lease_term_years_screen"]
    annuity = (1 - (1 + discount) ** -term) / discount
    for channel, manufacturing, collection_share in product(by_contract, (0.70, 0.85, 1.03), (0.85, 0.90, 0.95, 1)):
        revenue_m = by_contract[channel]
        cash_m = revenue_m * collection_share
        required = manufacturing / annuity + maintenance
        result.append(dict(contract=channel, manufacturing_m=manufacturing, collection_share=collection_share,
                           lease_term_years=term, discount=discount, recurring_maintenance_m=maintenance,
                           per_end_unit_revenue_proxy_m=revenue_m, cash_assumption_m=cash_m,
                           per_unit_project_npv_m=(cash_m-maintenance)*annuity-manufacturing,
                           max_manufacturing_for_npv_zero_m=(cash_m-maintenance)*annuity,
                           gross_cash_required_m=required, recognized_revenue_required_m=required/collection_share,
                           revenue_uplift_required=required/collection_share/revenue_m-1))
    return actual,result


def capital(inputs):
    history = load(ROOT/"docs/research15/annual.json")
    source = {row["period"]:row["values"] for row in history if "ISRG" in row["company"]}
    rows = []
    old = None
    current_profit = inputs["forecast_context"]["tax_rate_operating_proxy"]
    for key in ("2022-FY","2023-FY","2024-FY","2025-FY"):
        d = source[key]
        nwc = d["ar"] + d["inventory"] - d["ap"] - d["advance"]
        investment = nwc + d["ppe"]
        nopat = d["operating_profit"]*(1-current_profit)
        avg = (investment + old["capital_proxy_m"])/2 if old else None
        item = dict(period=key, revenue_m=d["revenue"], operating_profit_m=d["operating_profit"],
                    operating_tax_proxy=current_profit, nopat_proxy_m=nopat, trade_nwc_proxy_m=nwc,
                    ppe_m=d["ppe"], capital_proxy_m=investment, average_capital_proxy_m=avg,
                    capital_turnover=d["revenue"]/avg if avg else None, roic_proxy=nopat/avg if avg else None,
                    incremental_nopat_over_incremental_capital_proxy=(nopat-old["nopat_proxy_m"])/(investment-old["capital_proxy_m"]) if old else None)
        rows.append(item)
        old=item
    return rows


def reverse_check():
    model = load(ROOT/"docs/research17/US/model.json")
    price = model["price"]
    shares = model["market"]["shares"]/1e6
    result = {}
    for name,s in model["cases"].items():
        wacc = s["wacc"]
        g = s["terminal"]["growth"]
        top = s["terminal"]
        discount = (1+wacc)**s["rows"][-1]["t"]
        explicit_pv = sum(r["model_cash_after_date"]/(1+wacc)**r["t"] for r in s["rows"])
        tpv = top["fcff"]/(wacc-g)/discount
        close(tpv, top["pv"])
        close(top["nopat"]*g/top["incremental_return"], top["reinvestment"])
        excess = s["bridge"]["bridge_net"]
        equity = explicit_pv + tpv + excess
        reconstructed = equity/shares
        close(reconstructed, s["per_share"])
        close(tpv/(explicit_pv+tpv),top["pv_share"])
        required_ev = price*shares - excess
        required_tpv = required_ev - explicit_pv
        required_fcff = required_tpv*(wacc-g)*discount
        close((explicit_pv + required_fcff/(wacc-g)/discount + excess)/shares,price)
        result[name] = dict(frozen_stage17_share_value=s["per_share"], wacc=wacc, stable_growth=g,
                            explicit_pv=explicit_pv, terminal_pv=tpv, enterprise_value=explicit_pv+tpv,
                            terminal_share=top["pv_share"], excess_adjusted_equity_items=excess, common_shares_m=shares,
                            equity_for_ordinary=equity, reconstructed_price=reconstructed,
                            observed_close=price, market_ev_isolated=required_ev,
                            required_terminal_pv=required_tpv, terminal_fcff_baseline=top["fcff"],
                            required_terminal_fcff_if_only_terminal_changes=required_fcff,
                            terminal_fcff_multiple=required_fcff/top["fcff"],
                            terminal_revenue_required_if_cash_margin_same=top["revenue"]*required_fcff/top["fcff"])
    # Frozen operational reverse diagnostics, with an independent 2031 revenue check.
    operating_reverse = []
    for route in load(ROOT/"docs/research16/isrg-reverse.json"):
        if "reverse" not in route:
            continue
        boundary = [price+x for x in route["reverse"]["gap_at_ends"]]
        y = route["year_2031"]
        extra = {}
        if y:
            procedure_count = y["da_vinci_procedures"] + y["ion_cases"]
            close(y["average_active"]*y["procedures_per_average_active"], y["da_vinci_procedures"])
            close(procedure_count*y["ia_per_total_procedure"]/1e6, y["segments"]["ia"])
            close(sum(y["segments"].values()), y["revenue"])
            extra = dict(procedures_combined_2031=procedure_count, instruments_value_verified_m=y["segments"]["ia"],
                         combined_revenue_2031_m=y["revenue"])
        operating_reverse.append(dict(wacc=route["wacc"], installations_growth=route["installation_growth"],
                                      realization_growth=route["ia_per_case_growth"],
                                      utilization_domain=route["reverse"]["search"], boundary_prices=boundary,
                                      utilization_root=route["utilisation_growth"], **extra))
    return dict(fixed_cash_flow_reverse=result, operating_reverse_stage16=operating_reverse)


def systems_placement_bridge(i, revenue):
    placements = i["quarter_placements"]
    period_f, period_p = "2026Q3", "2025Q3"
    latest = placements[period_f]
    prior = placements[period_p]
    a, b = (next(r for r in revenue if r["period"] == period) for period in (period_f, period_p))
    q1 = latest["da_vinci"] - latest["da_vinci_fixed"] - latest["da_vinci_usage"]
    q0 = prior["da_vinci"] - prior["da_vinci_fixed"] - prior["da_vinci_usage"]
    p1, p0 = i["forecast_context"]["q3_asp_m_current_and_prior"]
    volume = (q1-q0)*(p1+p0)/2
    price_mix = (p1-p0)*(q1+q0)/2
    lease = a["systems_operating_lease"]-b["systems_operating_lease"]
    buyout = a["systems_buyout_rounded"]-b["systems_buyout_rounded"]
    change = a["systems_total"]-b["systems_total"]
    residual = change-volume-price_mix-lease-buyout
    close(volume+price_mix+lease+buyout+residual,change)
    return [dict(period="2025Q3→2026Q3",local_valuation_cutoff=i["market_cutoff"],
                 current_da_vinci_placements=latest["da_vinci"],prior_da_vinci_placements=prior["da_vinci"],
                 current_tradein=latest["da_vinci_tradein"],prior_tradein=prior["da_vinci_tradein"],
                 da_vinci_nonop_leased_placement_latest=q1,da_vinci_nonop_leased_placement_prior=q0,
                 asp_m_latest=p1,asp_m_prior=p0, systems_revenue_change=change,volume_bridge_m=volume,
                 price_mix_bridge_m=price_mix,operating_lease_change_m=lease,buyout_revenue_change_m=buyout,
                 mix_fx_rounding_and_ion_residual_m=residual)]


def main():
    i = load(HERE/"isrg-inputs.json")
    revenue = revenue_views(i)
    history, volume_bridge = drivers(i)
    lease_proxies, contracts = lease_cash(i,revenue)
    reverse = reverse_check()
    accounting = profit_cash_bridge(i,revenue)
    selected = [
        ("quarter-revenue-bridge.csv",revenue),("annual-unit-history.csv",history),("instrument-volume-mix.csv",volume_bridge),
        ("quarter-cash-accounting.csv",accounting),("lease-revenue-proxy.csv",lease_proxies),
        ("contract-thresholds.csv",contracts),("historical-capital-proxy.csv",capital(i)),
    ]
    selected.append(("system-placement-bridge.csv", systems_placement_bridge(i,revenue)))
    for filename,rows in selected:
        write_csv(HERE/filename,rows)
    (HERE/"independent-valuation.json").write_text(json.dumps(reverse,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ISRG revenue, GAAP EBIT, CFO, WACC, terminal FCFF, equity and observed-price bridges verified.")


if __name__ == "__main__":
    main()
