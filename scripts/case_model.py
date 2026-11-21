"""Rebuild fifteen economic forecast paths and their company-specific price tests."""
import argparse
from copy import deepcopy
from functools import partial
from math import isclose
import json
from pathlib import Path

from recalculate_research14 import CASES, ROOT, read, save, sha
from recalculate_research16 import Context, isrg_value, pop_value, reverse
from research17_analysis import research

OUT = ROOT / 'docs/cases'
AS_OF = '2026-11-12'
CODES = ('002507','600298','688188','09992','US')


def get_records(stage, file):
    return read(ROOT / 'docs' / f'research{stage}' / f'{file}.json')


def code_of(row):
    return row['company'].split('_', 1)[0]


def group(rows, company):
    return [r for r in rows if r['company'] == company]


def add_optional(*values):
    return sum(values) if None not in values else None


def get_period(records, period):
    return next(r for r in records if r['period']==period)


def ctxs(annual, recent, stage17):
    old = {r['company']:r for r in get_records(15,'valuation')}
    return {code_of(m):Context(old[m['company']], annual, recent, {code_of(m):m['driver_holdout']}) for m in stage17}


ISRG_LEASE = {'variable':503.8,'operating_total':787.0,'period':'2026-YTD9','unit':'USD millions',
              'source_id':'S83c179dfd93521d4','sha256':'df5b434e5ae926551c12632ba637d5d182aa1fdf3eab00b5668983bc91','filed':'2026-10-21','availability':'2026-10-21；早于估值日','loc':'Note 5 Intuitive System Leasing；Nine Months Ended September 30, 2026列',
              'url':'https://www.sec.gov/Archives/edgar/data/1035267/000103526726000071/isrg-20260930.htm'}


def run_case(ctx, scenario, old, precise=False):
    """Execute the imported operating equations. Source rows and priors are immutable."""
    if ctx.code == '600298':
        return ctx.generic(scenario,rate=old['cases'][scenario]['wacc'])
    if ctx.code == '09992':
        args = {
            'base':(old['basis']['approved_capacity'], 1., 1., 1., .135),
            'stress':(.025, .8, 1.12, 1.17, .185),
            'improve':(.15, 1.1, .94, .90, .105),
        }
        return pop_value(ctx,scenario,*args[scenario])
    if ctx.code == 'US':
        install = .094 + old['basis']['installed_evidence_adjustment'] if scenario=='base' else None
        return isrg_value(ctx,scenario,install=install,reported_variable_lease=ISRG_LEASE['variable'] if precise else None)
    return ctx.generic(scenario)


def price(case, market, *, rate=None, terminal=None, bridge=None):
    """Discount model cash from the frozen close and convert to one share of the quoted security."""
    w = case['wacc'] if rate is None else rate
    tv = terminal or case['terminal']
    assert 0 < tv['growth'] < min(tv['incremental_return'], w)
    explicit = sum(r['model_cash_after_date']/(1+w)**r['t'] for r in case['rows'])
    final_cash = tv['nopat']*(1-tv['growth']/tv['incremental_return'])
    terminal_pv = final_cash/(w-tv['growth'])/(1+w)**case['rows'][-1]['t']
    enterprise = explicit+terminal_pv
    equity = enterprise + (bridge or case['bridge'])['bridge_net']
    return dict(explicit_pv=explicit,terminal_cash=final_cash,terminal_pv=terminal_pv,
                terminal_share=terminal_pv/enterprise,enterprise=enterprise,equity=equity,
                per_share=equity*1e6/market['shares']/market['fx'])


def check_money(old, new, market, compare=True):
    rebuilt = price(new,market)
    for v, ref in ((rebuilt['per_share'],old['per_share']), (new['per_share'],rebuilt['per_share']),
                   (new['terminal']['pv'],rebuilt['terminal_pv']), (new['equity'],rebuilt['equity'])):
        if compare or ref!=old['per_share']:
            assert isclose(v,ref,rel_tol=2e-12,abs_tol=1e-9), (v,ref)
    for row in new['rows']:
        assert isclose(row['present_value'],row['model_cash_after_date']/(1+new['wacc'])**row['t'],rel_tol=1e-12)
        if row['year']>=2027:
            assert isclose(row['nopat'],row['operating_profit']-row['cash_tax'],rel_tol=1e-12)
            assert isclose(row['model_cash_after_date'],row['nopat']-row['net_reinvestment'],rel_tol=1e-12)
    return rebuilt


def fuling_value(base, market, fee, capital, tax):
    """Only incremental-to-path half-year fees and working capital/capex. No terminal extrapolation."""
    staged = deepcopy(base)
    for row in staged['rows']:
        if row['year'] in (2027,2028,2029):
            row['model_cash_after_date'] -= (2*fee*(1-tax)+capital)*(1 if row['year']==2027 else .5 if row['year']==2028 else .25)
    return price(staged,market)['per_share']


def axes(code, ctx, old, case):
    if code=='002507':
        tax=case['rows'][1]['cash_tax']/case['rows'][1]['operating_profit']
        return ('附加可归属销售费用（半年度，百万元）','附加基地与营运资本现金付出（年，百万元）',
                (0.,300.),(0,10,25,50,100),
                [0,10,20,34.35092621,50,70,100,160,220,300],
                partial(fuling_value,case,old['market'],tax=tax),
                '2027–2029 额外冲击的权重1／0.5／0.25。费用年化税后处理，资本与占款直接扣现。输入是原路径以外的额外付出，压力测试与原集团销售费用不叠加估计实际归属。')
    if code=='600298':
        return ('新增资本回报','WACC',(.045,.30),(.055,.0596917,.065,.07,.075,.08,.09),
                [.045,.065,.08,.10,.112,.1175,.14,.175,.22,.30],
                lambda x,y:ctx.generic(roi=x,rate=y)['per_share'],
                '改变WACC与稳定新增ROIC，保留报告期实际、可售吨量和组均价。收益率下限高于增长率。')
    if code=='688188':
        v=65064/60993-1
        return ('控制系统销量增速','稳定核心营业利润率',(-.04,.25),(.41,.44,.47,.50,.53),
                [-.04,0,.025,.05,v,.0753,.10,.13,.17,.21,.25],
                lambda x,y:ctx.generic(volume_shift=x-v,steady_margin=y)['per_share'],
                '控制销量以披露的2024、2025同名套数为基准。长期利润率反映配套毛利、研发和售后净贡献，信用品质按原营运资本设定。')
    if code=='09992':
        latest=get_period(ctx.recent,'2026-H1')['cumulative']['revenue']
        reference=old['basis']['h2_2025']
        q3=reference*.5*(1-.475)
        return ('Q4绝对收入（人民币百万元）','固定现金租金倍数',(0.,22000.),(.80,.90,1.,1.1,1.25),
                [0,1000,2000,3000,4000,5500,7500,10000,15000,22000],
                lambda x,y:pop_value(ctx,'base',old['basis']['approved_capacity'],fixed_scale=y,
                                     h2_factor=(q3+x)/reference)['per_share'],
                f'Q3仅有同比范围。固定2025Q3占H2 50%、Q3同比−47.5%，故本表Q3为{q3:.3f}百万元情景。H1实际{latest:.3f}百万元，固定租金乘数传导到现金口径利润。库存见专项联合表。')
    return ('装机增速','每台活跃设备术量增速',(.02,.30),(.0,.03,.06,.09,.12),
            [.02,.05,.08,.0981635,.13,.16,.20,.25,.30],
            lambda x,y:isrg_value(ctx,install=x,use=y,yield_growth=.015,wacc=.08,reported_variable_lease=ISRG_LEASE['variable'])['per_share'],
            '固定WACC 8%、每例净收入增长1.5%与基准租赁设备现金，装机和活跃术量共同驱动耗材、服务及使用量租赁。')


def sweep(code,ctx,old,base):
    x_name,y_name,domain,ys,xs,fn,condition = axes(code,ctx,old,base)
    close=old['price']
    matrix=[dict(x=x,y=y,value=fn(x,y),close=close) for y in ys for x in xs]
    boundary=[]
    for y in ys:
        r=reverse(lambda x:fn(x,y),close,domain,condition)
        edge=[fn(x,y) for x in domain]
        boundary.append(dict(y=y,low=domain[0],high=domain[1],value_low=edge[0],value_high=edge[1],
            gap_low=edge[0]-close,gap_high=edge[1]-close,status=r['status'],
            roots=[dict(x=x,recovered=fn(x,y),gap=fn(x,y)-close) for x in r['roots']]))
        assert all(abs(row['gap'])<1e-7 for row in boundary[-1]['roots'])
    return dict(x=x_name,y=y_name,condition=condition,matrix=matrix,boundary=boundary)


def change_bridge(old,base,market):
    # Cross from archived to executable values using the stated block order.
    a=deepcopy(old)
    b=base
    checkpoints=[('阶段17冻结值',price(a,market)['per_share'])]
    cash=[]
    for before,after in zip(a['rows'],b['rows']):
        # Same stub clock and path scope in both vintages. Some stub models disclose no whole-year NOPAT.
        if 'nopat' in before and 'nopat' in after:
            cash.append(before['model_cash_after_date'] + after['nopat'] - before['nopat'])
        else:
            cash.append(before['model_cash_after_date'])
    for row,c in zip(a['rows'],cash):
        row['model_cash_after_date']=c
    checkpoints.append(('量价、成本与经营税',price(a,market)['per_share']))
    a['rows']=b['rows']
    checkpoints.append(('营运资本和再投资',price(a,market)['per_share']))
    a['wacc']=b['wacc']
    checkpoints.append(('融资及折现',price(a,market)['per_share']))
    a['terminal']=b['terminal']
    checkpoints.append(('终值',price(a,market)['per_share']))
    a['bridge']=b['bridge']
    checkpoints.append(('净债务、其他权益及股数',price(a,market)['per_share']))
    return [dict(step=n,per_share=v,delta=0. if i==0 else v-checkpoints[i-1][1])
            for i,(n,v) in enumerate(checkpoints)]


def native_spec(code, old):
    m=old['basis']
    if code=='09992':
        return dict(capacity=m['approved_capacity'],h2_reference=m['h2_2025'],lease_history=m['lease_history'],
                    axis='等效渠道增长×销售密度；现金固定和浮动租赁另算', calibration=m['correction'])
    if code=='US':
        return dict(install_base=.094+m['installed_evidence_adjustment'], utilization_base=.013,unit_net_revenue_growth=.003,
                    lease_unit_manufacturing=.85, reported_sales_split=m['sales_split'], cash_remap=m['cash_remap'],
                    lease_note_precision=ISRG_LEASE, axis='装机、每台活跃术量、器械耗材、服务、固定与按量租赁')
    if code=='600298':
        return dict(axis='可售吨量×组均价和地域结构', marginal_financing_cost=m['kd'], beta=m['structural_beta'],
                    tax=m['tax'], risk_free=m['rf'], equity_risk_premium=m['erp'], plant_bridge=m['plant_and_cash_bridge'])
    if code=='688188':
        return dict(axis='控制系统销量×软硬件组合', systems_2024=60993, systems_2025=65064,
                    financial_vs_operating=m['financial_vs_operating'])
    return dict(axis='食品销量×组均价和品类',channel_h1_bridge=m['channel_h1_bridge'],
                plant_scenarios=m['plant_scenarios'])


def bake():
    manifest=read(OUT/'frozen-inputs.json')
    assert all(sha(ROOT/rel)==digest for rel,digest in manifest['files'].items())
    frozen,facts=research()
    original=get_records(17,'valuation')
    assert len(frozen)==len(original)==5
    prices=0
    recomputed={m['company']:m for m in frozen}
    for b in original:
        a=recomputed[b['company']]
        assert json.loads(json.dumps(a['critical_points']))==b['critical_points'],a['company']
        for r in b['critical_points'].get('rows',[]):
            for k in ('condition_price','price_at_threshold','recovered_market_price'):
                if k in r:
                    assert abs(r[k]-b['price'])<1e-7
                    prices+=1
    assert prices==62
    annual,recent=get_records(15,'annual'),get_records(15,'interim')
    assert len(annual)==65 and len(recent)==49
    contexts=ctxs(annual,recent,original)
    result={}
    for old in original:
        code=code_of(old)
        ctx=contexts[code]
        cases={}
        for c in CASES:
            baseline=run_case(ctx,c,old)
            check_money(old['cases'][c],baseline,old['market'])
            cases[c]=run_case(ctx,c,old,precise=True) if code=='US' else baseline
            cases[c]['valuation_check']=check_money(old['cases'][c],cases[c],old['market'],compare=code!='US')
        base=cases['base']
        result[code]=dict(company=old['company'], cutoff=AS_OF, close=old['price'], security=old['market'],
             cases=cases, historical_bridge=old['bridge'],
             stage17_to_case=change_bridge(old['cases']['base'],base,old['market']),
             tests=sweep(code,ctx,old,base), original_tests=old['critical_points'],
             operating_inputs=ctx.stage['parameters'], scenario_calibration=ctx.stage['calibration'],
             source_windows={'latest_disclosed_period':'2026-H1' if code=='09992' else '2026-Q3',
                 'frozen_stage17':'docs/research17/'+code+'/model.json',
                 'operating_account':f"companies/{old['company']}/work/research14/inputs.json"},
             native_driver_spec=native_spec(code,old),
             relative=old['relative'],
             holdouts={'driver_summary':old['driver_holdout'],
                       'driver':group(get_records(16,'driver_holdouts'),old['company']),
                       'revenue':old['stage15_total_revenue_holdouts']})
    return result, annual, recent, dict(annual=len(annual),interim=len(recent),cold_or_current_facts=len(facts),
                                       frozen_facts=len(get_records(17,'current_facts')),old_price_roundtrips=prices,path_count=15)
