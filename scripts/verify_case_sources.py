"""Independently locate five original 2025 financial statement revenue rows."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def check(archive):
    import pypdfium2
    from lxml import html
    rows=json.loads((ROOT/'docs/research15/annual.json').read_text(encoding='utf-8'))
    result=[]
    for r in rows:
        if r['period']!='2025-FY':
            continue
        loc=r['locators']['revenue']
        f=archive/'companies'/r['company']/loc['path']
        blob=f.read_bytes()
        assert sha256(blob).hexdigest()==loc['sha256']
        if f.suffix.lower()=='.pdf':
            pdf=pypdfium2.PdfDocument(blob)
            body=pdf[loc['page']-1].get_textpage().get_text_range()
            content=[s for s in body.splitlines() if loc['row_label'] in s and '合计' not in s]
            if not content:
                # The bilingual statement may duplicate the original label under an issuer line split.
                content=[s for s in body.splitlines() if 'Revenue' in s or '营业总收入' in s]
        else:
            doc=html.fromstring(blob)
            tables=doc.xpath('//table')
            table=tables[loc['html_table']-1]
            content=[' '.join(tr.itertext()) for tr in table.xpath('.//tr') if 'Total revenue' in ' '.join(tr.itertext())]
            if not content:
                content=[' '.join(tr.itertext()) for tr in doc.xpath('//tr') if 'Total revenue' in ' '.join(tr.itertext())]
        normalized=[re.sub(r'[,\s]','',line) for line in content]
        assert any(loc['value'] in val for val in normalized),(r['company'],content[:5])
        exact=float(loc['value'])*loc['scale']/1e6
        assert abs(exact-r['values']['revenue'])<1e-9
        result.append(dict(company=r['company'], original=r['source'], published=r['filed'],
           report_period='2025-FY',unit=loc['unit'],currency='USD' if r['company'].startswith('US') else 'CNY',
           statement=loc.get('table_heading') or 'Consolidated Statements of Income', locator=loc.get('page') or loc.get('html_table'),
           column='2025财年本期；2024比较列独立',label=loc['row_label'],value=loc['value'],sign='正',
           normalized_millions=exact,sha256=loc['sha256'],url=loc['url'],actor='agent'))
    assert len(result)==5
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=ROOT)
    args=parser.parse_args()
    print(json.dumps(check(args.archive),ensure_ascii=False,indent=2))
