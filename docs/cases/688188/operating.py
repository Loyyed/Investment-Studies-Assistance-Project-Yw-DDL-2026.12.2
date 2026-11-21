"""Rebuild Bochu's supplementary operating bridges and frozen-price inverse."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]


def load(name):
    return json.loads((DOCS / name).read_text(encoding='utf-8'))


def write(name, rows):
    with (HERE / (name + '.csv')).open('w', encoding='utf-8-sig', newline='') as f:
        table = csv.DictWriter(f, fieldnames=list(rows[0]))
        table.writeheader()
        table.writerows(rows)


def close(a, b, tolerance=1e-7):
    assert abs(a-b) < tolerance, (a,b)


def operating_tables():
    labels = ('平面解决方案', '管材解决方案', '三维解决方案', '其他主营')
    sales_24 = [1124.81290080, 380.23109685, 36.77665406, 176.05428520]
    sales_25 = [1292.90978748, 487.44975000, 63.89266655, 322.39255621]
    costs_24 = [194.65651401, 47.35938752, 7.10975959, 85.31945718]
    costs_25 = [238.58950650, 76.01847133, 11.08496289, 152.69782074]
    rows = []
    for name, r0, r1, c0, c1 in zip(labels, sales_24, sales_25, costs_24, costs_25):
        w0, w1 = r0/sum(sales_24), r1/sum(sales_25)
        m0, m1 = 1-c0/r0, 1-c1/r1
        rows.append(dict(group=name,revenue_24=r0,revenue_25=r1,cost_24=c0,cost_25=c1,
            gross_24=r0-c0,gross_25=r1-c1,margin_24=m0,margin_25=m1,
            sales_delta=r1-r0,gross_delta=(r1-c1)-(r0-c0),
            midpoint_mix_pp=(w1-w0)*(m1+m0)*50,midpoint_segment_margin_pp=(m1-m0)*(w1+w0)*50,
            label='原披露及算术',source='2024年报p25和2025年报p27–28；百万元人民币'))
    changed = ((1-sum(costs_25)/sum(sales_25))-(1-sum(costs_24)/sum(sales_24)))*100
    close(sum(r['midpoint_mix_pp']+r['midpoint_segment_margin_pp'] for r in rows),changed)
    q0, q1 = 60993,65064
    avg0, avg1 = sum(sales_24)/q0,sum(sales_25)/q1
    quantity = (q1-q0)*(avg0+avg1)/2
    realisation = (avg1-avg0)*(q0+q1)/2
    close(quantity+realisation,sum(sales_25)-sum(sales_24))
    volume = [dict(period=2024, control_units=q0, control_inventory=5226,hardware_units=35118, hardware_inventory=3127),
              dict(period=2025,control_units=q1,control_inventory=7340,hardware_units=56824,hardware_inventory=7963)]
    for r, sales in zip(volume,[sum(sales_24),sum(sales_25)]):
        r.update(hardware_to_control_shipments=r['hardware_units']/r['control_units'],
                 control_finished_stock_days=r['control_inventory']/r['control_units']*365,
                 hardware_finished_stock_days=r['hardware_inventory']/r['hardware_units']*365,
                 combined_main_revenue_per_control_equivalent_cny=sales/r['control_units']*1e6,
                 label='出货当量代理；组均价×组合；库存是件数',source='2024年报p26、2025年报p29')
    return rows,volume,dict(volume_contribution_m=quantity,realisation_mix_contribution_m=realisation,
        main_margin_change_pp=changed, main_mix_pp=sum(r['midpoint_mix_pp'] for r in rows),
        main_unit_margin_pp=sum(r['midpoint_segment_margin_pp'] for r in rows),
        report_main_revenue_25_m=sum(sales_25), report_main_revenue_24_m=sum(sales_24),
        other_activities_revenue_25_m=2195.63231292-sum(sales_25),
        other_activities_revenue_24_m=1735.45507067-sum(sales_24))


def benchmark(case, market, shift=0, margin=None, working_share=.122):
    """Rebuild Stage17 cash dynamics under control volume, margin and WC changes."""
    terminal = case['terminal']
    end, growth, roi = terminal['year'],terminal['growth'],terminal['incremental_return']
    rate, stub = case['wacc'], case['rows'][0]
    tax = stub['cash_tax']/stub['operating_profit']
    target = terminal['margin'] if margin is None else margin
    sales, wc = stub['revenue'],max(stub['disclosed_wc_subset']*.91,stub['revenue']*working_share)
    pv = (stub['model_cash_after_date'] -(wc-stub['wc'])*stub['stub_fraction'])/(1+rate)**stub['t']
    projection = []
    for row in case['rows'][1:]:
        year = row['year']
        fade = max(0,(year-2029)/(end-2029))
        sales *= (1+row['driver_1']+shift*(1-fade))*(1+row['driver_2'])
        ratio = sales/row['revenue']
        new_wc = max(sales*working_share,wc*.91)
        physical_investment = ratio*(row['cash_capex']-row['depreciation']+row['lease_cash']+
            row['incremental_equipment_cash'])+new_wc-wc
        operating_profit = sales*(row['margin']+fade*(target-terminal['margin']))
        projection.append((row['t'],year, operating_profit*(1-tax),physical_investment))
        wc = new_wc
    stable = sales*(1+growth)*target*(1-tax)
    for (t,year,nopat,inv), nxt in zip(projection,projection[1:]+[(0,end,stable,0)]):
        convergence=max(0,(year-2029)/(end-1-2029))
        net=inv*(1-convergence)+max(0,(nxt[2]-nopat)/roi)*convergence
        pv+=(nopat-net)/(1+rate)**t
    pv += stable*(1-growth/roi)/(rate-growth)/(1+rate)**projection[-1][0]
    return (pv+case['bridge']['bridge_net'])*1e6/market['shares']/market['fx']


def bisect(fn, value, a, b):
    assert fn(a) < value < fn(b)
    for _ in range(74):
        m=(a+b)/2
        if fn(m)<value:
            a=m
        else:
            b=m
    root=(a+b)/2
    close(fn(root),value)
    return root


def ebit_bridge():
    rows = []
    observations = [
      ('2024-FY', 1735.45507067,348.19906522,23.43903730,101.45273021,121.29961103,281.03519017,
         -26.25818217,26.24149106,104.85997888,23.01454942,23.68838576,-1.57854252,-.03597342,.00401061,1036.24002764),
      ('2025-FY',2195.63231292,490.53807596,28.53670066,136.84351252,155.67764377,341.32953146,
          -32.82011965,33.87856901,124.18887711,22.15832869,44.63634117,-3.89550557,-17.25991692,-.23093198,1245.12416070),
      ('2025-YTD9',1619.59650409,354.80891106,20.86538197,82.40859269,96.37646313,180.91862499,
          -26.71718652,27.57393800,71.02495496,18.68563060,31.44990073,-1.67174753,0,-.18493762,1030.23951791),
      ('2026-YTD9',1879.56668264,509.06729813,21.49620010,89.71478333,117.21302497,203.88147884,
          -88.70163964,91.06114144,136.66140702,17.06413621,46.96535593,-1.56745572,0,.01205907,1226.03103942),
    ]
    for r in observations:
        period,rev,cogs,tax,sell,admin,rnd,fin,interest,other,investment,mark,credit,asset,disposal,legal=r
        ebit=rev-cogs-tax-sell-admin-rnd
        close(ebit-fin+other+investment+mark+credit+asset+disposal, legal)
        rows.append(dict(period=period,revenue=rev,cogs=cogs,gross=rev-cogs,sales_exp=sell,admin=admin,
             rd=rnd,surcharges=tax,analysis_ebit=ebit,finance_exp_signed=fin,interest_subline=interest,
             other_income=other,investment_income=investment,fair_value=mark,credit_loss=credit,
             asset_loss=asset,disposal=disposal,reported_operating_profit=legal,
             report_minus_core=legal-ebit,source='2025年报p125–126；2026三季报p8–9；百万元人民币'))
    return rows


def capital_tables():
    annual = [r for r in load('research15/annual.json') if r['company'].startswith('688188')]
    rows = []
    for k,row in enumerate(annual):
        val,der = row['values'],row['derived']
        prev = annual[k-1]['derived'] if k else {}
        wc, old = der.get('ncwc_trade_only'), prev.get('ncwc_trade_only')
        before, after = prev.get('operating_capital_subset'),der.get('operating_capital_subset')
        da,capex,nopat=der.get('depreciation_and_amortization'),val.get('capex'),der.get('nopat_proxy')
        delta = wc-old if wc is not None and old is not None else None
        cash = nopat+da-delta-capex if all(v is not None for v in [nopat,da,delta,capex]) else None
        rows.append(dict(period=row['period'],revenue=val.get('revenue'),reported_ebit=val.get('operating_profit'),
            analysis_ebit=der.get('adjusted_ebit'),cash_tax_proxy=(der['adjusted_ebit']-nopat if nopat is not None else None),
            nopat_proxy=nopat,da_proxy=da,wc_subset=wc,delta_wc_subset=delta,cash_capex=capex,
            operating_capital_subset=after,capital_turn_proxy=(val['revenue']/((before+after)/2)
                      if before and after and (before+after)>0 else None),
            roic_proxy=der.get('store_roic_proxy'),incremental_return_proxy=der.get('incremental_return_proxy'),
            forecast_tax_lease_separate=None, fcff_proxy_pre_unknown_lease=cash,reported_cfo=val.get('cfo'),
            cfo_less_capex=der.get('cfo_less_cash_capex'),
            cash_proxy_minus_cfo_less_capex=(cash-der['cfo_less_cash_capex']
                    if cash is not None and der.get('cfo_less_cash_capex') is not None else None),
            source=row['source'],label='税/D&A/资本/FCFF为代理；空值留缺；百万元人民币'))
    return rows


def draw_grid(rows, render_x, render_y, title, subtitle, file_name):
    """Portable, source-value heat map. Triple rows are x, y, value in display units."""
    import html
    xs=sorted({x for x,_,_ in rows})
    ys=sorted({y for _,y,_ in rows},reverse=True)
    cells={(x,y):value for x,y,value in rows}
    values=[v for v in cells.values() if v is not None]
    lo,hi=min(values),max(values)
    width,height=706,135+48*len(ys)
    dx=532/len(xs)
    pieces=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
      f'<title>{html.escape(title)}</title><desc>{html.escape(subtitle)}</desc>',
      f'<rect width="{width}" height="{height}" rx="17" fill="#fff5e9"/>']
    def label(x,y,value,size=15,color='#302b28',align='start'):
        return f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{align}" font-family="sans-serif" font-size="{size}">{html.escape(str(value))}</text>'
    pieces.extend([label(24,33,title,20),label(24,61,subtitle,14,'#51453d')])
    for j,y in enumerate(ys):
        yy=94+48*j
        pieces.append(label(140,yy+30,render_y(y),14,align='end'))
        for i,x in enumerate(xs):
            xx=150+i*dx
            value=cells.get((x,y))
            hiweight=(value-lo)/(hi-lo) if value is not None and hi>lo else 0
            if value is None:
                color='#e7e0d7'
            else:
                base=(246,227,208)
                end=(146,194,174)
                color='#'+''.join(f'{round(a+(b-a)*hiweight):02x}' for a,b in zip(base,end))
            pieces.append(f'<rect x="{xx}" y="{yy}" width="{dx-5}" height="43" rx="9" fill="{color}"/>')
            pieces.append(label(xx+(dx-5)/2,yy+28,'—' if value is None else f'{value:.2f}',15,align='middle'))
    for i,x in enumerate(xs):
        pieces.append(label(150+i*dx+(dx-5)/2,115+48*len(ys),render_x(x),14,align='middle'))
    pieces.append('</svg>')
    (HERE/file_name).write_text(''.join(pieces)+'\n',encoding='utf-8')


def main():
    m=next(x for x in load('research17/valuation.json') if x['company'].startswith('688188'))
    case=m['cases']['base']
    q3=m['basis']['financial_vs_operating']
    product,volume,more=operating_tables()
    write('product-bridge',product)
    write('volume-and-stock',volume)
    write('analysis-ebit-bridge',ebit_bridge())
    write('capital-crosscheck',capital_tables())
    def value(**kw):
        return benchmark(case,m['market'],**kw)
    close(value(),case['per_share'])
    cutoff=m['price']
    v=bisect(lambda x:value(shift=x),cutoff,-.06,.08)
    a=bisect(lambda x:value(margin=x),cutoff,.02,.8)
    close(v,m['critical_points']['volume_reverse']['roots'][0])
    close(a,m['critical_points']['margin_threshold'])
    results=[]
    for days in (0,15,30,45,60):
        wc=.122-m['critical_points']['turnover'][0]['cogs_ratio']*days/365
        root=bisect(lambda x:value(working_share=wc,shift=x),cutoff,-.06,.08)
        results.append(dict(inventory_days_improvement=days,wc_share=wc,value_before_volume=value(working_share=wc),
             required_2027_control_growth=case['rows'][1]['driver_1']+root,price_check=value(working_share=wc,shift=root),
             incremental_sets_relative_to_2025=root*volume[-1]['control_units']))
    write('stock-volume-boundary',results)
    grid=[]
    for change in (-.02,-.01,0,.01,.02):
        for margin in (.435,.45,case['terminal']['margin'],.485,.50,.515):
            grid.append(dict(volume_growth_2027=case['rows'][1]['driver_1']+change,
                             steady_margin=margin,per_share_cny=value(shift=change,margin=margin)))
    write('control-margin-grid',grid)
    draw_grid([(r['volume_growth_2027'],r['steady_margin'],r['per_share_cny']) for r in grid],
        lambda x:f'{x:.2%}',lambda x:f'{x:.2%}','柏楚电子｜量和利如何共同跨过同日收盘',
        '横轴 2027 控制量增长　纵轴 稳定核心营业利润率　格值 元／股　同日收盘 96.20 元','mechanism-grid.svg')
    more.update(cutoff='2026-11-12 SSE', tested_price=cutoff, model_base=value(),
          control_growth_edge=case['rows'][1]['driver_1']+v, volume_shift=v,
          stock_volume_boundary=results, steady_margin_edge=a,
          exact_reinsert_control=value(shift=v),exact_reinsert_margin=value(margin=a),
          excess_cash_bridge=case['bridge'],unknown_service_cost_bucket='未披露，阈值以下单列',
          terminal_roi_required=m['cases']['base']['terminal']['incremental_return'])
    (HERE/'operating-summary.json').write_text(json.dumps(more,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(more,ensure_ascii=False))


if __name__ == '__main__':
    main()
