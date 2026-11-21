"""Generate the case tables, evidence cross-references, and reproducible valuation receipts."""
import argparse
from collections import Counter
from pathlib import Path
import sys

from case_model import CODES, OUT, ROOT, bake, get_records, group, add_optional
from build_atlas_valuation_notes import wacc_note
from recalculate_research14 import read
sys.path.insert(0,str(ROOT/'app'))
from atlas_render import csv_payload
from atlas_service import json_bytes


def ratios(numerator,denominator):
    return numerator/denominator if numerator is not None and denominator not in (0,None) else None


def difference(a,b):
    return a-b if None not in (a,b) else None


def history_rows(records, lease_rows):
    previous={}
    for r in sorted(records,key=lambda x:x['period']):
        y=int(r['period'].split('-')[0])
        vals, der = r['values'], r['derived']
        val=vals.get
        d=der.get
        prior=previous.get(y-1,{})
        p=prior.get('derived',{}).get
        revenue=val('revenue')
        cost=val('cost')
        gross=difference(revenue,cost)
        ebit=d('adjusted_ebit')
        da=d('depreciation_and_amortization')
        nopat=d('nopat_proxy')
        cash_tax=val('cash_tax')
        modeled_tax=difference(ebit,nopat)
        wc=d('ncwc_trade_only')
        delta_wc=difference(wc,p('ncwc_trade_only'))
        capex=d('gross_cash_capex')
        rent=lease_rows.get(r['period'].replace('-FY','FY')) or lease_rows.get(r['period'])
        agg_lease=(add_optional(rent.get('lease_financing_cash'),rent.get('lease_operating_cash')) if rent else None)
        op_cash=add_optional(nopat,da,-delta_wc if delta_wc is not None else None)
        cap=d('operating_capital_subset')
        capital_delta=difference(cap,p('operating_capital_subset'))
        prior_nopat=p('nopat_proxy')
        ebit_residual=difference(ebit,val('operating_profit'))
        roic_base=(cap + p('operating_capital_subset')) / 2 if cap is not None and p('operating_capital_subset') is not None else None
        expenses={k:val(k) for k in ('sales','admin','research','tax_surcharge')}
        core_from_items=difference(gross,add_optional(*expenses.values()))
        yield dict(period=r['period'],company=r['company'],unit=r['unit'],stage=r['stage'],
             revenue=revenue,revenue_growth=difference(ratios(revenue,prior.get('values',{}).get('revenue')),1),cost=cost,gross_profit=gross,
             **expenses,finance_reported=val('finance'),fair_value=val('fair_value'),asset_impairment=val('asset_impairment'),
             gross_less_observed_expenses=core_from_items,observed_expenses_to_analysis_ebit_residual=difference(ebit,core_from_items),
             report_operating_profit=val('operating_profit'),analysis_ebit=ebit,report_to_analysis_delta=ebit_residual,
             cash_tax_reported=cash_tax,normal_tax_proxy=modeled_tax,nopat_proxy=nopat,da=da,
             wc_trade_subset=wc,delta_wc_trade_subset=delta_wc,cash_capex=capex,known_cash_lease_total=agg_lease,
             cfo_reported=val('cfo'),cfo_minus_capex=d('cfo_less_cash_capex'),
             op_cash_before_other_flows=op_cash,fcff_before_unresolved_items=difference(op_cash,capex),
             cfo_vs_bridge_residual=difference(val('cfo'),op_cash),
             capital_subset=cap,capital_delta=capital_delta,capital_turnover=ratios(revenue,roic_base),
             incremental_return_paired=ratios(difference(nopat,prior_nopat),capital_delta)
                  if capital_delta is not None and capital_delta>0 else None,
             roic_subset=d('store_roic_proxy'), previously_declared_roi_proxy=d('incremental_return_proxy'),
             source_id=r['source'],url=r['url'],filed=r['filed'],sha256=r['sha256'],
             note='历史FCFF为已识别范围的桥。未能逐项核的租赁、资本和其他CFO项目留作缺项，不能将残差当实际费用。',
             locators={k:r.get('locators',{}).get(k) for k in ('revenue','cost','operating_profit','cfo','capex','cash_tax','finance','research')})
        previous[y]=r


def recent_rows(records, unit):
    for r in records:
        for k in ('revenue','cost','operating_profit','cfo','capex','sales','research','cash_collections'):
            yield dict(company=r['company'],period=r['period'],metric=k,
                 unit=unit, cumulative=r.get('cumulative',{}).get(k), single_period=r.get('single',{}).get(k),
                 cumulative_yoy=r.get('yoy',{}).get(k), single_period_yoy=r.get('single_yoy',{}).get(k),
                 ending_balance=None,source=r['source'],sha256=r.get('sha256'),prior_source=r.get('prior_source'),
                 locator=r.get('locators',{}).get(k),tag='冻结底表／按期现列')
        for k,v in r.get('endpoint',{}).items():
            yield dict(company=r['company'],period=r['period'],metric=k, unit=unit,cumulative=None,single_period=None,
                       cumulative_yoy=None,single_period_yoy=None,ending_balance=v,source=r['source'],sha256=r.get('sha256'),
                       prior_source=r.get('prior_source'),locator=r.get('locators',{}).get(k),tag='期末余额')


def evidence_rows(company, unit):
    for r in group(get_records(15,'business-disclosures'),company):
        loc=r.get('locator') or {k:r.get(k) for k in ('page','html_table','table','row_label','line','column','column_header')}
        timestamp=r.get('published_at') or r.get('filed')
        source_path=r.get('source_path') or r.get('path')
        yield dict(id=r['id'],company=company,metric=r['metric'],report_period=r['period'],
                   source_id=r.get('source_id',r['id']),filename=Path(source_path).name if source_path else None,
                   published_at=timestamp,availability=timestamp,period_scope=r.get('scope'),html_or_page=loc,
                   value=r['value'],unit=r.get('unit'),currency=r.get('currency'),url=r['url'],sha256=r.get('source_sha256') or r.get('sha256'),
                   tag=r.get('tag','原披露定位；实时Fact按账本'),check=r.get('check'),actor='agent')
    for r in group(get_records(17,'evidence'),company):
        yield dict(id=r['source_id']+':'+r['metric'],company=company,metric=r['metric'],report_period=r['period'],
                   source_id=r['source_id'],filename=None,published_at=r.get('disclosed'),availability=r.get('disclosed'),
                   period_scope=r.get('note'),html_or_page=r['locator'],value=r['value'],unit=r['unit'],
                   currency=None,url=r['url'],sha256=r['source_sha256'],tag=r['tag'],checked=r.get('checked'),actor='agent')


def relative_rows(model):
    rel=model['relative']
    rm=rel['stage14_market']; ltm=rm['ltm']
    for n,ref,num,den in (
            ('市值／滚动归母净利润',rm['equity_price_to_ltm_parent'],rm['market_cap_reporting_currency'],ltm['parent_income']),
            ('企业价值／滚动核心EBIT',rm['ev_to_ltm_operating_ebit'],rm['market_ev'],ltm['core_ebit']),
            ('企业价值／滚动收入',rm['ev_to_ltm_sales'],rm['market_ev'],ltm['revenue'])):
        computed=num/den
        assert abs(computed-ref)<1e-9
        yield dict(comparison='自身同日滚动',period=rm['ltm_end'],observed_at=model['cutoff'],
              currency=model['security']['report'],security=model['security']['right'],
              metric=n,numerator=num,denominator=den,multiple=computed,
              note='复算已冻结的阶段14同日企业价值桥与常态化EBIT。与阶段17分母调整单列。')
    for scenario,case in model['cases'].items():
        for metric,numerator,denominator in (('条件EV／滚动核心EBIT',case['enterprise_value'],ltm['core_ebit']),
                ('条件权益价值／滚动归母净利',case['equity'],ltm['parent_income'])):
            yield dict(comparison=scenario,period=rm['ltm_end'],observed_at=model['cutoff'],
                  currency=model['security']['report'],security=model['security']['right'],metric=metric,
                  numerator=numerator,denominator=denominator,multiple=numerator/denominator,
                  note='以同一组原报告常态口径作条件倍数换算；分子来自新版DCF。')
    for comp,why in rel['universe']:
        yield dict(comparison='淘汰表',security=comp,metric=None, observed_at=model['cutoff'],note=why)


def annual_2026(model):
    for scenario,c in model['cases'].items():
        r=c['rows'][0]
        earnings=r.get('operating_profit',r.get('normalized_core_ebit'))
        actual=(r.get('disclosed_revenue') or r.get('h1_actual') or r.get('actual',{}).get('total'))
        remainder=r.get('undisclosed_revenue',r.get('rest_revenue',r.get('remaining_revenue')))
        assert abs(actual+remainder-r['revenue'])<1e-8
        yield dict(scenario=scenario, period=model['source_windows']['latest_disclosed_period'],
                    unit=model['security']['report']+' 百万', actual_revenue=actual,remaining_revenue=remainder,
                    full_year_revenue=r['revenue'],reported_core_ebit=r.get('disclosed_core_ebit'),
                    estimated_unreported_ebit=r.get('undisclosed_ebit',r.get('rest_ebit')),
                    estimated_full_year_operating_ebit=earnings, ending_wc=r.get('wc'),
                    cash_after_valuation_date=r['model_cash_after_date'],time_to_valuation=r['t'],
                    tag='已披露实际与情景估计分栏；估值仅纳入截点后现金')


def parameters(model):
    inputs=model['operating_inputs']
    for i,scenario in enumerate(('base','stress','improve')):
        d=model['cases'][scenario]
        fields=[
            ('经营量与实现价/结构',inputs['rates'][i],'同名历史驱动及留出修正；专门模型见 native_driver_spec'),
            ('预测期营业利润率先验',inputs['active_margin'][i],'历史可比范围；现金租金口径另外调整'),
            ('经营营运资本／收入',inputs['wc'][i],'集团可见经营性余额代理，最低去化速度按情景'),
            ('WACC',d['wacc'],wacc_note(model['company'].split('_',1)[0],scenario)),
            ('永续增长',d['terminal']['growth'],'稳态规模；唯一期间与终值所在年见预测底表'),
            ('稳态新增投入回报',d['terminal']['incremental_return'],'稳态再投资＝NOPAT×增长率／新增回报'),
        ]
        for name,value,note in fields:
            yield dict(scenario=scenario,parameter=name,value=value,rule=note,history_window=inputs['window'],
                       latest=model['source_windows']['latest_disclosed_period'],
                       recalibration=inputs['check'],
                       source=model['source_windows']['operating_account'],tag='条件路径')


def build(out, check):
    models,annual,recent,receipt=bake()
    if check:
        official=OUT/'model-acceptance.json'
        if official.is_file():
            import json
            standard=json.loads(official.read_text(encoding='utf-8'))
            assert standard['old_price_roundtrips']==62
    for c in CODES:
        model=models[c]
        company=model['company']
        periods=group(annual,company)
        unit=periods[-1]['unit']
        lease={r['period']:r for r in next(m for m in get_records(17,'valuation') if m['company']==company)['basis'].get('lease_history',[])}
        hist=list(history_rows(periods,lease))
        actual=list(recent_rows(group(recent,company),unit))
        forecast=[dict(scenario=k,**r) for k,case in model['cases'].items() for r in case['rows']]
        evidence=list(evidence_rows(company,unit))
        files={
         'model.json':json_bytes(model),
         '2026-bridge.csv':csv_payload(list(annual_2026(model))),
         'parameters.csv':csv_payload(list(parameters(model))),
         'inputs.json':json_bytes(dict(security=model['security'],cutoff=model['cutoff'],close=model['close'],
             operating=model['operating_inputs'],calibration=model['scenario_calibration'],source_windows=model['source_windows'],
             holdouts=model['holdouts'],native_driver_spec=model['native_driver_spec'])),
         'history.csv':csv_payload(hist),
         'interim.csv':csv_payload(actual),
         'forecast.csv':csv_payload(forecast),
         'evidence-index.csv':csv_payload(evidence),
         'relative.csv':csv_payload(list(relative_rows(model))),
         'operating-bridges.csv':csv_payload(group(get_records(15,'operating-bridges'),company)),
         'sensitivity.csv':csv_payload(model['tests']['matrix']),
         'reverse.csv':csv_payload(model['tests']['boundary']),
         'value-bridge.csv':csv_payload(model['stage17_to_case']),
        }
        target=out/c
        target.mkdir(parents=True,exist_ok=True)
        for name,data in files.items():
            path=target/name
            if check:
                assert path.read_bytes()==data,path
            else:
                path.write_bytes(data)
    counter={c:sum(len(q['roots']) for q in m['tests']['boundary']) for c,m in models.items()}
    receipt.update(new_joint_reversals=counter,
                   paths={c:{k:r['per_share'] for k,r in m['cases'].items()} for c,m in models.items()})
    out.mkdir(parents=True,exist_ok=True)
    receipt_file=out/'model-acceptance.json'
    if check:
        old=read(receipt_file)
        # Restored archives are per checkout. The model bytes and frozen counts remain identical.
        assert {k:v for k,v in old.items() if k!='cold_or_current_facts'}=={
                k:v for k,v in receipt.items() if k!='cold_or_current_facts'}
    else:
        receipt_file.write_bytes(json_bytes(receipt))
    print(receipt)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    build(args.output.resolve(),args.check)
