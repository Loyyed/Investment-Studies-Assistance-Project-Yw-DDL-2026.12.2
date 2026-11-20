"""Recompute the old accounting bridge and the rent-adjusted cash bridge."""
import argparse
from decimal import Decimal as D
from hashlib import sha256
import sys
from pathlib import Path

from build_atlas_valuation_notes import TARGET, write_csv
from long_atlas_data import ROOT, readj

FIELDS_POP={
    'rou_da':('lease_note_page','使用權資產折舊費用合計'),
    'lease_interest_expense':('lease_note_page','利息開支'),
    'short_lease_expense':('lease_note_page','短期租賃開支'),
    'variable_lease_expense':('lease_note_page','未計入負債的可變租賃開支'),
    'operating_lease_cash':('lease_note_page','租賃作為經營活動之現金流出'),
    'financing_lease_cash':('lease_note_page','租賃作為融資活動之現金流出'),
    'operating_cash_before_tax_and_interest':('cfo_page','經營所得現金'),
}

def make_rows(data):
    angel=[]
    pop=[]
    evidence=[]
    for item in data['angel']:
        t={k:D(v['value']) for k,v in item['cells'].items()}
        margin=t['revenue']-t['cost']
        ebit=t['operating_profit']+t['finance']
        implied=margin-t['tax_surcharge']+t['other_operating_profit']-t['sales']-t['admin']
        assert abs(ebit-implied)<D('.05'), (item['period'],ebit,implied)
        wc=t['receivables']+t['inventory']-t['payables']-t['customer_advances']
        capital=t['fixed_assets_total']+wc
        cfo=D(str(item['base_cfo_m']))
        if item['period']=='2005-FY':
            available=D(data['angel_cfo_correction']['value'])/10**6
        else:
            available=cfo
        angel.append(dict(period=item['period'],unit='百万元人民币',
                     **{k:v/10**6 for k,v in t.items()},gross_m=margin/10**6,
                     analysis_ebit_m=ebit/10**6,analysis_ebit_margin=ebit/t['revenue'],
                     p_and_l_residual=(ebit-implied)/10**6,wc_narrow_m=wc/10**6,
                     capital_narrow_m=capital/10**6,capital_turnover=t['revenue']/capital,
                     pretax_roic_proxy=ebit/capital,pretax_roic_25pct_tax_proxy=ebit*D('.75')/capital,
                     cfo_frozen_m=cfo,cfo_preferred_m=available,capex_frozen_m=item['base_capex_m'],
                     preferred_cfo_after_cash_capex_m=available-D(str(item['base_capex_m'])),
                     tag='旧会计制度经营资本子集与研究代理',
                     breaks='2004采用2005报表比较栏逐行重排；2005更正现金留双版本；2007新准则分段。'))
        for k,v in item['cells'].items():
            evidence.append(dict(company='600298',period=item['period'],metric=k,unit='人民币元',
                                 checked=data['checked_date'],**v))
    for i,r in enumerate(data['pop']):
        total=r['operating_lease_cash']+r['financing_lease_cash']
        normalized=r['core_ifrs_ebit']+r['rou_da']+r['short_lease_expense']+r['variable_lease_expense']-total
        cfo_after=r['cfo']-r['capex']-r['financing_lease_cash']
        assert r['cfo']>0 and total>0
        subset=dict(**r,total_cash_rent=total,after_rent_core_ebit=normalized,after_rent_core_margin=normalized/r['revenue'],
                    after_rent_cfo_and_capex=cfo_after,cash_rent_ratio=total/r['revenue'],
                    double_count_avoid='经营分类租赁已经过CFO；仅追加扣融资分类。费用到现金的桥不把租赁利息费用当成第二支现金。')
        if r['period']=='2022-FY':
            later=data['pop_2022_rou_as_later_comparative']['later_comparative']
            subset['rou_later_comparative']=later
            subset['after_rent_margin_later_comparative']=(normalized-r['rou_da']+later)/r['revenue']
        pop.append(subset)
        for k,(page,row) in FIELDS_POP.items():
            evidence.append(dict(company='09992',period=r['period'],metric=k,unit='人民币千元',value=r[k],
                checked=data['checked_date'],source=r['id'],sha256=r['sha256'],available=r['date'],url=r['url'],
                page=r[page],label=row,column=1,column_header='本年已审计合并'))
    note=data['angel_cfo_correction']
    evidence.append(dict(company='600298',period=note['period'],metric='cfo_correction',unit='人民币元',
                    checked=data['checked_date'],source=note['id'],sha256=note['sha256'],available=note['date'],
                    url=note['url'],page=note['page'],label=note['line'],value=note['value'],column=1,column_header=note['column']))
    r=data['pop_2022_rou_as_later_comparative']
    p=data['pop'][3]
    evidence.append(dict(company='09992',period=r['year'],metric='rou_da_later_comparative',unit='人民币千元',
                    checked=data['checked_date'],source=r['later_id'],sha256=p['sha256'],available=p['date'],
                    url=r['later_url'],page=r['page'],label='使用權資產折舊費用合計',value=r['later_comparative'],
                    column=2,column_header='2022 比较列'))
    return angel,pop,evidence


def manifest(code):
    path=next((ROOT/'companies').glob(code+'_*'))
    return path,{x['id']:x for x in readj(path/'sources/manifest.json')['sources']}


def verify_originals(evidence, raw_workspace):
    import re
    import pypdfium2 as pdf
    matches={}
    for c in ('600298','09992'):
        company,sources=manifest(c)
        for row in (r for r in evidence if r['company']==c):
            source=sources[row['source']]
            file=raw_workspace/'companies'/company.name/source['path']
            if file not in matches:
                assert sha256(file.read_bytes()).hexdigest()==row['sha256']==source['sha256']
                matches[file]=pdf.PdfDocument(file)
            page=matches[file][row['page']-1]
            formatted=f"{D(str(row['value'])):,}"
            text=page.get_textpage().get_text_range()
            page.close()
            assert formatted in text or str(row['value']) in text,(row['source'],row['page'],formatted)
            if row.get('line') and isinstance(row['line'],int):
                line=text.splitlines()[row['line']-1]
                assert formatted in line,(row['source'],row['page'],line)
    for document in matches.values():
        document.close()
    print('original pages verified',len(evidence),'across',len(matches),'files')


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--verify-originals',type=Path)
    args=a.parse_args()
    data=readj(TARGET/'history-supplement-inputs.json')
    angel,pop,evidence=make_rows(data)
    if args.verify_originals:
        verify_originals(evidence,args.verify_originals)
    write_csv(TARGET/'600298'/'early-capital.csv',angel)
    write_csv(TARGET/'09992'/'historical-lease-cash.csv',pop)
    for code in ('600298','09992'):
        write_csv(TARGET/code/'historical-original-locators.csv',[r for r in evidence if r['company']==code])

if __name__=='__main__':
    main()
