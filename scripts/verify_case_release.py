"""Case publication tests for a working tree or a clean clone."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.request import Request,urlopen

from build_cases import OUT, ROOT, build
from check_super_atlas import compare


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate(url=None):
    build(OUT,check=True)
    stage=compare(ROOT,url)
    registered=read(OUT/'case-package.json')
    atlas=read(ROOT/'docs/super-atlas/atlas-editable.json')
    companies={}
    for code in registered['companies']:
        work=OUT/code
        case=read(work/'model.json')
        card=next(c for c in atlas['cards'] if c['id']=='company-'+code)
        sections=card['feature']['sections']
        assert any(c['id']=='deepcase' for c in sections)
        plot=next(c['chart'] for c in sections if c['id']=='price')
        assert plot['series'][0]['values']==[case['cases'][k]['per_share']
            for k in ('stress','base','improve')]+[case['close']]
        with (work/'forecast.csv').open(encoding='utf-8-sig',newline='') as f:
            table=list(csv.DictReader(f))
        for k,v in case['cases'].items():
            found=[r for r in table if r['scenario']==k and 2027<=int(r['year'])<=2031]
            assert len(found)==5
            for row,expected in zip(found,v['rows'][1:6]):
                assert float(row['model_cash_after_date'])==expected['model_cash_after_date']
        for f in ('case.md','report-map.md','independent-review.md'):
            assert (work/f).stat().st_size>600
        html=(work/'index.html').read_text(encoding='utf-8')
        assert '双变量反解' in html and f'{case["cases"]["base"]["per_share"]:.2f}' in html
        companies[code]=dict(
            model=hashlib.sha256((work/'model.json').read_bytes()).hexdigest(),
            quoted=case['close'],base=case['cases']['base']['per_share'],
            value_bridge_delta=sum(x['delta'] for x in case['stage17_to_case']),
            new_reverse_count=sum(len(r['roots']) for r in case['tests']['boundary']))
    assert len(companies)==5
    with (OUT/'acceptance.csv').open(encoding='utf-8-sig',newline='') as f:
        matrix=list(csv.DictReader(f))
        assert len(matrix)==60
        assert all((OUT/r['file']).is_file() for r in matrix)
    route_count=0
    if url:
        # Issuer originals are tested via hash restore and selected direct source checks.
        for route in ['/desk/','/desk/compare/','/cases/','/atlas/','/atlas/compare/',
                      '/atlas/document.json','/atlas/offline.html']+[
                f'/cases/{c}/{f}' for c in companies for f in ('','case.md','forecast.csv','model.json','sensitivity.svg')]:
            with urlopen(Request(url+route),timeout=15) as r:
                assert r.status==200 and r.read(8),route
            route_count+=1
    return dict(stage17=stage,companies=companies,matrix_rows=len(matrix),publication_routes=route_count,
                case_manifest=len(registered['files']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url')
    args=p.parse_args()
    print(json.dumps(validate(args.url),ensure_ascii=False,indent=2))
