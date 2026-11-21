"""Cross-format, evidence and frozen-valuation publication checks."""
import argparse
import csv
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import urlopen
from zipfile import ZipFile

from build_long_atlas import BASELINE, OUT, atomic, build, edition_data, json_text, readcsv, readj
from case_model import ROOT, bake
from build_atlas_history import make_rows


class Survey(HTMLParser):
    def __init__(self,html):
        super().__init__()
        self.paragraphs={}
        self.destinations=[]
        self.ids=set()
        self.plots=0
        self.mechanisms=0
        self.active=None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        info=dict(attrs)
        if 'id' in info:
            self.ids.add(info['id'])
        if tag=='a' and 'href' in info:
            self.destinations.append(info['href'])
        if tag=='p' and 'data-prose' in info:
            self.active=info['id']
            self.paragraphs[self.active]=''
        if 'data-data-figure' in info:
            self.plots+=1
        if 'data-mechanism' in info:
            self.mechanisms+=1

    def handle_data(self, data):
        if self.active:
            self.paragraphs[self.active]+=data

    def handle_endtag(self,tag):
        if tag=='p':
            self.active=None


def offline_links(page, relative, members):
    origin='file:///archive/'+relative
    dangling=[]
    for url in page.destinations:
        target=urlsplit(urljoin(origin,url))
        if target.scheme in ('http','https'):
            continue
        file=unquote(target.path.removeprefix('/archive/'))
        if file not in members or target.fragment and file==relative and target.fragment not in page.ids:
            dangling.append(url)
    assert not dangling,(relative,sorted(set(dangling)))


def audit(url=None):
    model,annual,recent,summary=bake()
    assert [len(annual),len(recent),summary['frozen_facts'],summary['old_price_roundtrips'],summary['path_count']]==[65,49,188,62,15]
    newest=readj(OUT/'history-supplement-inputs.json')
    early,pop,older=make_rows(newest)
    new=readcsv(OUT/'historical-reviewstore-receipt.csv')
    assert len(new)==58 and all(r['verifier']=='agent' and r['verification_event'] for r in new)
    assert len(older)==122
    bridge=readcsv(OUT/'002507/channel-current-price.csv')
    old=[x for x in bridge if x['root']=='']
    additional=[x for x in bridge if x['root']!='']
    assert len(old)==5 and len(additional)==9
    assert all(float(x['value_at_root'])==float(x['close']) or abs(float(x['value_at_root'])-float(x['close']))<1e-8 for x in additional)
    expected,counts=edition_data(False)
    parsed=readcsv(OUT/'word-count.csv')
    assert sum(int(x['han']) for x in parsed if x['chapter']=='合计')==sum(x['han'] for x in expected.values())
    urls=set(['/long-atlas/','/long-atlas/compare.html','/long-atlas/offline.zip','/desk/','/research/','/atlas/'])
    package=readj(OUT/'package.json')
    details={}
    with TemporaryDirectory() as tempdir:
        derived=Path(tempdir)
        build(derived)
        with ZipFile(OUT/'offline.zip') as offline, ZipFile(derived/'offline.zip') as reproduced:
            members=set(offline.namelist())
            assert members==set(reproduced.namelist())
            assert all(offline.read(path)==reproduced.read(path) for path in members)
            for path in package['files']:
                if path.endswith(('.html','.csv','.md','.json')) and (derived/path).is_file():
                    assert (derived/path).read_bytes()==(OUT/path).read_bytes(),path
            for relative in ('index.html','compare.html'):
                offline_links(Survey(offline.read(relative).decode()),relative,members)
            for code,d in expected.items():
                base=OUT/code
                a=Survey((base/'index.html').read_text(encoding='utf8'))
                b=Survey(offline.read(code+'/index.html').decode())
                assert a.paragraphs==b.paragraphs==readj(base/'document.json')['paragraphs']==d['paragraphs']
                assert a.plots==b.plots==len(d['figures']) and a.mechanisms==b.mechanisms==4
                offline_links(b,code+'/index.html',members)
                expected_md=['# '+d['name']+'证券投资研究图册']
                for ch in d['chapters']:
                    expected_md.append('## '+ch['title'])
                    expected_md.extend('### '+x['text'] if x['role']=='heading' else x['text'] for x in ch['blocks']
                                       if x['role'] in ('heading','prose'))
                assert (base/'case.md').read_text(encoding='utf8').strip()=='\n\n'.join(expected_md)
                urls.update('/long-atlas/'+code+'/'+f for f in ('','case.md','coverage.csv','document.json','valuation-receipt.json'))
                for item in a.destinations:
                    parsed=urlsplit(urljoin('/long-atlas/'+code+'/',item))
                    if not parsed.scheme and parsed.path.startswith('/'):
                        urls.add(parsed.path+('?' + parsed.query if parsed.query else ''))
                vals=readj(base/'valuation-receipt.json')
                assert all(abs(x['difference'])<1e-8 for x in vals['scenarios'])
                details[code]=dict(han=d['han'],charts=a.plots,mechanisms=a.mechanisms,paragraphs=len(a.paragraphs),
                                   digest=d['digest'],scenarios=d['cases'],asof=d['cutoff'],close=d['close'],
                                   original_annual_periods=len([x for x in annual if x['company'].split('_')[0]==code]))
    if url:
        for route in sorted(urls):
            if route.startswith('/desk/#'):
                continue
            with urlopen(url+route,timeout=8) as response:
                assert response.status==200 and response.read(1),route
    warm=summary['cold_or_current_facts']
    return dict(baseline=BASELINE,companies=details,scope='阶段15–17财务和估值的冻结窗口',
                base_model=summary,warm_or_restored_reviewstore=warm,ledger_snapshot_additions=len(new),
                reviewed_raw_locations=len(older),angel_supplement_years=len(early),pop_lease_supplement_years=len(pop),
                fuling_prior_zero_edges=len(old),fuling_added_reversals=len(additional),
                reproducible_offline_members=len(members),online_routes_checked=len(urls) if url else None)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url')
    p.add_argument('--write',action='store_true')
    a=p.parse_args()
    result=audit(a.url)
    if a.write:
        atomic(OUT/'acceptance.json',json_text(result))
    print(json_text(result))
