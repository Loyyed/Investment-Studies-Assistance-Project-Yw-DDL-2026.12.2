"""Recover public originals into local storage after exact SHA-256 verification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from csv import DictReader
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def digest(path):
    with path.open('rb') as source:
        checksum = sha256()
        while data := source.read(1 << 18):
            checksum.update(data)
    return checksum.hexdigest()


def registered():
    rows = read('docs/super-atlas/coverage.json')
    need = {(r['company'], s['source_id']) for r in read('docs/research17/current_facts.json')
            for s in r['sources']}
    known={(r['company'],r['id']) for r in rows}
    published=ROOT/'docs/long-atlas/historical-reviewstore-receipt.csv'
    if published.is_file():
        with published.open(encoding='utf-8-sig',newline='') as receipt:
            confirmed={(r['company'],r['source']) for r in DictReader(receipt)}
        companies={r['company'].split('_',1)[0]:r['company'] for r in rows if '_' in r['company']}
        for code in sorted({c for c,_ in confirmed}):
            company=companies[code]
            with (published.parent/code/'historical-original-locators.csv').open(encoding='utf-8-sig',newline='') as index:
                locators={r['source']:r for r in DictReader(index)}
            manifest=read(f'companies/{company}/sources/manifest.json')['sources']
            for source in manifest:
                sid=source['id']
                if (code,sid) not in confirmed:
                    continue
                need.add((company,sid))
                if (company,sid) in known:
                    continue
                loc=locators[sid]
                assert loc['sha256']==source['sha256']
                rows.append(dict(company=company,id=sid,source_path=source['path'],
                                 source_version=source['sha256'],original_url=loc['url']))
    for row in rows:
        company, identifier = row['company'], row['id']
        if row.get('source_path'):
            relative = Path('companies', company, row['source_path'])
        elif row.get('local_capture'):
            relative = Path(row['local_capture'])
        else:
            continue
        allowed = (ROOT / '.local').resolve() if row.get('local_capture') else (
            ROOT / 'companies' / company / 'sources/raw').resolve()
        target = (ROOT / relative).resolve()
        if not target.is_relative_to(allowed) or not row.get('source_version'):
            continue
        url = row.get('original_url', '')
        if urlsplit(url).scheme != 'https':
            continue
        yield (identifier, company, relative, target, url, row['source_version'], (company, identifier) in need)


def recover(row, archive, user_agent, plan):
    identifier, company, relative, target, url, expected, _ = row
    result = {'id':identifier, 'company':company, 'path':relative.as_posix(), 'url':url, 'sha256':expected}
    if target.exists():
        result['status'] = '已验证' if digest(target) == expected else '本地已有异版，保留并等待核对'
        return result
    if plan:
        result['status'] = '待恢复'
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        if archive:
            upstream = (archive / relative).resolve()
            if not upstream.is_relative_to(archive):
                raise ValueError('本地档案路径越界')
            original = upstream.open('rb')
        else:
            original = urlopen(Request(url, headers={'User-Agent': user_agent}), timeout=45)
        with original, tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temp = Path(stream.name)
            while block := original.read(1 << 18):
                stream.write(block)
        if digest(temp) != expected:
            raise ValueError('原件指纹不一致')
        if target.exists():
            raise ValueError('本地已有文件，保留当前版本')
        os.replace(temp, target)
        result['status'] = '已恢复并验证'
    except (ValueError, OSError) as exc:
        result['status'] = '待恢复'
        result['detail'] = str(exc)
    finally:
        if temp and temp.exists():
            temp.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=('facts','all'), default='facts')
    parser.add_argument('--from-archive', type=Path, help='经授权的本地原件目录根路径，不修改该目录')
    parser.add_argument('--user-agent', default='InvestmentResearchCollaborator/1.0')
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--id', help='只恢复指定来源编号')
    args = parser.parse_args()
    rows = [r for r in registered() if (args.scope == 'all' or r[-1]) and (not args.id or r[0] == args.id)]
    if args.id and not rows:
        parser.error('所选范围没有这个来源编号')
    archive = args.from_archive.resolve() if args.from_archive else None
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda r: recover(r, archive, args.user_agent, args.plan), rows))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if not args.plan and any(r['status'] not in ('已验证','已恢复并验证') for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
