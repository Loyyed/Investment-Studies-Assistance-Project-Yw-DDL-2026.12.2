"""Render and serve independent cases using the existing workbench routes."""
from pathlib import PurePosixPath
import re
from urllib.parse import parse_qs, urlsplit

from atlas_registry import NAMES
from json import loads


def read(path):
    return loads(path.read_text(encoding='utf-8'))
from atlas_render import data_table, link, links, mast, page, text

SUPPORTED = {'.html':'text/html', '.csv':'text/csv', '.json':'application/json',
             '.md':'text/markdown', '.svg':'image/svg+xml', '.py':'text/plain', '.png':'image/png', '.jpg':'image/jpeg'}
LABELS = {
    'case.md':'案例正文 MD', 'report-map.md':'未来报告素材地图', 'independent-review.md':'独立复核',
    'history.csv':'历史财务桥', 'interim.csv':'近期累计／单季／余额', 'operating-bridges.csv':'经营活动桥',
    'forecast.csv':'2026实际＋预测底表', 'inputs.json':'程序输入索引', 'model.json':'完整模型与结果',
    'sensitivity.csv':'双变量矩阵', 'reverse.csv':'价格反推与无解边界', 'value-bridge.csv':'阶段17—新版价值桥',
    'evidence-index.csv':'来源与定位', 'relative.csv':'相对估值底表', 'sensitivity.svg':'灵敏度图',
}
NAV = [('工作台','/desk/'),('长篇图册','/long-atlas/'),('五家公司案例','/cases/'),('超级图册','/atlas/'),
       ('证据与覆盖','/research/'),('期后记录','/research/follow-up.html')]
SELECT = [
 ('688188','优先','销量、毛利、库存能构成可回代的故事。92.76 接近 96.20，反证能改变方向。',
  '财报同名系统销量、产品类别及库存可回查，客户级续购和配套服务费用仍缺。','中等'),
 ('600298','备选','新厂转固、销售认证与融资成本共同决定价差，跨周期材料完整。',
  '投产与会计转固能核验，新厂可售吨量及吨现金回收难归属。','较高'),
 ('002507','备选','渠道新增毛利能否留下现金，新基地投放存在明确反证。',
  '渠道和项目表详尽，终端销量、退换货和旧线替代难拆。','中等'),
 ('09992','备选','IP接力、海外渠道和现金租金产生明显情景分岔。',
  '区间披露不能还原季度绝对额，成熟门店同批次数据有缺口。','较高'),
 ('US','备选','术量和装机相互作用，现价需要超过发布改善路径的联合兑现。',
  'SEC业务和租赁附注可复算，单台使用强度、制造及维护现金仍需代理。','高'),
]


def matrix_svg(test, currency):
    rows=test['matrix']
    xs=list(dict.fromkeys(r['x'] for r in rows))
    ys=list(dict.fromkeys(r['y'] for r in rows))
    shades=('#f4dcd3','#f8f1e5','#dceadf')
    w=108+max(len(xs)*87,375)
    h=100+(len(ys)+1)*39
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="双变量条件估值矩阵">',
         f'<rect width="{w}" height="{h}" rx="18" fill="#fffaf0"/>',
         '<g font-family="sans-serif" fill="#263e36" font-size="13">',
         f'<text x="20" y="29" font-weight="bold">同日每股价值 · {text(currency)} · 收盘 {rows[0]["close"]:g}</text>',
         f'<text x="20" y="51">{text(test["y"])} ＼ {text(test["x"])}</text>']
    for i,x in enumerate(xs):
        svg.append(f'<text x="{114+i*86}" y="80">{x:.5g}</text>')
    for i,y in enumerate(ys):
        svg.append(f'<text x="20" y="{108+i*39}">{y:.6g}</text>')
    for r in rows:
        i,j=xs.index(r['x']),ys.index(r['y'])
        value,close=r['value'],r['close']
        c=shades[0 if value<close-.01 else 2 if value>close+.01 else 1]
        x,y=107+i*86,89+j*39
        svg.append(f'<g><title>{r["x"]}／{r["y"]} = {value:.12g}</title>'
                   f'<rect x="{x}" y="{y}" width="82" height="32" rx="7" fill="{c}"/>'
                   f'<text x="{x+7}" y="{y+21}">{value:.2f}</text></g>')
    return ''.join(svg)+'</g></svg>'


def case_nav(current=None):
    return NAV+[(name,'/cases/'+code+'/') for code,name in NAMES.items() if code!=current]


def markdown_sections(root, path, code):
    from companybench.portal import markdown_html
    markdown=path.read_text(encoding='utf-8')
    body=markdown_html(markdown,path.parent.relative_to(root),'').split('<body>',1)[1].split('</body>',1)[0]
    def registered(m):
        from html import unescape
        u=urlsplit(unescape(m[1]))
        if u.path!='/file':
            return m[0]
        q=parse_qs(u.query)
        v=q.get('path',[''])[0]
        if v.startswith(('/cases/','/research/','/atlas/','/stage15/','/stage16/','/stage17/')):
            return 'href="'+text(v.replace('?company=','?code=')+('#'+u.fragment if u.fragment else ''))+'"'
        target=(root/v).resolve()
        cases=root/'docs/cases'
        if target.is_relative_to(cases) and target.is_file():
            route='/cases/'+target.relative_to(cases).as_posix()
        elif target.is_relative_to(root/'docs') and target.is_file():
            rel=target.relative_to(root/'docs')
            folder=rel.parts[0]
            route='/stage'+folder[-2:]+'/'+ '/'.join(rel.parts[1:]) if folder in ('research15','research16','research17') else None
        else:
            fragment=v.find('/stage')
            route=v[fragment:] if fragment>=0 else None
        if route:
            return 'href="'+text(route+('#'+u.fragment if u.fragment else ''))+'"'
        return m[0]
    body=re.sub(r'href="([^"]+)"',registered,body)
    body=body.replace('<div class="table">','<div class="scroll" tabindex="0">')
    titles=[]
    def index(m):
        ident=f'case-{code}-section-{len(titles)+1}'
        titles.append((m[2], '#'+ident))
        return f'<h{m[1]} id="{ident}">{m[2]}</h{m[1]}>'
    body=re.sub(r'<h([2-3])>(.*?)</h\1>',index,body)
    toc='<nav class="source-links">'+''.join(f'<a href="{href}">{n}</a>' for n,href in titles)+'</nav>'
    return toc,body,len(titles)


def overview(root, out):
    title='五家公司证券投资案例'
    tiles=''
    for code,name in NAMES.items():
        m=read(out/code/'model.json')
        v=m['cases']['base']['per_share']; quote=m['security']['quote']
        tiles+=('<div class="tile"><h2>'+link(name,'/cases/'+code+'/')+'</h2><p>'
              f'收盘 {m["close"]:.2f} {quote} · 基准 {v:.2f} {quote}</p>'
              +links([('正文与数据','/cases/'+code+'/'),('估值模型','/cases/'+code+'/model.json'),
                      ('独立图册','/atlas/company/'+code)])+'</div>')
    return page(root,title,mast(title,'从交易、经营与资本回报推进到可复算的每股价值。','2026-11-12 各市场收盘',NAV)+
              '<main class="shell note"><div class="cover-grid">'+tiles+'</div><h2>选题比较与优先推荐</h2>'
              +data_table(['公司','推荐顺序','故事与可证伪性','原始证据质量','完成难度'],
                 [[dict(title=NAMES[r[0]],href='/cases/'+r[0]+'/'),*r[1:]] for r in SELECT])
              +links([('验收矩阵','/cases/acceptance.csv'),('全量复算回执','/cases/model-acceptance.json'),
                      ('干净克隆验收','/cases/rebuild-receipt.json'),('组长待审','/cases/review.html'),('动效预览','/cases/motion.html'),('运行说明','/cases/README.md')])+'</main>')


def render_case(root, out, code):
    target=out/code
    model=read(target/'model.json')
    title=NAMES[code]+'证券投资案例'
    md=target/'case.md'
    areas,body,count=markdown_sections(root,md,code)
    assert count>=7,(code,count)
    c=model['cases']['base']
    quote=model['security']['quote']
    stages=[[k,m['per_share'],m['wacc'],m['valuation_check']['explicit_pv'],m['terminal']['pv'],m['terminal']['pv_share']]
            for k,m in model['cases'].items()]
    available=sorted((f.name for f in target.iterdir() if f.is_file() and f.suffix in SUPPORTED
                      and f.name not in ('index.html',)),key=lambda n:(n not in LABELS,list(LABELS).index(n) if n in LABELS else n))
    nav=links([(LABELS.get(n,n),'/cases/'+code+'/'+n) for n in available])
    header=(f'基准 {c["per_share"]:.2f} {quote}，同日收盘 {model["close"]:.2f} {quote}。'
            '商业模式、经营变化与价格条件沿同一模型核对。')
    content=mast(title,header,'冻结窗口 2026-11-12',case_nav(code))
    content+='<main class="shell note"><div class="chapter"><h2>数据与复核</h2>'+nav+areas+'</div>'
    content+='<section class="chapter case-body">'+body+'</section><section class="chapter"><h2>三条路径与价值</h2>'
    content+=data_table(['情景','每股','WACC','显性期现值','终值现值','终值占比'],stages)
    content+='<h2>双变量反解</h2><p>'+text(model['tests']['condition'])+'</p><div class="scroll" tabindex="0">'
    content+=matrix_svg(model['tests'],quote)+'</div>'
    content+='<details><summary>同源反解边界与回代</summary>'+data_table(
         ['第二驱动取值','搜索首端价值','搜索末端价值','状态','首个解','回代价值'],
         [[r['y'],r['value_low'],r['value_high'],r['status'],r['roots'][0]['x'] if r['roots'] else None,
           r['roots'][0]['recovered'] if r['roots'] else None] for r in model['tests']['boundary']])+ '</details>'
    content+=links([('下载双变量底表','/cases/'+code+'/sensitivity.csv'),('查看原窗口事实','/research/facts.html?code='+code)])
    content+='</section></main>'
    return page(root,title,content)


def serve_case(host, root, route, query):
    parts=route.removeprefix('/cases/').strip('/').split('/')
    root=(root/'docs/cases').resolve()
    if len(parts)>2:
        return host.send({'error':'没有该案例资源'},404)
    rel=parts[0] or 'index.html'
    if rel in NAMES:
        rel=rel+'/'+(parts[1] if len(parts)==2 else 'index.html')
    elif len(parts)>1:
        return host.send({'error':'没有该案例资源'},404)
    file=(root/rel).resolve()
    listed=read(root/'case-package.json')['files']
    if rel not in listed or not file.is_relative_to(root) or file.suffix not in SUPPORTED or not file.is_file():
        return host.send({'error':'没有该案例资源'},404)
    mime=SUPPORTED[file.suffix]
    disposition=('attachment; filename="'+file.name+'"') if file.suffix in ('.md','.csv','.json','.py') or query.get('download')==['1'] else None
    # Sandboxed readers must explicitly opt in to user-initiated downloads.
    return host.send(file.read_bytes(),content=mime+'; charset=utf-8',disposition=disposition,
                     interactive=file.suffix=='.html',downloadable=True)
