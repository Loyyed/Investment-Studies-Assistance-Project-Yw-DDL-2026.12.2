"""Record verified historical disclosure cells under the existing scoped authorization."""
import argparse
from pathlib import Path
import sys

from build_atlas_history import make_rows, manifest, verify_originals
from build_atlas_valuation_notes import TARGET, write_csv
from long_atlas_data import ROOT, readj

HISTORICAL_FIELDS={
 '600298': {'fixed_assets_total','receivables','inventory','payables','customer_advances','finance','cfo_correction'},
 '09992': {'rou_da','operating_lease_cash','financing_lease_cash','rou_da_later_comparative'},
}

def authorized(row):
    return row['metric'] in HISTORICAL_FIELDS[row['company']] or (
        row['company']=='600298' and row['metric']=='cost' and row['period'] in ('2004-FY','2005-FY'))

def review(root):
    from companybench import core
    from source_compat import enable
    enable(core,root)
    return core.ReviewStore

def register(rows, root):
    Store=review(root)
    output=[]
    for code,selected in HISTORICAL_FIELDS.items():
        company,sources=manifest(code)
        store=Store(root/'companies'/company.name)
        before=len(store.facts())
        ledger=store._read()
        delegation=next(d for d in ledger['delegations'] if d['active'] and 'disclosure' in d['kinds'] and
                        '经过原文核验的新增历史原数' in d['statement_original'])
        for r in (r for r in rows if r['company']==code and authorized(r)):
            # Source version and byte integrity have been independently checked before registering.
            rid=f"V22-{r['period'][:4]}-{r['metric'].upper().replace('_','-')}"
            caption=r['label'].strip()
            location=f"PDF物理第{r['page']}页，{caption}，第{r['column']}数值列，{r['column_header']}"
            if r.get('line'):
                location+=f"，文本行{r['line']}"
            record=dict(id=rid,kind='disclosure',state='Unknown',value=str(r['value']),claim=caption,
                scope=dict(period=r['period'],entity=company.name.split('_',1)[1],basis='历史合并原披露',
                           definition=caption,unit=r['unit'],currency='CNY'),
                sources=[dict(source_id=r['source'],location=location)],
                support_boundary='保留报告本期或指明比较版本。派生利润、资本回报和条件估值另表计算。')
            if rid not in ledger['records']:
                store.upsert(record)
            elif ledger['records'][rid]!=record:
                raise AssertionError((company.name,rid,'需要复核记录版本'))
            view=next(v for v in store.records() if v['id']==rid)
            if view['effective_state']!='Fact':
                if view['issues']:
                    raise ValueError((rid,view['issues']))
                store.confirm(rid,'agent',f"原件指纹和 PDF 物理页、科目、列头及单位已核对。{location}为{r['value']}{r['unit']}。",
                              delegation['id'],view['binding'])
        assert store.history_valid()
        state={r['id']:r for r in store.facts()}
        for r in (r for r in rows if r['company']==code and authorized(r)):
            rid=f"V22-{r['period'][:4]}-{r['metric'].upper().replace('_','-')}"
            item=state[rid]
            output.append(dict(company=code,fact_id=rid,period=r['period'],metric=r['metric'],value=r['value'],
                               unit=r['unit'],source=r['source'],binding=item['binding'],
                               verification_event=item['confirmation_event'],verifier=item['verifier'],
                               state_at_verification=item['effective_state'],needs_current_binding=True))
        print(code,'facts',before,'->',len(state))
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--register',action='store_true',required=True)
    args=parser.parse_args()
    sys.path[:0]=[str(ROOT/'shared/runtime'),str(ROOT/'app')]
    source=readj(TARGET/'history-supplement-inputs.json')
    _,_,rows=make_rows(source)
    verify_originals(rows,ROOT)
    report=register(rows,ROOT)
    write_csv(TARGET/'historical-reviewstore-receipt.csv',report)
    print('historical ReviewStore receipts',len(report))

if __name__=='__main__':
    main()
