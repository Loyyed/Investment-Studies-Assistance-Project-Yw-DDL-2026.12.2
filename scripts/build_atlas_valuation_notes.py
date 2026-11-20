"""Rebuild the long-edition WACC note and Fuling's focused current-price tests."""
import csv
import json
from pathlib import Path

from case_model import CODES, OUT, ROOT, code_of, ctxs, fuling_value, get_records, read, reverse

TARGET = ROOT/'docs/long-atlas'
CHANNEL_DOMAIN = (0.,300.)
DEMAND_DOMAIN = (-.13,.03)


def write_csv(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        csvfile=csv.DictWriter(f,list(dict.fromkeys(key for r in rows for key in r)),lineterminator='\n')
        csvfile.writeheader()
        csvfile.writerows(rows)


def wacc_note(code, scenario):
    if code == '600298':
        if scenario != 'base':
            return '安琪阶段16独立折现情景；压力8.00%，改善5.50%；不反推β'
        return '安琪阶段16采用条件β=1；以1.60%无风险利率、5.32%市场风险溢价和税后债务成本及市场权重计算'
    if code == '09992':
        return '阶段14周收益β按2/3样本、1/3单位收缩；租赁作经营现金，估值资本结构无有息债务权重'
    if code == 'US':
        return '阶段14美股周收益β按2/3样本、1/3单位收缩；美元参数；估值资本结构无有息债务权重'
    return '阶段14周收益β按2/3样本、1/3单位收缩；以市场债务权重及情景税率计算税后融资成本'


def wacc_rows(models):
    rows=[]
    for code in CODES:
        info=models[code]
        cfg=ROOT/'companies'/info['company']/'work/research14'
        old=read(cfg/'calculation.json')['cases']
        available=read(cfg/'market.json')
        for scenario,result in info['cases'].items():
            detail=old[scenario]['discount']
            old_input=old[scenario]['rows'][0]
            beta=detail['beta_applied']
            tax=old_input['cash_tax_rate']
            direct=code=='600298' and scenario!='base'
            if code=='600298' and scenario=='base':
                beta=1.
            ke=detail['rf']+beta*detail['erp']
            weight=detail['debt_weight']
            kd=detail['cost_debt_pre_tax']
            wacc_input=ke*(1.-weight)+kd*(1.-tax)*weight
            if not direct:
                assert abs(wacc_input-result['wacc'])<1e-12
            rows.append(dict(code=code,scenario=scenario,beta_raw=detail['beta_raw'],beta_old_shrunk=detail['beta_applied'],
                        beta_adopted=None if direct else beta,n=detail['beta_n'],r2=detail['beta_r2'],
                        beta_se=available.get('beta_se'),risk_free=detail['rf'],equity_risk_premium=detail['erp'],
                        debt_weight=weight,pre_tax_debt_cost=kd,tax_rate=tax,
                        archive_wacc=detail['wacc'],recomputed_wacc=None if direct else wacc_input,wacc=result['wacc'],
                        condition=wacc_note(code,scenario),
                        source=(cfg/'calculation.json').relative_to(ROOT).as_posix()))
    return rows


def bound(test, domain, current, category, **fixed):
    result=reverse(test,current,domain,category)
    rows=[]
    for x in result['roots'] or [None]:
        value=test(x) if x is not None else None
        if x is not None:
            assert abs(value-current)<1e-7
        rows.append(dict(test=category,**fixed,low=domain[0],high=domain[1],
                         price_low=test(domain[0]),price_high=test(domain[1]),close=current,
                         gap_low=test(domain[0])-current,gap_high=test(domain[1])-current,
                         value_at_root=value,root=x,status=result['status']))
    return rows


def fuling_results(model):
    archive=get_records(17,'valuation')
    company=next(row for row in archive if code_of(row)=='002507')
    ctx=ctxs(get_records(15,'annual'),get_records(15,'interim'),archive)['002507']
    base=model['cases']['base']
    market=model['security']
    close=model['close']
    tax=base['rows'][1]['cash_tax']/base['rows'][1]['operating_profit']
    rows=[]
    for capital in (0,10,25,50,100):
        rows.extend(bound(lambda fee:fuling_value(base,market,fee,capital,tax),CHANNEL_DOMAIN,close,
                          'H1可归属费用×增量资本付出（百万元），固定集团量价；历史验收0根',
                          halfyear_fee_m=None,incremental_capital_m=capital,annual_volume_change_delta_pp=None))
    for capital in (0,10,25):
        for fee in (0,7.683189275,21.0877):
            def price(shift):
                return fuling_value(ctx.generic(volume_shift=shift),market,fee,capital,tax)
            old=price(0)
            temporary=fuling_value(base,market,fee,capital,tax)
            assert abs(old-temporary)<1e-9
            rows.extend(bound(price,DEMAND_DOMAIN,close,
                              '集团各显性年度销量增速附加百分点×直销费用（条件）；资本列固定',
                              halfyear_fee_m=fee,incremental_capital_m=capital,
                              annual_volume_change_delta_pp='root×100'))
    return rows


def main():
    models={code:read(OUT/code/'model.json') for code in CODES}
    write_csv(TARGET/'wacc.csv',wacc_rows(models))
    rows=fuling_results(models['002507'])
    write_csv(TARGET/'002507'/'channel-current-price.csv',rows)
    print('expanded Fuling',[(r['incremental_capital_m'],r['halfyear_fee_m'],r['root'],r['price_low'],r['price_high']) for r in rows])

if __name__=='__main__':
    main()
