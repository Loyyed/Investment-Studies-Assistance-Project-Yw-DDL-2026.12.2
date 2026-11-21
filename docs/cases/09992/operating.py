"""Rebuild POP MART's revenue/cash bridges and invert the frozen HKD close."""
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


def delta_table(labels, before, after, locator):
    return [dict(group=k,million_cny_2025H1=a/1000,million_cny_2026H1=b/1000,
          delta_m=(b-a)/1000,yoy=b/a-1, source=locator, tag='原披露及算术')
          for k,a,b in zip(labels,before,after)]


def revenue_bridges():
    types = ('零售门店','机器商店','线上','批发及其他')
    regions = [
        ('PRC',18,[4405948,678298,2937255,261311],[6089686,778953,4778746,553124]),
        ('亚太不含PRC',21,[1492991,32597,1069214,256100],[1716171,56523,643551,158800]),
        ('美洲',23,[736961,105429,1326565,95927],[903063,103944,722144,162486]),
        ('欧洲及其他',25,[272110,4417,164963,36190],[403066,11106,67631,23927])]
    geographic=[]
    for name,page,before,after in regions:
        for r in delta_table(types,before,after,f'2026中报物理p{page}，RMB千元两列'):
            geographic.append(dict(region=name,**r))
    ip=[
     ('THE MONSTERS',4814017,4454361),('星星人',389363,2649969),('CRYBABY',1218170,1632570),
     ('DIMOO',1105135,1619217),('SKULLPANDA',1220504,1551211),('HIRONO',728420,1008855),
     ('MOLLY',1357248,900631),('Zsiga',211256,298341),('其他艺术家IP',1184452,1174314),
     ('授权IP',1524840,1771199),('外采及其他',122871,112253)]
    by_ip=delta_table(*zip(*ip),'2026中报物理p26，2025及2026 H1未审人民币千元')
    for rows in (geographic,by_ip):
        close(sum(r['million_cny_2025H1'] for r in rows),13876.276)
        close(sum(r['million_cny_2026H1'] for r in rows),17172.921)
    stores=[]
    for scope,old,new,old_count,new_count in [
        ('PRC 门店整体',4405.948,6089.686,443,455),
        ('中国大陆门店',3648.359,5427.444,409,419)]:
        a,b=old/old_count,new/new_count
        change_number=(new_count-old_count)*(a+b)/2
        change_yield=(b-a)*(old_count+new_count)/2
        close(change_number+change_yield,new-old)
        stores.append(dict(scope=scope,count_at_2025H1=old_count,count_at_2026H1=new_count,
             sales_2025H1=old,sales_2026H1=new,exit_store_sales_proxy_2025=a,exit_store_sales_proxy_2026=b,
             sales_per_endpoint_store_gain=b/a-1,change_count_m=change_number,
             change_revenue_yield_and_cohort_m=change_yield,
             note='中报p19口径，期末门店作分母；店效、地址、开业时间、折扣、结构未拆'))
    return geographic,by_ip,stores


def costs_and_cash():
    inputs= [
        ('入销货成本存货',3272871,4303215),('员工',992685,1405025),('运输物流',784667,754346),
        ('短租及可变租金',513331,673120),('电商佣金服务',642451,561961),('使用权折旧',254184,451934),
        ('营销',400899,444073),('授权费用',451171,376247),('PPE折旧',177571,301991),
        ('税金附加',142314,206207),('银行手续费',141094,149496),('无形资产摊销',77637,67336),
        ('存货减值',4302,22806),('审计费',1700,1800),('其他',221330,345273)]
    rows=delta_table(*zip(*inputs),'2026中报物理p88附注6；费用性质包含交叉归属')
    for col,total in [('million_cny_2025H1',8078.207),('million_cny_2026H1',10064.830)]:
        close(sum(r[col] for r in rows),total)
    recent=[r for r in load('research15/interim.json') if r['company'].startswith('09992') and
                r['period'] in ('2025-H1','2026-H1')]
    cash_t=[]
    for r,lease in zip(recent,[(254.184,513.331,433.149,263.592),(451.934,673.120,708.255,502.889)]):
        a,s,o,f=lease
        val,b=r['cumulative'],r['endpoint']
        gross=val['revenue']-val['cost']
        core=gross-val['sales']-val['admin']
        adjusted=core+a+s-o-f
        actual_lease=o+f
        capex=val['capex']+val['intang_capex']
        cash_t.append(dict(period=r['period'],revenue=val['revenue'],reported_cogs=val['cost'],gross=gross,
             sales_expense=val['sales'],admin_expense=val['admin'],reported_ebit=val['operating_profit'],
             analysis_ifrs_ebit=core,net_other_in_report_ebit=val['operating_profit']-core,
             rou_da_addback=a,variable_and_short_accounting_addback=s,operating_lease_cash=o,financing_lease_cash=f,
             cash_rent=actual_lease,after_lease_cash_ebit=adjusted,after_lease_margin=adjusted/val['revenue'],
             cash_tax_paid=val['cash_tax'],group_cfo=val['cfo'],cash_capex=capex,
             cfo_after_fixed_lease_and_capex=val['cfo']-f-capex,
             inventory=b['inventory'],trade_recv=b['ar'],trade_pay=b['ap'],contract_liab=b['advance'],
             wc_partial=b['inventory']+b['ar']-b['ap']-b['advance'],
             source='2026中报p66/69–70/88/102；RMB百万元'))
    return rows,cash_t


def benchmark(m, half_factor=None, turns=None, rent=1, discount_margin=0):
    """Independently rebuild the frozen cash-rent forecast and linked H2 turnover."""
    case=m['cases']['base']; pp=case['rows']; stub=pp[0]; future=pp[1:]; T=case['terminal']
    h1, original_h2=stub['h1_actual'],stub['rest_revenue']
    h2_prior=m['critical_points']['ref_h2_2025']
    h2=original_h2 if half_factor is None else h2_prior*half_factor
    tax=stub['cash_tax']/stub['operating_profit']
    floor=stub['wc']
    reference=m['critical_points']['group_h1_inventory_turn'][1]
    h1_stock, cogs_ratio = 6101.530,5207.181/17172.921
    def stock(turn):
        return max(0,4*h2*cogs_ratio/turn-h1_stock)
    wc_percent=max(0,.135+((stock(turns)-stock(reference))/(h1+h2) if turns else 0))
    wc=max(floor,(h1+h2)*wc_percent)
    proportional=(h1+h2)/stub['revenue']
    rent_stub=rent*(stub['cash_rent_fixed']+stub['cash_rent_operating']*h2/original_h2)
    before_rent=(stub['rest_ebit']+stub['cash_rent_fixed']+stub['cash_rent_operating'])/original_h2
    ebit=h2*(before_rent+discount_margin)-rent_stub
    reported_stub=stub['model_cash_after_date']
    stub_fcff=reported_stub+((ebit-stub['rest_ebit'])*(1-tax)+
       (h2/original_h2-1)*stub['rest_da']-(wc-stub['wc']))*stub['stub_fraction']
    discount=case['wacc']; pv=stub_fcff/(1+discount)**stub['t']
    target_rows=[]
    for r in future:
        rev=r['revenue']*proportional
        ebit=rev*(r['margin_before_cash_rent']+discount_margin)-rent*(
           r['cash_rent_fixed']+r['cash_rent_operating']*proportional)
        new_wc=max(rev*wc_percent,wc*.91)
        invest=proportional*(r['cash_capex']-r['depreciation'])+new_wc-wc
        target_rows.append(dict(t=r['t'],transition=r['transition'],nopat=ebit*(1-tax),invest=invest))
        wc=new_wc
    stable=target_rows[-1]['nopat']*(1+T['growth'])
    roi=T['incremental_return']
    for a,b in zip(target_rows,target_rows[1:]+[{'nopat':stable}]):
        investment=a['invest']*(1-a['transition'])+max(0,(b['nopat']-a['nopat'])/roi)*a['transition']
        pv+=(a['nopat']-investment)/(1+discount)**a['t']
    pv+=stable*(1-T['growth']/roi)/(discount-T['growth'])/(1+discount)**target_rows[-1]['t']
    price=(pv+case['bridge']['bridge_net'])*1e6/m['market']['shares']/m['market']['fx']
    return dict(price=price,h2=h2,stock_difference_m=(stock(turns)-stock(reference) if turns else 0),
        cash_rent_h2_m=rent_stub,yearend_wc_share=wc_percent)


def edge(m, turns, rent, margin):
    low,high=.25,.85
    target=m['price']
    fl=benchmark(m,low,turns,rent,margin)['price']
    fh=benchmark(m,high,turns,rent,margin)['price']
    if not (fl<=target<=fh):
        return dict(low_price=fl,high_price=fh,low_gap=fl-target,high_gap=fh-target,root=None)
    for _ in range(74):
        mid=(low+high)/2
        if benchmark(m,mid,turns,rent,margin)['price']<target:
            low=mid
        else:
            high=mid
    root=(low+high)/2
    r=benchmark(m,root,turns,rent,margin)
    close(r['price'],target)
    r.update(root=root,low_price=fl,high_price=fh,low_gap=fl-target,high_gap=fh-target)
    return r


def capacity_grid(m):
    original=m['critical_points']
    h2p=original['ref_h2_2025']
    q4grid=[]
    for turn in (1.35,original['group_h1_inventory_turn'][1],2.2):
        for rent in (.85,1,1.15):
            for margin in (-.03, -.015, 0, .015):
                r=edge(m,turn,rent,margin)
                for weight in (.35,.50,.65):
                    for decline in (.45,.50):
                        q3=h2p*weight*(1-decline)
                        q4=(r['h2']-q3) if r['root'] is not None else None
                        q4grid.append(dict(h2_turn=turn,rent_index=rent,incremental_gross_margin=margin,
                             assumed_Q3_weight=weight,disclosed_decrease_endpoint=decline,
                             implied_Q3_m=q3,breakeven_Q4_m=q4 if q4 is not None and q4>=0 else None,
                             algebraic_Q4_m=q4,price_at_edge=r.get('price'),boundary_low_price=r['low_price'],
                             boundary_high_price=r['high_price'],required_H2_factor=r['root'],
                             cash_rent_h2_m=r.get('cash_rent_h2_m'),rmb_to_hkd_divisor=m['market']['fx'],
                             status=('搜索范围内无等值根' if q4 is None else
                                 '非负Q4无等值解' if q4<0 else '现价可回代')))
                if margin==0:
                    old=next(x for x in original['rows'] if x['h2_inventory_turn']==turn and x['rent_multiplier']==rent)
                    close(old['h2_factor'],r['root'])
    write('q4-cash-threshold-grid',q4grid)
    return q4grid


def capital_table(m):
    records=sorted((r for r in load('research15/annual.json') if r['company'].startswith('09992')),
                   key=lambda r:r['period'])
    leases={r['period']:r for r in m['basis']['lease_history']}
    output=[]
    prev_wc=None
    prev_capital=None
    prev_nopat=None
    for r in records:
        v,d=r['values'],r['derived']
        lease=leases.get(r['period'],{})
        vest=[v.get(k) for k in ('inventory','ar','ap','advance')]
        wc=vest[0]+vest[1]-vest[2]-vest[3] if all(x is not None for x in vest) else None
        cap_items=[v.get(k) for k in ('ppe','intangible')]
        if r['period']=='2025-FY':
            wc=5472.839+921.240-1858.216-393.119  # 2025 AR physical pp.221–222
            cap_items=[1417.556,208.665]
        capital=wc+sum(cap_items) if wc is not None and all(x is not None for x in cap_items) else None
        ebit=lease.get('cash_scope_ebit')
        nopat=ebit*.75 if ebit is not None else None
        d_a_items=[v.get(k) for k in ('depreciation','amortization')]
        annual_da={'2024-FY':286.481+124.024,'2025-FY':398.202+127.050}  # 2025 AR physical p.283
        da=annual_da.get(r['period'],sum(d_a_items) if all(x is not None for x in d_a_items) else None)
        delta=wc-prev_wc if wc is not None and prev_wc is not None else None
        cash_capex=v['capex']+v['intang_capex'] if v.get('capex') is not None and v.get('intang_capex') is not None else None
        financed=lease.get('lease_financing_cash')
        fcff=nopat+da-delta-cash_capex if all(x is not None for x in (nopat,da,delta,cash_capex)) else None
        avg=(capital+prev_capital)/2 if capital is not None and prev_capital is not None else None
        inc=((nopat-prev_nopat)/(capital-prev_capital) if all(x is not None for x in
             (nopat,prev_nopat,capital,prev_capital)) and capital>prev_capital else None)
        output.append(dict(period=r['period'],group_revenue=v['revenue'],report_ebit=v.get('operating_profit'),
            core_ifrs_ebit=d.get('adjusted_ebit'),cash_lease_ebit=ebit,op_cash_tax_25pct_proxy=ebit*.25 if ebit is not None else None,
            operating_after_rent_nopat=nopat,da_ex_rou_if_visible=da,inventory=v.get('inventory'),
            trade_working_capital_subset=wc,delta_trade_wc_subset=delta,
            ppe_intangible_plus_trade_wc_subset=capital,asset_turnover_proxy=(v['revenue']/avg if avg else None),
            cash_lease_roic_proxy=(nopat/avg if nopat is not None and avg else None),incremental_cash_roic_proxy=inc,
            historical_noncomparable_lease_mixed_roic=d.get('store_roic_proxy'),
            historical_noncomparable_incremental_return=d.get('incremental_return_proxy'),
            cash_capex=cash_capex,ifrs_cfo=v.get('cfo'),financing_lease_cash=financed,
            ifrs_cfo_less_capex_and_financed_lease=(v['cfo']-cash_capex-financed if all(x is not None for x in
                        (v.get('cfo'),cash_capex,financed)) else None),cash_lease_fcff_proxy=fcff,
            source=r['source']+' / 2025年报p221–222、283、301同列补充限2024/25',tag='窄口径资本、现金税与ROIC代理；空项待补；百万元人民币'))
        prev_wc,prev_capital,prev_nopat=wc,capital,nopat
    return output


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
    m=next(x for x in load('research17/valuation.json') if x['company'].startswith('09992'))
    geo,ip,stores=revenue_bridges()
    costs,cash=costs_and_cash()
    write('region-channel-bridge',geo)
    write('ip-contribution',ip)
    write('store-cohort-proxy',stores)
    write('expense-nature',costs)
    write('cash-rent-ebit-cfo',cash)
    write('capital-crosscheck',capital_table(m))
    baseline=benchmark(m)['price']
    close(baseline,m['cases']['base']['per_share'])
    grid=capacity_grid(m)
    chosen=[r for r in grid if r['h2_turn']==m['critical_points']['group_h1_inventory_turn'][1] and r['assumed_Q3_weight']==.5 and r['disclosed_decrease_endpoint']==.5]
    draw_grid([(r['rent_index'],r['incremental_gross_margin'],r['breakeven_Q4_m']/100 if r['breakeven_Q4_m'] is not None else None) for r in chosen],
        lambda x:f'{x:.2f}×',lambda x:f'{x:+.1%}','泡泡玛特｜持续毛利和现金租金改变Q4门槛',
        '横轴 租金乘数　纵轴 持续毛利变化　格值 亿元人民币　Q3权重50%、同比−50%','mechanism-grid.svg')
    official=load('super-atlas/follow-up.json')
    buybacks=[d for d in official if d['company'].startswith('09992') and d['title'].startswith('翌日')]
    write('subsequent-buybacks',[{k:x.get(k) for k in ('date','when','shares','cash','url','sha256',
                     'asof_scope','valuation_changed')} for x in buybacks])
    anchor=[r for r in grid if r['assumed_Q3_weight']==.5 and r['rent_index']==1 and
                r['h2_turn']==m['critical_points']['group_h1_inventory_turn'][1]]
    summary=dict(model_base=baseline,close_date='2026-11-12 HKEX',close_price=m['price'],
       grouped_PRC_m=sum(r['delta_m'] for r in geo if r['region']=='PRC'),
       grouped_overseas_m=sum(r['delta_m'] for r in geo if r['region']!='PRC'),
       overseas_offline_retail_m=sum(r['delta_m'] for r in geo if r['region']!='PRC' and r['group']=='零售门店'),
       overseas_online_m=sum(r['delta_m'] for r in geo if r['region']!='PRC' and r['group']=='线上'),
       top_IP_delta_m=ip[0]['delta_m'],ex_monsters_group_growth=(
           (17172.921-ip[0]['million_cny_2026H1'])/(13876.276-ip[0]['million_cny_2025H1'])-1),
       Twinkle_share_of_total_growth=ip[1]['delta_m']/(17172.921-13876.276),
       ex_two_IP_growth=(17172.921-ip[0]['million_cny_2026H1']-ip[1]['million_cny_2026H1'])/
                    (13876.276-ip[0]['million_cny_2025H1']-ip[1]['million_cny_2025H1'])-1,
       sensitivity_rows=len(grid),anchor_25Q3_share_50=anchor,
       base_h2_discount_only=[dict(additional_persisted_margin=margin,per_share_hkd=benchmark(m,discount_margin=margin)['price'])
                              for margin in (-.03,-.015,0,.015)],
       post_cutoff_reported_shares=sum(x['shares'] for x in buybacks),
       post_cutoff_reported_paid_hkd=sum(x['cash'] for x in buybacks),explanation='披露、算术与条件边界；无Fact写入')
    (HERE/'operating-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == '__main__':
    main()
