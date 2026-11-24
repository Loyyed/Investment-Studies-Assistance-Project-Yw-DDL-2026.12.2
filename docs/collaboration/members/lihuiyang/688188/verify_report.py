"""Recalculate archived cash identities and validate the personal report's local links.

This checks calculations, not the empirical truth of forecast assumptions or student review.
Run after build_report.py. Add --with-pdf to check the locally available annual original.
"""
from pathlib import Path
from decimal import Decimal as D
from urllib.parse import unquote, urlsplit
import argparse
import csv
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
ARCHIVE = ROOT / '报告留存处/柏楚电子证券投资图册'
REPORT = ROOT / '报告留存处/2026-11-24_SSE-688188_柏楚电子证券投资分析报告Version2.md'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def near(actual, expected, tol=1e-8):
    assert abs(actual - expected) < tol, (actual, expected, tol)


def calculate():
    model = json.loads((ARCHIVE / 'data/model.json').read_text(encoding='utf-8'))
    receipt = model['receipt']
    cases = {}
    for name, case in model['scenarios'].items():
        rate, growth = case['wacc'], case['growth']
        assert rate > growth
        assert [row['year'] for row in case['path']] == list(range(2026, 2036))
        for row in case['path']:
            near(row['t'], 49/365 + row['year']-2026)
            if row['year']>2026:
                previous=case['path'][row['year']-2027]
                near(row['delta_nwc'],row['nwc']-previous['nwc'])
                near(row['valued_cash'],row['fcff'])
            core = row['revenue'] - sum(row[k] for k in (
                'cost', 'sales', 'admin', 'research', 'surcharge', 'incremental_service'))
            core += row['normalized_operating_saving']
            near(core, row['core_ebit'])
            near(row['core_ebit'] - row['cash_tax'], row['nopat'])
            near(row['ar'] + row['inventory'] - row['ap'] + row['other_nwc'], row['nwc'])
            cash = row['nopat'] + row['da'] - row['lease_net_cash']
            # cash_capex is total cash investment; project_cash_capex is its disclosed subset.
            assert row['cash_capex'] >= row['project_cash_capex']
            cash -= row['cash_capex'] + row['delta_nwc']
            near(cash, row['fcff'])
            near(row['valued_cash'] / (1 + rate) ** row['t'], row['pv'])
            assert all(row[k] == 0 for k in (
                'arc_weld_increment', 'battery_laser_increment', 'precision_increment'))
        q4 = case['q4']
        q4_cash = q4['core_ebit'] * (1 - 0.13) + q4['da_proxy']
        q4_cash -= q4['capex'] + q4['lease_cash']
        q4_cash -= q4['closing_modeled_wc'] - q4['opening_trade_wc']
        near(q4_cash, q4['fcff_proxy'])
        near(q4['stub_fraction'], 49 / 92)
        near(q4_cash * q4['stub_fraction'], case['path'][0]['valued_cash'])
        explicit = sum(row['valued_cash'] / (1 + rate) ** row['t'] for row in case['path'])
        stable = case['stable_2036']
        reinvest = stable['nopat'] * growth / case['roic']
        terminal_cash = stable['nopat'] - reinvest
        near(reinvest, stable['reinvestment'])
        near(terminal_cash, case['terminal_fcff'])
        terminal = terminal_cash / (rate - growth) / (1 + rate) ** case['path'][-1]['t']
        enterprise = explicit + terminal
        equity = enterprise + receipt['cash_bridge']
        price = equity / (receipt['shares'] / 1_000_000)
        for actual, expected in ((explicit, case['explicit_pv']),
                                 (terminal, case['terminal_pv']),
                                 (enterprise, case['enterprise_value']),
                                 (equity, case['equity_value']), (price, case['price'])):
            near(actual, expected)
        cases[name] = dict(explicit_pv_m=explicit, terminal_pv_m=terminal,
                           terminal_share=terminal / enterprise,
                           equity_value_m=equity, per_share_cny=price,
                           price_residual=price-case['price'])
    assert [f"{cases[k]['per_share_cny']:.2f}" for k in ('stress','base','improve')] == ['42.02','81.81','134.83']
    samples = {}
    for inventory, ar in ((D(110),D(45)),(D(150),D(65))):
        capital = D(50)*(inventory-D(50))/D(365)+D(100)*ar/D(365)
        cash = (D(100)-D(50)-D(4)-D(2)-D(5))*(1-D('.13'))-D(3)-capital
        samples[f'{inventory}/{ar}'] = str(cash)
    with (ARCHIVE/'data/bundle-cash-thresholds.csv').open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            key=f"{row['inventory_days']}/{row['ar_days']}"
            if row['gross_margin']=='0.5' and row['service_scenario']=='5' and key in samples:
                assert abs(D(samples[key])-D(row['first_cohort_cash'])) < D('1e-12')
    build=json.loads((HERE/'build-receipt.json').read_text(encoding='utf-8'))
    for row in build['external_estimate']:
        profit=D(row['profit_anchor_2025_yi'])*(1+D(row['growth']))**int(row['years'])
        assert profit==D(row['profit_2030_yi'])
        assert profit*D(row['pe'])/D(row['shares_yi'])==D(row['future_price_cny'])
    assert digest(REPORT)==build['report_sha256']
    assert digest(ARCHIVE/'data/model.json')==build['model_sha256']
    return dict(cases=cases, first_cohort_cash_samples=samples,
                external_estimate=build['external_estimate'], cash_bridge_m=receipt['cash_bridge'])


def links():
    docs=[REPORT, HERE.parent/'READMEVersion2.md', *HERE.glob('*.md')]
    count=0
    for path in docs:
        body=path.read_text(encoding='utf-8')
        for url in re.findall(r'!?\[[^\]]*\]\(([^)\n]+)\)',body):
            split=urlsplit(url)
            if split.scheme or split.netloc:
                continue
            if split.path:
                target=(path.parent/unquote(split.path)).resolve()
                assert target.is_file(), (str(path.relative_to(ROOT)),url)
                count+=1
        if path==REPORT:
            anchors=re.findall(r'<a name="([^"]+)"',body)
            assert len(anchors)==len(set(anchors))
            heading_anchors={re.sub(r'[^\w -]','',title.lower()).replace(' ','-')
                             for title in re.findall(r'^#{1,6} (.+)$',body,re.M)}
            for fragment in re.findall(r'\]\(#([^)]+)\)',body):
                assert fragment in set(anchors)|heading_anchors, fragment
            assert re.findall(r'^## 第 (\d) 章',body,re.M)==list('123456789')
            assert len(re.findall(r'!\[',body))==14
            assert '```mermaid' not in body
    return dict(local_files=count, documents=len(docs), figures=14, report_anchors=len(anchors))


def original_pdf():
    from pypdf import PdfReader
    path=ROOT/'companies/688188_柏楚电子/sources/raw/01_年报/2026-04-10_2025年年度报告_1225091045.pdf'
    assert digest(path)=='e12688b3c2e80e63fae0008983426c644a0ca5bc0da6bed30f9b45f635ecfed2'
    pdf=PdfReader(path)
    probes={8:['2,195,632,312.92','1,112,547,607.75','1,104,320,726.22','19.26'],
            25:['525','40.92'],126:['1,130,626,497.82','341,329,531.46'],
            130:['35,202,823.72','1,104,320,726.22'],
            2:['748,965,430.64','556,671,299.26','67.32','拟派发'],
            113:['53,339,003','41,718,851','36,194,281','32,384,156','22,859,445']}
    for page, tokens in probes.items():
        text=re.sub(r'\s+','',pdf.pages[page-1].extract_text())
        for token in tokens:
            assert token in text, (page,token)
    return dict(sha256=digest(path),physical_pages=list(probes),
                exact_value_probes=sum(map(len,probes.values())),role='Agent original-page check')


def main(with_pdf=False):
    sys.path.insert(0,str(ROOT/'scripts'))
    from check_super_atlas import compare
    result=dict(status='pending-local-links',research_date='2026-11-24',valuation_date='2026-11-12',
                calculations=calculate(), frozen_regression=compare(ROOT,None))
    result['original_pdf']=original_pdf() if with_pdf else 'not requested in this run'
    result['report_sha256']=digest(REPORT)
    result['limitations']='Checks cash identities, archived outputs and local files; not parameter validation, live ReviewStore, human review, or rendered PDF page count.'
    # Make the receipt's own documentation link resolvable, without claiming success early.
    (HERE/'verification-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    result['links']=links()
    result['status']='passed'
    (HERE/'verification-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--with-pdf',action='store_true')
    main(args.parse_args().with_pdf)
