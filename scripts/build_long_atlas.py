"""Build an editable, printable and self-contained edition from the chapter Markdown."""
import argparse
import csv
from hashlib import sha256
from html import escape
from io import StringIO
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_DEFLATED
import unicodedata

from long_atlas_data import BRANDS, CASES, MECHANISMS, NAMES, OUT, ROOT, field_coverage, figures, number, readcsv, readj

BASELINE='9301d3129511c0080818e802311d1989f6cd1505'
EDITION='2026-11-20-v22'
TITLE='五家公司证券投资超级图册'
HAN=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0003134f]')
LINK=re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
HEADING=re.compile(r'^(#{1,6})\s+(.+)$')
CHAPTER_NAMES=['投资判断与导读','交易链与竞争','行业与历史周期','收入、成本和渠道','现金与再投资','预测与估值','反证与跟踪']
FIG_IDS=[('price',), (), ('revenue','margins'), ('special-1','special-2','interim'),
         ('cash','wc','historical-addon','capital'), ('forecast-revenue','forecast-cash','value-bridge','reverse'), ()]
MARKS={'002507':'菜','600298':'酵','688188':'控','09992':'偶','US':'术'}
COLORS=('#216557','#ad4c39','#4c679a','#955d93')
CSS=(Path(__file__).with_name('long_atlas.css')).read_text(encoding='utf-8')
JS=(Path(__file__).with_name('long_atlas.js')).read_text(encoding='utf-8')


def atomic(file, value):
    file.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(value,bytes):
        file.write_bytes(value)
    else:
        file.write_text(value,encoding='utf-8',newline='\n')


def json_text(o, compact=False):
    return (json.dumps(o,ensure_ascii=False,indent=None if compact else 2,allow_nan=False)+'\n').replace('<','\\u003c')


def csv_text(rows):
    out=StringIO()
    if rows:
        keys=list(dict.fromkeys(k for r in rows for k in r))
        writer=csv.DictWriter(out,keys,lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return '\ufeff'+out.getvalue()


def plain(src):
    src=LINK.sub(lambda m:m[1],src)
    return re.sub(r'[*_~\x60]','',src)


def han(src):
    src=LINK.sub('',src)
    return ''.join(HAN.findall(unicodedata.normalize('NFKC',src)))


def link(text,url,attrs=''):
    return f'<a href="{escape(url,quote=True)}"{attrs}>{escape(str(text))}</a>'



def stable_route(ref):
    # Markdown chapters can use paths relative to their source files. Published URLs
    # are stable across the online company page and the unpacked offline edition.
    if ref.startswith('../../../'):
        ref='/'+ref[9:]
    if ref=='/research14-market-series.json':
        return '/long-atlas/market-series.json'
    return re.sub(r'^/research(1[567])/',r'/stage\1/',ref)


def offline_file(route):
    ref=urlsplit(route).path
    for stage in ('15','16','17'):
        prefix=f'/stage{stage}/'
        if ref.startswith(prefix):
            candidate=ROOT/'docs'/f'research{stage}'/ref.removeprefix(prefix)
            if candidate.is_file() and candidate.suffix in ('.md','.csv','.json'):
                return f'support/stage{stage}/'+ref.removeprefix(prefix),candidate
    if ref=='/research14-market-series.json':
        file=ROOT/'docs/research14-market-series.json'
        if file.is_file():
            return 'support/research14-market-series.json',file
    if ref=='/research/facts.html':
        return 'support/stage17/current_facts.json',ROOT/'docs/research17/current_facts.json'
    if ref=='/research/follow-up.html':
        for candidate in ('post-cutoff.csv','post-cutoff.json','follow-up.csv','follow-up.json'):
            result=ROOT/'docs/research17'/candidate
            if result.is_file():
                return 'support/stage17/'+candidate,result
    return None


def relative_ref(url, code, bundled):
    url=stable_route(url)
    if not url.startswith('/'):
        return url
    prefix='../' if code else ''
    if url.startswith('/long-atlas/'):
        target=url.removeprefix('/long-atlas/')
        if not target or target.endswith('/'):
            target+='index.html'
        return prefix+target
    if bundled:
        registered=offline_file(url)
        if registered:
            return prefix+registered[0]
        if url.startswith('/cases/'):
            return prefix+'support/'+url.removeprefix('/cases/')
    return url


def rich(src, code=None, bundled=False):
    tokens=list(LINK.finditer(src))
    end=0
    content=[]
    for m in tokens:
        content.append(escape(plain(src[end:m.start()])))
        ref=m[2].strip()
        if ref.startswith(('/','#','../','./')) or urlsplit(ref).scheme in ('https','http'):
            content.append(link(m[1],relative_ref(ref,code,bundled)))
        else:
            content.append(escape(m[1]))
        end=m.end()
    content.append(escape(plain(src[end:])))
    return ''.join(content)


def parse_chapter(file, chapter):
    text=file.read_text(encoding='utf-8').strip()
    blocks=[]
    title=CHAPTER_NAMES[chapter-1]
    headings=False
    counter=0
    appendix=False
    fenced=False
    pending=[]
    def flush():
        nonlocal counter
        if not pending:
            return
        body=' '.join(pending)
        pending.clear()
        counter+=1
        blocks.append(dict(id=f's{chapter}-p{counter}',role='appendix' if appendix else 'prose',text=body))
    for raw in text.splitlines():
        line=raw.strip()
        if not line:
            flush()
            continue
        if re.match(r'^[\x60~]{3,}',line):
            flush()
            fenced=not fenced
            continue
        if fenced:
            continue
        heading=HEADING.match(line)
        if heading:
            flush()
            heading_text=heading[2]
            if not headings and len(heading[1])==1:
                title=heading_text
            else:
                blocks.append(dict(role='heading',text=heading_text))
                appendix=bool(re.match('^(附录|图表|来源与口径|证据索引|参考文献)',heading_text))
            headings=True
        elif line.startswith(('|','>','![','<!--','[^')) or re.fullmatch(r'[-*_]{3,}',line):
            flush()
            blocks.append(dict(role='aux',text=line))
        else:
            pending.append(line)
    flush()
    return dict(id=f'chapter-{chapter}',number=chapter,title=title,blocks=blocks)


def edition_data(allow_incomplete):
    all_docs={}
    counts=[]
    seen={}
    for code in NAMES:
        model=readj(CASES/code/'model.json')
        parts=[]
        for i in range(1,8):
            file=OUT/code/'chapters'/f'{i:02}.md'
            if file.is_file():
                parts.append(parse_chapter(file,i))
            elif not allow_incomplete:
                raise FileNotFoundError(file)
        paragraphs={}
        for c in parts:
            included=excluded=0
            for b in c['blocks']:
                if b['role']!='prose':
                    continue
                canonical=han(b['text'])
                if not canonical or canonical in seen:
                    b['role']='excluded'
                    excluded+=len(canonical)
                else:
                    seen[canonical]=(code,b['id'])
                    included+=len(canonical)
                    paragraphs[b['id']]=plain(b['text'])
            counts.append(dict(company=code,chapter=c['id'],title=c['title'],han=included,
                               repeated_or_unclassified=excluded))
        total=sum(r['han'] for r in counts if r['company']==code)
        counts.append(dict(company=code,chapter='合计',title=NAMES[code],han=total,
                           repeated_or_unclassified=sum(r['repeated_or_unclassified'] for r in counts if r['company']==code)))
        if not allow_incomplete and total<20000:
            raise ValueError(f'{code} 仅 {total} 个有效正文汉字')
        source='\n\n'.join(f'# {c["title"]}\n\n'+'\n\n'.join(b['text'] for b in c['blocks'] if b['role']=='prose') for c in parts)
        plots=figures(code)
        if len(plots)<12 or len(MECHANISMS[code])<4:
            raise ValueError(f'{code} 图数未达到最低要求')
        if len({(f['source'],str(f['series'])) for f in plots})!=len(plots):
            raise ValueError(f'{code} 重复图表')
        all_docs[code]=dict(format='company-research-atlas/v2.2',edition=EDITION,baseline=BASELINE,
                            code=code,name=NAMES[code],cutoff=model['cutoff'],
                            digest=sha256(source.encode()).hexdigest(),
                            han=total,chapters=parts,paragraphs=paragraphs,figures=plots,
                            mechanisms=MECHANISMS[code],markets=model['security'],close=model['close'],
                            cases={k:m['per_share'] for k,m in model['cases'].items()})
    return all_docs,counts


def clean_display(val):
    if val is None or val=='':
        return '—'
    if isinstance(val,float):
        return f'{val:,.6g}'
    return str(val)


def table(cols, rows):
    return ('<div class="table-cut" tabindex="0" role="region" aria-label="数据表可局部滚动"><table><thead><tr>'+
            ''.join('<th scope="col">'+escape(str(s))+'</th>' for s in cols)+'</tr></thead><tbody>'+
            ''.join('<tr>'+''.join('<td>'+escape(clean_display(v))+'</td>' for v in r)+'</tr>' for r in rows)+
            '</tbody></table></div>')


def svg(fig, kind):
    labels=fig['labels']
    series=fig['series']
    vals=[val for s in series for val in s['values'] if val is not None]
    width=660
    letters=max(len(str(l)) for l in labels)
    rotated=len(labels)>7 or letters>9
    bottom=118 if rotated else 56
    height=266+bottom
    y0=266
    start=70
    step=(width-start-15)/len(labels)
    lo,hi=min(vals),max(vals)
    if kind=='bar' or lo==hi:
        lo=min(0,lo)
        hi=max(1,hi)
    spread=max(hi-lo,1e-10)
    lo-=spread*.07
    hi+=spread*.10
    yp=lambda v:y0-(v-lo)/(hi-lo)*(y0-19)
    xp=lambda i:start+(i+.5)*step
    graphic=[f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(fig["title"]+" "+fig["unit"])}" xmlns="http://www.w3.org/2000/svg">']
    for i in range(5):
        v=lo+(hi-lo)*i/4
        y=yp(v)
        graphic.append(f'<path d="M{start} {y:.1f}H{width-12}" stroke="#d2d7ca"/>'
                       f'<text x="{start-5}" y="{y+4:.1f}" text-anchor="end" fill="#314b42" font-size="13">{v:,.4g}</text>')
    if len(labels)>14:
        show=set(range(0,len(labels),max(2,len(labels)//9)))
        show.add(len(labels)-1)
    else:
        show=range(len(labels))
    for i in show:
        l=str(labels[i])
        display=l if len(l)<=14 else l[:13]+'…'
        x=xp(i)
        rotate=f' transform="rotate(-43 {x:.1f} {y0+14})"' if rotated else ''
        anchor='end' if rotated else 'middle'
        graphic.append(f'<text x="{x:.1f}" y="{y0+14}"{rotate} text-anchor="{anchor}" fill="#2b473e" font-size="13">{escape(display)}<title>{escape(l)}</title></text>')
    for j,s in enumerate(series):
        color=COLORS[j%len(COLORS)]
        previous=None
        for i,v in enumerate(s['values']):
            if v is None:
                previous=None
                continue
            x,y=xp(i),yp(v)
            hint=escape(f'{labels[i]} {s["name"]} {v:,.9g} {fig["unit"]}')
            if kind=='bar':
                w=max(1,step*.7/len(series))
                bx=x+((j-len(series)/2)*w)
                base=yp(0)
                graphic.append(f'<rect x="{bx:.2f}" y="{min(base,y):.2f}" width="{w:.2f}" height="{max(.7,abs(base-y)):.2f}" rx="2" fill="{color}"><title>{hint}</title></rect>')
            else:
                if previous is not None:
                    graphic.append(f'<path d="M{previous[0]:.2f} {previous[1]:.2f}L{x:.2f} {y:.2f}" fill="none" stroke="{color}" stroke-width="2.8"/>')
                graphic.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.4" fill="{color}"><title>{hint}</title></circle>')
                previous=x,y
    graphic.append('</svg>')
    return ''.join(graphic)


def render_figure(f,code,bundled):
    default=f['kind']
    alternate='line' if default=='bar' else 'bar'
    rows=[[l]+[s['values'][i] for s in f['series']] for i,l in enumerate(f['labels'])]
    cols=['期间或条件']+[s['name'] for s in f['series']]
    kind_names={'line':'趋势线','bar':'对照柱','table':'底表'}
    buttons=''.join(f'<button type="button" data-mode="{k}" aria-pressed="{str(k==default).lower()}">{kind_names[k]}</button>' for k in (default,alternate,'table'))
    plots=''.join(f'<div class="plot-shell" data-view="{k}" tabindex="0" aria-label="图表可局部滚动"'+(' hidden' if i else '')+'>'+svg(f,k)+'</div>' for i,k in enumerate((default,alternate)))
    legend=''.join(f'<li><i style="background:{COLORS[i%len(COLORS)]}"></i>{escape(s["name"])}</li>' for i,s in enumerate(f['series']))
    source=link('同源底表或模型',relative_ref(f['source'],code,bundled))
    many=' data-many' if len(f['labels'])>6 or max(len(str(l)) for l in f['labels'])>9 else ''
    return (f'<figure id="figure-{f["id"]}" class="figure" data-data-figure{many}>'
            f'<h3>{escape(f["title"])}</h3><p class="date">单位 {escape(f["unit"])}</p>'
            f'<div role="group" aria-label="图表形式">{buttons}</div><ul class="legend">{legend}</ul>{plots}'
            f'<div data-view="table" hidden>{table(cols,rows)}</div>'
            f'<figcaption>{escape(f["reading"])}</figcaption><details><summary>展开数据、口径和来源</summary>'
            f'{table(cols,rows)}<p class="source-note">{source} · 显示值至六位有效数字，下载保存计算精度。</p></details></figure>')


def mechanism(entry,idx):
    title,path,note=entry
    nodes=''.join(f'<div class="node"><b>{n}</b>{escape(p)}</div>' for n,p in enumerate(path.split('|'),1))
    return (f'<figure class="mechanism" data-mechanism id="mechanism-{idx}"><h3>{escape(title)}</h3>'
            f'<div class="flow" role="img" aria-label="{escape(path.replace("|","，"))}">{nodes}</div>'
            f'<figcaption>{escape(note)} · 原创交易机制示意</figcaption></figure>')


def head(title,body,code=None,document_data=None):
    attrs=f' data-company="{code}" style="--accent:{BRANDS[code][2]}"' if code else ''
    embedded=f'<script type="application/json" id="company-document">{json_text(document_data,True)}</script>' if document_data else ''
    return (f'<!doctype html>\n<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(title)}</title><style>{CSS}</style><body{attrs}>'
            f'<a class="skip" href="#main">跳到研究正文</a>{body}{embedded}<script>{JS}</script></body></html>')


def price_cards(d):
    items=[('同日收盘',d['close']),('压力',d['cases']['stress']),('基准',d['cases']['base']),('改善',d['cases']['improve'])]
    return '<div class="quotes">'+''.join(f'<div class="quote"><small>{name}</small><strong class="value">{v:,.2f}</strong>'
                    f'<small>{d["markets"]["quote"]}／股</small></div>' for name,v in items)+'</div>'


def nav(code=None,bundled=False):
    def route(path):
        return relative_ref('/long-atlas/'+path,code,bundled)
    choices='<option value="">切换公司</option>'+''.join(f'<option value="{route(c+"/")}"'+(' selected' if c==code else '')+
                '>'+escape(name)+'</option>' for c,name in NAMES.items())
    work=link('研究工作台','/desk/') if not bundled else ''
    return ('<header class="top"><strong>'+link('图册总封面',route(''))+'</strong>'+link('五家同日比较',route('compare.html'))+
            (link('证据','#evidence')+link('编辑和下载','#downloads') if code else link('本版下载','#downloads'))+
            f'<label>公司 <select aria-label="切换公司" id="company-picker">{choices}</select></label>{work}</header>')


ILLUSTRATIONS = {
 '002507': ('#e8d8bb','#698567','<path d="M45 77h82l-8 42H53z" fill="#aa523e"/><path d="M43 77h85" stroke="#f4dbaa" stroke-width="6"/><path d="M80 80c-24-11-35-27-23-35 7-5 16 0 23 15 5-27 20-38 29-30 14 13-3 39-29 50" fill="#48735c"/><path d="M72 51l13 21 15-27" stroke="#f2edcf" stroke-width="2" fill="none"/>'),
 '600298': ('#e9ddbe','#976f37','<path d="M69 40h35v14H69z" fill="#aa723b"/><rect x="57" y="52" width="59" height="66" rx="11" fill="#d8ab68"/><path d="M69 105h35m-35-7V66" stroke="#f5ead1" stroke-width="3"/><circle cx="82" cy="80" r="5" fill="#fff3db"/><circle cx="99" cy="91" r="6" fill="#fff3db"/><path d="M113 62c24 0 25 22 25 28" stroke="#74583b" stroke-width="5" fill="none"/>'),
 '688188': ('#d9e4e6','#578097','<path d="M45 110h90v9H45z" fill="#416977"/><path d="M58 109V38h64v23" stroke="#54829c" stroke-width="11" fill="none" stroke-linejoin="round"/><path d="M109 56h26v20h-26z" fill="#325865"/><path d="M122 76v30m-12-6 12 6 9-9" stroke="#a25940" stroke-width="3" fill="none"/>'),
 '09992': ('#eadde5','#9a6e8b','<path d="M64 88c-32-20-19-52-4-51 13 1 18 26 22 38m15 0c5-20 11-39 23-40 14-1 23 28-8 52" stroke="#926b88" stroke-linecap="round" stroke-width="13" fill="none"/><path d="M45 99a44 29 0 0 1 88 0 44 29 0 0 1-88 0" fill="#ad809c"/><path d="M62 100a27 16 0 0 1 54 0 27 16 0 0 1-54 0" fill="#f3e2dd"/><circle cx="80" cy="98" r="2.5" fill="#382a3b"/><circle cx="101" cy="98" r="2.5" fill="#382a3b"/><path d="M86 108q4 4 10 0" stroke="#69445e" fill="none"/>'),
 'US': ('#d8e8e1','#54877f','<path d="M51 117h83M63 115V63l35-23 27 21" stroke="#43786f" stroke-width="9" fill="none" stroke-linecap="round"/><circle cx="61" cy="63" r="8" fill="#a7c5b8"/><circle cx="97" cy="40" r="8" fill="#a7c5b8"/><path d="M126 60v30m0 0-10 13m10-13 10 13" stroke="#915c48" stroke-width="4" fill="none" stroke-linecap="round"/><path d="M57 118h24V99H57z" fill="#6a9b8f"/>'),
}

def illustration(code):
    background,ink,drawing=ILLUSTRATIONS[code]
    return (f'<svg class="industry-mark" viewBox="0 0 175 140" role="img" aria-label="{NAMES[code]}原创行业示意">'
            f'<rect x="9" y="9" width="157" height="122" rx="36" fill="{background}"/>'
            f'<path d="M28 94Q56 32 139 30" fill="none" stroke="{ink}" opacity=".2" stroke-width="2"/>'
            +drawing+'</svg>')

def model_appendix(code):
    path=CASES/code
    rows=readcsv(path/'forecast.csv')
    actual=readcsv(path/'2026-bridge.csv')
    cases=[('base','基准'),('stress','压力'),('improve','改善')]
    lookup={k:n for k,n in cases}
    status=[[lookup[x['scenario']],x['period'],number(x['actual_revenue']),number(x['remaining_revenue']),
             number(x['full_year_revenue']),number(x['cash_after_valuation_date'])] for x in actual]
    headers=['情景','已披露期间','已披露收入','剩余期收入估计','全年收入','估值日后现金']
    result='<details class="links"><summary>展开2026实际、剩余期及估值现金</summary>'+table(headers,status)+'</details>'
    detail=[[lookup[x['scenario']],x['year'],*[number(x.get(m)) for m in ('revenue','operating_profit','cash_tax','nopat',
             'depreciation','delta_wc','cash_capex','lease_cash','incremental_equipment_cash','model_cash_after_date','present_value')]]
             for x in rows if int(x['year'])>=2027]
    names=['情景','财年','收入','经营利润','经营现金税','NOPAT','折旧','营运资本变动','现金购建','租赁现金','新增租赁设备现金','FCFF','现金现值']
    result+='<details class="links"><summary>展开2027—2031及成熟期三条现金路径</summary>'+table(names,detail)+'</details>'
    m=readj(path/'model.json')
    checks=[]
    for key,label in cases:
        s=m['cases'][key]
        v=s['valuation_check']
        checks.append([label,s['wacc'],s['terminal']['growth'],s['terminal']['incremental_return'],
                      v['explicit_pv'],v['terminal_pv'],v['terminal_share'],s['enterprise_value'],s['bridge']['bridge_net'],
                      s['equity'],m['security']['shares'],m['security']['fx'],s['per_share']])
    result+='<details class="links"><summary>展开折现、终值和每股价值桥</summary>'+table(
        ['情景','WACC','永续增长','稳态边际回报','显性期现值','终值现值','终值／EV','EV','权益调整','普通股权益','股数','财报／报价','每股价值'],checks)+'</details>'
    hist=m['historical_bridge']
    result+='<details class="links"><summary>展开阶段15到阶段17历史价值桥</summary>'+table(
        ['步骤','前值','后值','每股变化'],[[row['step'],row['start'],row['end'],row['change']] for row in hist])+'</details>'
    return result


def evidence(code,bundled):
    raw=CASES/code
    parts=[
        ('年度和近期财务',[('年度财务、阶段和原件','history.csv'),('近期累计、单季、期末','interim.csv'),('现金和利润变化桥','operating-bridges.csv')]),
        ('估值、原始驱动及判断',[('2026实际及剩余期','2026-bridge.csv'),('年度预测至终值','forecast.csv'),('历史参数与输入','parameters.csv'),
         ('完整可复算模型','model.json'),('反解和无根边界','reverse.csv'),('可比与相对估值','relative.csv'),
         ('旧新逐步每股变化','value-bridge.csv'),('上一版独立复核','independent-review.md')])]
    items=[(f.stem,f.name) for f in raw.glob('*.csv') if f.name not in {n for _,it in parts for _,n in it}]
    parts.append(('公司专项数据与证据',sorted(items)))
    groups=''.join(f'<details class="links"><summary>{title}</summary><p class="routes">'+''.join(
        link(name,relative_ref(f'/cases/{code}/{file}',code,bundled)) for name,file in refs)+'</p></details>' for title,refs in parts)
    origin=(link('当前 Fact 与来源绑定','/research/facts.html?code='+code)+' · '+link('估值日后跟踪','/research/follow-up.html')) if not bundled else (
            link('冻结原件证据索引',relative_ref(f'/cases/{code}/evidence-index.csv',code,bundled))+' · 离线证据保留公开 URL 和原件定位。')
    return ('<section class="chapter" id="evidence"><div class="source-pack"><h2>证据与复算</h2><p>'+origin+'</p>'+
            '<p>年度表保留来源编号、披露日、版本、指纹、行列与原始单位。已确认 Fact 以工作台在线 ReviewStore 的当前绑定为准。</p>'+
            groups+'<p class="routes">'+link('五家关键主张与复算条件','../claims.csv')+link('逐公司数据字段覆盖','coverage.csv')+'</p></div></section>')


def company(doc,bundled):
    code=doc['code']
    title=f'{doc["name"]}｜{BRANDS[code][0]}'
    available={f['id']:f for f in doc['figures']}
    contents=''.join(link(c['title'],'#'+c['id']) for c in doc['chapters'])
    rail=('<aside class="rail"><details open><summary>公司阅读目录</summary><nav aria-label="公司章节">'+contents+
          link('证据与复算','#evidence')+link('编辑与下载','#downloads')+'</nav></details></aside>')
    reading=['<section class="hero" id="main" tabindex="-1"><div class="date">'+escape(doc['markets']['ticker'])+
             ' · '+escape(doc['markets']['exchange'])+' · '+doc['cutoff']+' 当地未复权收盘</div>'
             f'<div class="hero-company"><div><h1>{escape(title)}</h1><p class="intro">{escape(BRANDS[code][3])}</p></div>{illustration(code)}</div>{price_cards(doc)}'
             '<nav class="routes" aria-label="三条阅读路线">'+link('经营故事','#chapter-2')+
             link('历史数据','#chapter-3')+link('预测估值','#chapter-6')+'</nav></section>']
    used=set()
    for c in doc['chapters']:
        reading.append(f'<section class="chapter" id="{c["id"]}"><h2>{escape(c["title"])}</h2>')
        plots=[available[k] for k in FIG_IDS[c['number']-1] if k in available]
        used.update(f['id'] for f in plots)
        mech=[i for i in range(4) if (2,4,5,7)[i]==c['number']]
        section_plots=[*(render_figure(f,code,bundled) for f in plots),
                       *(mechanism(doc['mechanisms'][i],i+1) for i in mech)]
        n_prose=sum(b['role']=='prose' for b in c['blocks'])
        positions={1+(i*n_prose)//(len(section_plots)+1):item for i,item in enumerate(section_plots)}
        prose_index=0
        reading.append('<div class="reading">')
        for b in c['blocks']:
            role=b['role']
            if role=='heading':
                reading.append('<h3>'+escape(b['text'])+'</h3>')
            elif role=='prose':
                reading.append(f'<p id="{b["id"]}" data-prose>{rich(b["text"],code,bundled)}</p>')
                prose_index+=1
                if prose_index in positions:
                    reading.extend(('</div>',positions[prose_index],'<div class="reading">'))
            elif role=='appendix':
                reading.append('<p class="source-note">'+rich(b['text'],code,bundled)+'</p>')
        reading.append('</div>')
        if c['number']==6:
            reading.append('<div class="source-pack"><h3>估值展开表</h3>'+model_appendix(code)+'</div>')
        reading.append('</section>')
    remainder=[f for f in doc['figures'] if f['id'] not in used]
    if remainder:
        reading.append('<section class="chapter" id="charts"><h2>数据图</h2>')
        reading.extend(render_figure(f,code,bundled) for f in remainder)
        reading.append('</section>')
    reading.append(evidence(code,bundled))
    downloads=[('在线正文 MD','case.md'),('可编辑 JSON','document.json'),('公司字数表','word-count.csv'),
               ('数据字段覆盖','coverage.csv'),('图表清单','figures.csv'),('公司估值复算','valuation-receipt.json')]
    reading.append('<section class="chapter" id="downloads"><h2>编辑、版本与下载</h2>'
                   '<p>本页草稿跟随本设备与本版正文。可导出带修改的 JSON 交给编辑者审阅。</p>'
                   '<div class="editable"><button type="button" id="edit-toggle" aria-pressed="false">编辑本地草稿</button> '
                   '<button type="button" id="save-draft" disabled>保存本地草稿</button> '
                   '<button type="button" id="export-draft">导出草稿 JSON</button><span id="revision" aria-live="polite"></span></div>'
                   '<p class="routes">'+''.join(link(n,v,' download') for n,v in downloads)+'</p>'
                   f'<p class="source-note">版本 {EDITION} · 正文有效汉字 {doc["han"]:,} · 正文指纹 <code>{doc["digest"]}</code></p></section>')
    return head(title,nav(code,bundled)+'<div class="progress" aria-hidden="true"></div><div class="layout">'+rail+
                '<main>'+''.join(reading)+'</main></div>',code,doc)


def cover(docs,bundled):
    cards=''.join('<a class="cover-card" style="--accent:'+BRANDS[c][2]+'" href="'+
                  relative_ref(f'/long-atlas/{c}/',None,bundled)+'">'+illustration(c)+
                  f'<h2>{escape(d["name"])}</h2><p><strong>{escape(d["markets"]["ticker"])}</strong> · {escape(BRANDS[c][0])}</p>'
                  f'<p>{escape(BRANDS[c][3])}</p></a>' for c,d in docs.items())
    download=(link('完整离线包 ZIP','offline.zip',' download')+' ' if not bundled else '')
    download+=link('总字数与逐章统计','word-count.csv',' download')+' '+link('数据字段与口径','coverage.csv',' download')+' '+link('图表清单','figures.csv',' download')+' '+link('各公司 WACC 参数与公式','wacc.csv',' download')+' '+link('新增历史原披露核验回执','historical-reviewstore-receipt.csv',' download')+' '+link('五家重大主张与证据','claims.csv',' download')+' '+link('新增原件定位','other-original-evidence.csv',' download')
    html=(nav(bundled=bundled)+'<main id="main" class="container" tabindex="-1"><section class="hero">'
          f'<p class="date">证券研究 · 2026-11-12 各交易所当地未复权收盘</p><h1>{TITLE}</h1>'
          '<p class="intro">从交易、经营历史与现金回收到每股价值。选择一家公司阅读完整案例，或用同日价格比较五家。</p>'
          '</section><section class="chapter"><h2>选择公司</h2><div class="cover-grid">'+cards+'</div></section>'
          '<section id="downloads" class="chapter"><h2>版本与下载</h2><div class="routes">'+download+'</div>'
          f'<p>本版 {EDITION}。保留阶段15—17冻结模型、当前工作台证据索引与既有图册。</p></section></main>')
    return head(TITLE,html)


def compare(docs,bundled):
    rows=[]
    for code,d in docs.items():
        base=d['cases']['base']
        rows.append([d['name'],d['markets']['ticker'],d['markets']['quote'],d['close'],d['cases']['stress'],
                     base,d['cases']['improve'],f'{(base/d["close"]-1):+.2%}',BRANDS[code][3]])
    html=nav(bundled=bundled)+('<main id="main" class="container" tabindex="-1"><section class="hero">'
           '<p class="date">2026-11-12 各交易所当地未复权收盘</p><h1>五家同日估值</h1>'
           '<p>每股保留报价币种。跨公司看基准相对收盘的百分比。</p></section><section class="chapter">'+
           table(['公司','代码','报价币种','同日收盘','压力','基准','改善','基准相对收盘','当前判断'],rows)+
           '</section><section id="downloads" class="chapter"><h2>比较底表</h2>'+
           link('同日比较 CSV','compare.csv',' download')+'</section></main>')
    vals=[dict(zip(('company','ticker','currency','close','stress','base','improve','base_to_close','judgment'),r)) for r in rows]
    return head('五家同日估值',html),vals


def calc_receipt(code):
    m=readj(CASES/code/'model.json')
    raw=CASES/code
    s=m['security']
    d=[]
    for name,o in m['cases'].items():
        v=o['valuation_check']
        rate=o['wacc']
        explicit=sum(x['model_cash_after_date']/(1+rate)**x['t'] for x in o['rows'])
        t=o['terminal']
        final=t['nopat']*(1-t['growth']/t['incremental_return'])
        terminal=final/(rate-t['growth'])/(1+rate)**o['rows'][-1]['t']
        enterprise=explicit+terminal
        per=(enterprise+o['bridge']['bridge_net'])*1e6/s['shares']/s['fx']
        assert abs(per-o['per_share'])<1e-8
        d.append(dict(scenario=name,wacc=rate,recomputed=per,model=o['per_share'],difference=per-o['per_share'],
                      explicit_pv=explicit,terminal_pv=terminal,enterprise=enterprise,equity=o['equity'],
                      terminal_share=terminal/enterprise,bridge=o['bridge']))
    hist=m['historical_bridge']
    return dict(code=code,cutoff=m['cutoff'],quoted_currency=s['quote'],close=m['close'],scenarios=d,
                historical_bridge=hist,stage17_to_current=m['stage17_to_case'],
                reverse_boundaries=m['tests']['boundary'],source='/cases/'+code+'/model.json')


def build(destination=OUT,allow_incomplete=False):
    docs,counts=edition_data(allow_incomplete)
    all_cover=[]
    all_per_fig=[]
    base_assets={}
    compare_html,compare_rows=compare(docs,False)
    base_assets['index.html']=cover(docs,False)
    base_assets['market-series.json']=(ROOT/'docs/research14-market-series.json').read_text(encoding='utf-8')
    base_assets['compare.html']=compare_html
    base_assets['compare.csv']=csv_text(compare_rows)
    base_assets['word-count.csv']=csv_text(counts)
    for code,d in docs.items():
        count=[r for r in counts if r['company']==code]
        fields_list=field_coverage(code)
        list_of_figs=[dict(company=code,id=x['id'],kind='独立数据图',title=x['title'],unit=x['unit'],source=x['source'],task=x['reading'])
                      for x in d['figures']]
        list_of_figs.extend(dict(company=code,id=f'mechanism-{i}',kind='机制图',title=x[0],unit='',source='原创机制示意',task=x[2])
                            for i,x in enumerate(d['mechanisms'],1))
        all_cover.extend(fields_list)
        all_per_fig.extend(list_of_figs)
        base_assets[code+'/index.html']=company(d,False)
        base_assets[code+'/document.json']=json_text(d)
        base_assets[code+'/case.md']='# '+NAMES[code]+'证券投资研究图册\n\n'+'\n\n'.join(
                    f'## {x["title"]}\n\n'+'\n\n'.join(
                        ('### '+b['text']) if b['role']=='heading' else b['text']
                        for b in x['blocks'] if b['role'] in ('heading','prose')) for x in d['chapters'])+'\n'
        base_assets[code+'/word-count.csv']=csv_text(count)
        base_assets[code+'/coverage.csv']=csv_text(fields_list)
        base_assets[code+'/figures.csv']=csv_text(list_of_figs)
        base_assets[code+'/valuation-receipt.json']=json_text(calc_receipt(code))
    base_assets['coverage.csv']=csv_text(all_cover)
    base_assets['figures.csv']=csv_text(all_per_fig)
    reference=[]
    for name,obj in base_assets.items():
        atomic(destination/name,obj)
    supplemental=['claims.csv','other-original-evidence.csv','wacc.csv','historical-reviewstore-receipt.csv','002507/channel-current-price.csv',
                 '600298/early-capital.csv','600298/historical-original-locators.csv',
                 '09992/historical-lease-cash.csv','09992/historical-original-locators.csv']
    for item in supplemental:
        data=(OUT/item).read_bytes()
        atomic(destination/item,data)
        reference.append((item,OUT/item))
    for d in docs.values():
        for c in d['chapters']:
            for b in c['blocks']:
                for _,ref in LINK.findall(b['text']):
                    src=offline_file(stable_route(ref))
                    if src:
                        reference.append(src)
    reference=list(dict(reference).items())
    for code in docs:
        for path in sorted((CASES/code).iterdir()):
            if path.is_file() and path.suffix in ('.csv','.json','.md','.svg','.py'):
                reference.append(('support/'+code+'/'+path.name,path))
    # Store deterministic member metadata to make the offline bundle independently reproducible.
    def zip_member(zf,name,payload):
        from zipfile import ZipInfo
        member=ZipInfo(name,(2026,11,20,0,0,0))
        member.compress_type=ZIP_DEFLATED
        zf.writestr(member,payload)
    with ZipFile(destination/'offline.zip','w',compression=ZIP_DEFLATED) as zf:
        for name,obj in sorted(base_assets.items()):
            if name=='index.html':
                obj=cover(docs,True)
            elif name=='compare.html':
                obj=compare(docs,True)[0]
            elif name.endswith('/index.html'):
                obj=company(docs[name.split('/')[0]],True)
            zip_member(zf,name,obj.encode())
        for name,path in reference:
            zip_member(zf,name,path.read_bytes())
    package=dict(edition=EDITION,codes=list(docs),baseline=BASELINE,files=sorted([*base_assets,'offline.zip',*supplemental,*[p.relative_to(OUT).as_posix() for p in (OUT/'previews').glob('*.png')],
                               *[n for n in ('README.md','motion.md','review.md','browser-receipt.json','acceptance.json') if (OUT/n).is_file()]]),
                 html_sha256={n:sha256(v.encode()).hexdigest() for n,v in base_assets.items() if n.endswith('.html')})
    atomic(destination/'package.json',json_text(package))
    return counts


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--preview',action='store_true',help='允许未齐稿，仅用于尚未发布的本地校验')
    p.add_argument('--out',type=Path,default=OUT)
    args=p.parse_args()
    counts=build(args.out,args.preview)
    for r in counts:
        if r['chapter']=='合计':
            print(r['company'],r['han'])

if __name__=='__main__':
    main()
