"""Check frozen inputs, live bindings and the 394 transported workbench entries."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
from http.client import HTTPConnection
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs/collaboration'
BASE = '5c515fc6adc5b4cf4eb766f982721d8bdd9e309a'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def live(url, path, head=False):
    connection = HTTPConnection(url.hostname, url.port, timeout=30)
    try:
        connection.request('HEAD' if head else 'GET', path.split('#',1)[0])
        response = connection.getresponse()
        body = response.read() if not head else b''
        return response.status, response.getheader('Location'), body
    finally:
        connection.close()


def check_entries(url, records):
    def row(record):
        targets = [record['entry']] + [x.get('download_url', x['href']) for x in record['downloads']]
        ok, origins, missing = 0, 0, []
        for target in dict.fromkeys(targets):
            u = urlsplit(target)
            if u.scheme in ('https','http'):
                origins += 1
                continue
            if u.path == '/research-file':
                file = ROOT / parse_qs(u.query)['path'][0]
                if not file.is_file():
                    missing.append(target)
                    continue
            status, origin, _ = live(url, target, u.path in ('/research-source','/research-file'))
            if status == 200:
                ok += 1
            elif status == 302 and origin == record.get('original_url'):
                origins += 1
            else:
                missing.append(f'{status} {target}')
        return dict(
            company=record['company'],stage=record['stage'],id=record['id'],
            version=record['version'],source_at=BASE,previous_entry=record['entry'],
            new_entry=record['entry'],local_accesses=ok,issuer_paths=origins,
            downloads=json.dumps(record['downloads'],ensure_ascii=False),
            status='缺项' if missing else '附公开原件链接' if origins else '已验证访问', diagnostics=' | '.join(missing))
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(row,records))
    return result


def verify(url):
    stage15 = {d['company']:d['cases']['base']['per_share'] for d in read('docs/research15/valuation.json')}
    frozen = read('docs/research17/same-date.json')
    models = read('docs/research17/valuation.json')
    assert len(models) == len(frozen) == 5
    assert [round(d['stage15'], 2) for d in frozen[:3]] == [13.98, 97.91, 98.66]
    assert frozen[2]['stage15'] > frozen[2]['market_close'] > frozen[2]['stage16']
    for case, model in zip(frozen,models):
        assert case['stage15'] == stage15[case['company']]
        assert model['cases']['base']['per_share'] == case['stage16']
        assert case['stage16'] - case['stage15'] == case['delta']
        assert case['as_of'] == '2026-11-12'
    events = read('docs/super-atlas/follow-up.json')
    assert len(events) == 9 and all(not d['valuation_changed'] for d in events)
    batchnames = ['R12-FIRST-8','R14-002507-8','R14-600298-8','R14-688188-8','R14-9992-8','R14-ISRG-8']
    known = read('docs/research17/current_facts.json')
    bindings = {(r['company'],r['id']):(r['binding'],r['confirmation_event']) for r in known}
    for batch in batchnames:
        rows = read(f'docs/research15/{batch}.json')
        assert [r['index'] for r in rows] == list(range(1,9))
        for row in rows:
            assert bindings[row['company'],row['ledger_id']][1] == row['confirmation_event']
    response,_,body=live(url,'/research/facts.json')
    assert response == 200
    current = json.loads(body)
    assert all(bindings[r['company'],r['id']]==(r['binding'],r['confirmation_event']) for r in current)
    registered = read('docs/super-atlas/coverage.json')
    assert len(registered) == 394
    results=check_entries(url,registered)
    return results, dict(source_commit=BASE, cutoff='2026-11-12',
        research_companies=5, audited_batch_positions=48, frozen_facts=len(known),
        live_facts_in_this_run=len(current), followup_records=len(events),
        covered=len(results), statuses=dict(Counter(r['status'] for r in results)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8780')
    parser.add_argument('--output',type=Path, default=DEST)
    args=parser.parse_args()
    url=urlsplit(args.url)
    if url.hostname not in ('127.0.0.1','localhost'):
        parser.error('只能检查本机工作台')
    results,summary=verify(url)
    args.output.mkdir(exist_ok=True,parents=True)
    with (args.output/'migration.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream, list(results[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(results)
    (args.output/'migration.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.output/'migration-acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    assert not summary['statuses'].get('缺项')


if __name__ == '__main__':
    main()
