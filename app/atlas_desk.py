"""Read the album's canonical judgments in the team workbench."""
from atlas_registry import CUTOFF, NAMES, read
from atlas_render import data_table, link, links, mast, page, text

DEFAULT = ('002507', '600298', '688188')


def rows_for(root, doc):
    cards = {c['id'].removeprefix('company-'):c for c in doc['cards'] if c['id'].startswith('company-')}
    for m in read(root, 'docs/research17/valuation.json'):
        code = m['comparison']['code']
        c = cards[code]
        fp = m['comparison']
        yield {
            'code':code, 'name':NAMES[code], 'currency':fp['quote'], 'close':fp['market_close'],
            'stage15':fp['stage15'], 'change':fp['delta'], 'summary':c['feature']['summary'],
            'trigger':c.get('judgment', {}).get('trigger', ''),
            'model':m, 'case':[m['cases'][k]['per_share'] for k in ('stress','base','improve')],
        }


def render_desk(root, doc, *, mode='home', nonce=None):
    rows = list(rows_for(root,doc))
    nav = [('三公司首页','/desk/'),('五家公司图册','/atlas/'),('同日对照','/desk/compare/'),
           ('报告摘要','/desk/summary/'),('证据与覆盖','/research/'),('原生工作台','/')]
    if mode == 'compare':
        title = '五家公司同日估值与判断'
    elif mode == 'summary':
        title = '五家公司报告摘要'
    else:
        title = '三公司研究工作台'
    intro = ('历史结果以发布时快照展示。当前 Fact 按本地原件绑定核验。'
             if mode != 'home' else '先读三家 A 股的经营判断。默认名单供团队确认，五家完整图册均可进入。')
    content = mast(title, intro, CUTOFF, nav)
    content += '<main class="shell note">'
    def stock(row):
        return dict(title=row['name'],href='/atlas/company/'+row['code'])
    if mode == 'compare':
        content += data_table(['公司','币种','收盘','压力值','基准值','改善值','阶段15基准','同日变化','主判断'],
            [[stock(r),r['currency'],r['close'],*r['case'],r['stage15'],r['change'],r['summary']] for r in rows])
        content += links([('阶段17冻结对照','/stage17/same-date.html'),('旧新价值桥','/stage17/value-bridge.html'),
                          ('主题横向比较','/atlas/compare/')])
    else:
        content += '<div class="cover-grid">'
        for r in rows:
            if mode == 'home' and r['code'] not in DEFAULT:
                continue
            k = r['code']
            values = '／'.join(f'{v:.2f}' for v in r['case'])
            content += ('<article class="tile"><h2>'+link(r['name']+' '+k, '/atlas/company/'+k)+'</h2>'
                '<p>'+text(r['summary'])+'</p><p><strong>'+text(r['currency'])+' '+f"{r['close']:.2f}"+'</strong>'
                ' · 压力／基准／改善 '+values+'</p><p>'+text(r['trigger'])+'</p>'
                +links([('公司图册','/atlas/company/'+k),('冻结报告','/stage17/'+k+'/report.html'),
                        ('模型','/stage17/'+k+'/model.json'),('当前 Fact','/research/facts.html?code='+k),
                        ('关键原件','/research/coverage.html?code='+k)])+'</article>')
        content += '</div>'
    content += '</main>'
    return page(root, title, content, nonce=nonce)
