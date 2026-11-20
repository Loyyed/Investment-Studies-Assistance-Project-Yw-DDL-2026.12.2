"""Render the research edition from the same document used by the editor and charts."""
from urllib.parse import quote

from atlas_render import (
    attributes, draw_figure, encoded, filter_bar, link, links, offline_resolver, paragraph,
    section_html, text,
)

INDUSTRIES = {
    '002507': ('深交所', '002507', '食品加工', '腌制容器与菜叶',
               '直销和新基地能为涪陵留下多少现金？'),
    '600298': ('上交所', '600298', '生物发酵', '发酵罐与管线',
               '新厂通过认证后，多久能赚到资本成本？'),
    '688188': ('科创板', '688188', '工业控制', '金属板与激光切割路径',
               '控制系统续购和配套毛利能填平估值差距吗？'),
    '09992': ('港交所', '09992', 'IP 零售', '零售盒与抽象藏品轮廓',
              'IP 接续能经得起成熟门店的现金检验吗？'),
    'US': ('纳斯达克', 'ISRG', '手术机器人', '手术机械臂的运动关节',
           '每台设备的术量能撑起租赁与当前股价吗？'),
}

COMPARISON = {'overview', 'business', 'forecast', 'valuation', 'updates'}


def company_link(code, offline):
    return ('#company-' if offline else '/atlas/company/') + code


def resolve_links(coverage, offline, current):
    base = offline_resolver(coverage) if offline else lambda url: url

    def resolve(url):
        if url.startswith('#company-') and not offline:
            code, _, chapter = url.removeprefix('#company-').partition('-')
            if code in INDUSTRIES and code != current:
                return company_link(code, False) + ('#company-' + code + '-' + chapter if chapter else '')
        return base(url)

    return resolve


def industry_art(code):
    return (
        f'<div class="sector-art sector-{code.lower()}" aria-hidden="true">'
        '<i></i><b></b><em></em></div>'
    )


def site_header(doc, *, offline, code):
    is_company = code in INDUSTRIES
    home = '#cover' if offline else '/atlas/'
    edit = (
        '/showcase?space=securities-atlas'
        + ('&chapter=company-' + quote(code) if is_company else '')
    )
    if offline:
        actions = [('选择公司', home), ('横向比较', '#overview'), ('期后证据', '#updates')]
    else:
        actions = [
            ('选择公司', home), ('横向比较', '/atlas/compare/'),
            ('证据与覆盖', '/research/coverage.html' + ('?code=' + quote(code) if is_company else '')),
            ('编辑与历史', edit), ('离线 HTML', '/atlas/offline.html?download=1'),
            ('可编辑 JSON', '/atlas/document.json'),
        ]
    nav = links(actions, 'edition-nav')
    return (
        '<a class="skip-link" href="#main">跳到主要内容</a>'
        '<header class="edition-header"><div class="shell edition-top">'
        + link('证券投资图册', home, 'edition-brand') + nav
        + '</div></header>'
    )


def publication_line(doc):
    return f'<p class="issue-date"><time>{text(doc["valuation_date"])}</time> · 各交易所当地收盘</p>'


def cover_page(doc, companies, offline):
    cards = []
    for code, card in companies.items():
        exchange, ticker, sector, _, question = INDUSTRIES[code]
        target = company_link(code, offline)
        cards.append(
            f'<a class="company-card card-{code.lower()}" href="{target}"'
            f' data-company-code="{code}">'
            + industry_art(code)
            + f'<div class="company-card-copy"><span class="market-code">{exchange} · {ticker}</span>'
            + f'<h2>{text(card["title"])}</h2><p>{text(question)}</p>'
            + f'<span class="sector-name">{sector}</span></div></a>'
        )
    title = text(doc['title'])
    if title == '五家公司证券投资超级图册':
        title = '<span>五家公司</span><span>证券投资超级图册</span>'
    return (
        '<section id="cover" class="edition-cover"><div class="cover-heading">'
        + publication_line(doc)
        + f'<h1>{title}</h1>'
        + '<p class="cover-deck">选择一家公司，从客户付钱读到自由现金流，再检验股价要求的经营结果。</p>'
        + '</div>'
        + '<nav class="company-picker" aria-label="选择公司">'
        + ''.join(cards)
        + '</nav></section>'
    )


def value_panel(section, code, doc):
    if section is None:
        return ''
    chart = section.get('chart')
    if not chart or len(chart['series']) != 1:
        return ''
    values = dict(zip(chart['labels'], chart['series'][0]['values']))
    if any(label not in values for label in ('收盘','压力','基准','改善')):
        return ''
    metrics = ''.join(
        f'<div class="valuation-item{(" base" if label=="基准" else "")}">'
        f'<dt>{text(label)}</dt><dd>{values[label]:,.2f}</dd></div>'
        for label in ('收盘','压力','基准','改善')
    )
    return (
        f'<section class="valuation-panel" aria-labelledby="values-{code}">'
        f'<h2 id="values-{code}">同日估值 <span>{text(chart["unit"])}</span></h2>'
        f'<dl>{metrics}</dl><p>以 {text(doc["valuation_date"])} 当地收盘比较。'
        + link('估值与价值桥', '#company-'+code+'-price') + '</p></section>'
    )


def section_directory(card):
    ident = card['id']
    sections = [section for section in card['feature']['sections'] if not section.get('hidden')]
    items = [(section['title'], '#'+ident+'-'+section['id']) for section in sections]
    return links(items, 'company-outline')


def company_switch(companies, selected, offline):
    entries = []
    for code, card in companies.items():
        state = ' aria-current="page"' if code == selected and not offline else ''
        entries.append(
            f'<a href="{company_link(code, offline)}"{state} data-company-code="{code}">'
            f'{text(card["title"])}</a>'
        )
    return '<nav class="company-switch" aria-label="切换公司">' + ''.join(entries) + '</nav>'


def company_story(doc, code, card, charts, resolve, methods, *, offline):
    feature = card['feature']
    sections = [item for item in feature['sections'] if not item.get('hidden')]
    ident = card['id']
    value = next((item for item in sections if item['id'] == 'price'), None)
    lead = next((item for item in sections if item['id'] == 'cash' and item.get('chart')), None)
    exchange, ticker, sector, art_label, _ = INDUSTRIES[code]
    card_title = 'h2' if offline else 'h1'
    lead_graph = ''
    if lead:
        lead_graph = (
            f'<div class="lead-figure" id="{text(ident)}-lead">'
            '<h2>经营兑现后能留下多少现金</h2>'
            + draw_figure(lead['chart'], ident+'-lead', charts, lead.get('annotation',''))
            + '<p>' + link('查看现金流推导和依据', '#'+ident+'-cash') + '</p>'
            + '</div>'
        )
    references = [
        ('阶段17定稿', resolve(f'/stage17/{code}/report.html')),
        ('同源估值模型', resolve(f'/stage17/{code}/model.json')),
        (
            '阶段17核验快照' if offline else '原件与当前核验',
            resolve('/stage17/fact-view.html' if offline else f'/research/facts.html?code={code}'),
        ),
        ('期后事件', '#updates' if offline else '/research/follow-up.html'),
    ]
    body = (
        f'<article class="company-story chapter" id="{text(ident)}" data-story>'
        '<header class="company-intro">'
        '<div class="company-brief">'
        f'<p class="market-code">{exchange} · {ticker} <span>{sector}</span></p>'
        f'<{card_title}>{text(card["title"])}</{card_title}>'
        f'<p class="investment-question">{text(feature["headline"])}</p>'
        + paragraph(feature['summary'])
        + links(references, 'company-references')
        + '</div>'
        + f'<div class="company-key"><div class="company-emblem" title="{text(art_label)}">'
        + industry_art(code)
        + '</div>'
        + value_panel(value, code, doc)
        + '</div></header>'
        + lead_graph
        + '<details class="chapter-menu" open><summary>章节目录</summary>'
        + section_directory(card) + '</details>'
        + '<div class="story-layout">'
        + '<div class="sticky-toc"><h2>章节</h2>' + section_directory(card) + '</div>'
        + '<div class="story-content">'
    )
    for section in sections:
        content = section.copy()
        if section is lead:
            # Move the first occurrence of this chart onto the opening spread.
            content['chart'] = None
            content['annotation'] = ''
            content['refs'] = [
                *content.get('refs', []),
                {'title':'返回三情景现金流图','href':'#'+ident+'-lead'},
            ]
        body += section_html(content, ident+'-'+section['id'], charts, resolve, methods)
    body += (
        '</div></div><div class="story-footer">'
        + link('返回选择公司', '#cover' if offline else '/atlas/', 'action')
        + '</div></article>'
    )
    return body


def comparison_story(results, charts, resolve, methods, *, online):
    tabs = ''.join(
        f'<a id="nav-{text(card["id"])}" href="#{text(card["id"])}">{text(card["title"])}</a>'
        for card in results
    )
    nav = '<nav class="compare-tabs" aria-label="比较章节">' + tabs + '</nav>'
    parts = []
    for card in results:
        feature = card['feature']
        content = ''.join(
            section_html(section, card['id']+'-'+section['id'], charts, resolve, methods)
            for section in feature['sections'] if not section.get('hidden')
        )
        filters = ''
        if online:
            terms = ' '.join([card['title'], feature['headline'], feature['summary'],
                              *(section['body'] for section in feature['sections'])])
            filters = attributes(terms, '|'.join(card['codes']), '|'.join(card['tags']), '|'.join(card['versions']))
        parts.append(
            f'<article id="{text(card["id"])}" class="chapter compare-story" {filters}>'
            f'<header><p class="market-code">{text(card["title"])}</p>'
            f'<h2>{text(feature["headline"])}</h2>{paragraph(feature["summary"])}</header>'
            + content + '</article>'
        )
    choices = ''
    if online:
        choices = filter_bar([
            ('topic','主题', [(x, x) for x in ('商业模式','经营预测','证券估值','反方与跟踪')], None),
            ('version','阶段', [(x, '阶段 '+x) for x in ('12','14','15','16','17')], None),
        ])
    return '<section id="comparison" class="comparison">' + choices + nav + ''.join(parts) + '</section>'


def method_index(methods):
    items = ''.join(
        f'<details id="method-{text(key)}"><summary>{text(key)} {text(card["title"])}</summary>'
        + paragraph(card['body']) + paragraph(card['evidence']) + paragraph(card['boundary'])
        + '</details>'
        for key, card in methods.items()
    )
    return '<details id="methods" class="methods"><summary>应用方法卡</summary>' + items + '</details>' if items else ''


def edition_html(root, title, content, charts, nonce, offline):
    sheet = '\n'.join((root/'app'/name).read_text(encoding='utf-8')
                      for name in ('atlas.css', 'atlas_edition.css'))
    assets = (root/'shared/runtime/companybench/result_features.js',
              root/'app/atlas.js', root/'app/atlas_edition.js')
    code = '\n'.join(file.read_text(encoding='utf-8') for file in assets)
    token = f' nonce="{text(nonce)}"' if nonce else ''
    body_class = 'edition-body edition-offline' if offline else 'edition-body'
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{text(title)}</title><style>{sheet}</style></head>'
        f'<body class="{body_class}">{content}'
        f'<script{token} type="application/json" id="charts">{encoded(charts)}</script>'
        f'<script{token}>{code}</script></body></html>\n'
    )


def render_edition(root, doc, coverage, *, code=None, nonce=None, offline=False):
    """The company code "compare" serves the comparative edition."""
    if code == 'ISRG':
        code = 'US'
    cards = [card for card in doc['cards'] if not card.get('archived')]
    companies = {
        key: card for key in INDUSTRIES
        for card in cards if card['id'] == 'company-'+key and card.get('feature')
    }
    if code not in (None, 'compare') and code not in companies:
        raise ValueError('图册公司不存在或已归档')
    compare = [card for card in cards if card['id'] in COMPARISON]
    methods = {card['id']:card for card in cards if card.get('kind') == 'knowledge'}
    resolve = resolve_links(coverage, offline, code)
    charts = {}
    header = site_header(doc, offline=offline, code=code)
    status = (
        '<div class="reading-progress" aria-hidden="true"><span></span></div>'
        if code in companies or offline else ''
    )
    content = ''
    title = doc['title']
    if offline or code is None:
        content += cover_page(doc, companies, offline)
    if offline or code in companies:
        selected = companies.items() if offline else [(code, companies[code])]
        if not offline:
            title = companies[code]['title'] + '｜证券投资图册'
            content += (
                '<div class="company-nav">'
                + link('返回封面', '/atlas/', 'back-link')
                + company_switch(companies, code, offline)
                + '</div>'
            )
        content += ''.join(
            company_story(doc, ident, card, charts, resolve, methods, offline=offline)
            for ident, card in selected
        )
    if offline or code == 'compare':
        if not offline:
            title = '横向比较｜' + title
            content += ('<nav class="presentation" aria-label="演示控制"><button id="previous">上一章</button>'
                        '<span id="position" aria-live="polite"></span><button id="next-slide">下一章</button>'
                        '<button id="exit">退出演示</button></nav>'
                        '<header class="compare-heading">' + publication_line(doc) + '<h1>五家公司横向比较</h1>'
                        '<button id="present" type="button">从头演示</button></header>')
        content += comparison_story(compare, charts, resolve, methods, online=not offline)
    if offline or code is not None:
        content += method_index(methods)
    methods_src = '行业图为本项目原创 CSS 示意，用于区分行业。'
    edition = f'{doc["atlas_version"]} · 展示修订 {doc["revision"]}'
    footer = (
        f'<footer class="edition-footer"><p>{text(doc["note"])}</p>'
        f'<p>{text(edition)} · {methods_src}</p>'
        + (link('首屏公司目录','#cover') if offline else link('回到图册封面','/atlas/'))
        + '</footer>'
    )
    complete = header + status + '<main class="shell edition-main" id="main" tabindex="-1">' + content + footer + '</main>'
    return edition_html(root, title, complete, charts, nonce, offline)
