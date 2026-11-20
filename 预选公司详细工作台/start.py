"""Run candidate selection and the shared Companybench on a local port."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from secrets import compare_digest
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlencode, urlsplit
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SHARED = ROOT / 'shared'
sys.path.insert(0, str(SHARED / 'runtime'))

from companybench import portal
from companybench.core import ReviewStore, WorkbenchError, atomic_text, locked, read_json, save_json

STYLES = """
:root{color-scheme:light;--paper:#f7f3ea;--ink:#172a31;--muted:#526065;--navy:#14323d;--edge:#d5ccc0;--light:#fffdfa}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:1rem/1.58 system-ui,sans-serif}
main,header>div{max-width:69rem;margin:auto;padding:1.2rem clamp(.9rem,4vw,3rem)}
header{background:var(--navy);color:#fffefb}h1{margin:.35rem 0;font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.18}
h2,h3{margin:.45rem 0}p{margin:.55rem 0}header a{color:#fffefb}nav{display:flex;gap:.85rem;flex-wrap:wrap}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.5fr);gap:1rem}
section,article{min-width:0}article,.panel{background:var(--light);border:1px solid var(--edge);border-radius:.5rem;padding:1rem;margin-bottom:.75rem}
form{display:grid;gap:.7rem}label{display:grid;gap:.22rem;font-weight:600}label.check{display:flex;align-items:baseline;gap:.5rem}
input:not([type=checkbox]),select,textarea{min-width:0;width:100%;font:inherit;background:#fff;color:var(--ink);padding:.45rem;border:1px solid #7b8589;border-radius:.25rem}
button,.button{display:inline-flex;align-items:center;min-height:2.75rem;max-width:100%;justify-self:start;padding:.4rem .75rem;background:var(--navy);color:#fff;border:1px solid var(--navy);border-radius:.35rem;font:inherit;text-decoration:none;cursor:pointer}
a{color:#15515c;text-underline-offset:.22em}:focus-visible{outline:3px solid #a46526;outline-offset:3px}
.meta,small{font-size:.9rem;color:var(--muted)}header .meta{color:#dde7e8}code{overflow-wrap:anywhere}
.actions{display:flex;flex-wrap:wrap;align-items:center;gap:.65rem}.steps{white-space:normal;margin:.5rem 0 1rem;padding-left:1.4rem}
details summary{cursor:pointer}.sources{list-style:none;padding:0}.sources li{padding:.55rem 0;border-bottom:1px solid var(--edge);overflow-wrap:anywhere}
.notice{background:#fbe8d7;border-left:4px solid #995725;padding:.65rem}
@media(max-width:45rem){.grid{grid-template-columns:1fr}.button{justify-self:stretch}}
"""

TEMPLATES = {
    '研究计划.md': 'tasks/research-plan.md', '口径裁决.md': 'work/metric-scope.md',
    '机制底稿.md': 'work/claim-notes.md', '最终报告.md': 'outputs/analysis-report.md',
    '内容验收.md': 'docs/acceptance.md', '会话交接.md': '会话交接/CURRENT.md',
    '稳定约定.md': '会话交接/DECISIONS.md', '年度变化.md': 'work/yearly-changes.md',
    '合同验收映射.md': 'work/contract-acceptance.md', '学习路径.md': 'docs/learning-path.md',
    '行业数据字典.md': 'work/series-definition.md',
}
PROFILES = {'general': '通用', 'consumer': '消费', 'industrial': '工业', 'financial': '金融'}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def clean(data, key, maximum, *, optional=False):
    value = str(data.get(key, '')).strip()
    if len(value) > maximum or (not optional and not value):
        raise WorkbenchError(f'{key}须为有效内容，最长 {maximum} 字。')
    return value


def identity(data):
    market = clean(data, 'market', 16).upper()
    code = clean(data, 'code', 20).upper()
    if not re.fullmatch('[A-Z][A-Z0-9]{1,15}', market):
        raise WorkbenchError('市场用 2–16 个字母或数字标识，并以字母开头。')
    if not re.fullmatch('[A-Z0-9]+(?:[.-][A-Z0-9]+)*', code):
        raise WorkbenchError('代码使用字母、数字、点或短横线。')
    return f'{market}-{code}', market, code


def add_event(candidate, action, actor='', detail=''):
    candidate['events'].append({'action': action, 'at': timestamp(), 'actor': actor, 'detail': detail})


def private_readables(name, market, code):
    return f"""# {name} · {market} {code}

先读本工作区的[会话交接](会话交接/CURRENT.md)。原始资料在 sources，证据账本在 evidence，经营与财务底稿在 work，报告草稿在 outputs。

通过预选工作台打开此项目。事实使用共享原生 ReviewStore 的 facts()，核准身份依实际操作登记。外部研究的引用保存在 work/reference-links.json，导入原件后仍需对读并独立确认。

本工作区及其原件、账本和草稿存放在本地数据目录。团队已确认的 Markdown 走协作仓库的报告合并流程。
"""


def scaffold(project, candidate):
    """Initialize a native project without importing data or duplicating the shared toolkit."""
    settings = {
        'schema_version': 1, 'company': candidate['company'], 'market': candidate['market'],
        'code': candidate['code'], 'profile': candidate['profile'], 'created_at': timestamp(),
        'information_cutoff': '', 'research_purpose': candidate['rationale'] or '公司分析',
        'source_scope': '本项目登记与独立核验的来源',
        'network_policy': '按本项目的任务与共享条件选择来源', 'review_mode': 'human-first',
        'reviewer': '', 'executor': '', 'signature_status': 'pending',
        'required_dimensions': ['商业模式', '行业竞争', '竞争优势'],
    }
    name, market, code = (settings[key] for key in ('company', 'market', 'code'))
    project.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.candidate-', dir=project.parent) as temp:
        path = Path(temp) / project.name
        for directory in ('sources/raw', 'sources/unpacked', 'sources/text', 'work', 'evidence',
                          'outputs', 'docs/images', '会话交接', 'tasks', 'runtime'):
            (path / directory).mkdir(parents=True)
        save_json(path / 'project.json', settings)
        save_json(path / 'sources/manifest.json', {'schema_version': 1, 'sources': []})
        save_json(path / 'evidence/ledger.json', {
            'schema_version': 1, 'records': {}, 'events': [], 'delegations': [], 'approvals': [],
        })
        save_json(path / 'work/report-scope.json', {
            'ready': False, 'path': 'outputs/analysis-report.md', 'record_ids': [],
        })
        save_json(path / 'work/reference-links.json', {'references': []})
        save_json(path / 'work/selection.json', candidate)
        navigation = read_json(SHARED / 'templates/研究导航.json', {})
        if navigation:
            save_json(path / 'work/research-navigation.json', navigation)
        for source, destination in TEMPLATES.items():
            template = (SHARED / 'templates' / source).read_text(encoding='utf-8-sig')
            text = template.replace('{{公司}}', name).replace('{{代码}}', code)
            atomic_text(path / destination, text.replace('{{行业适配}}', candidate['profile']))
        atomic_text(path / 'README.md', private_readables(name, market, code))
        atomic_text(path / 'AGENTS.md', """# 独立公司研究

先读本工作区的会话交接/CURRENT.md，再读协作仓库根 AGENTS.md 和 shared 中的共用工作流程。对读来源原件后使用 ReviewStore.facts()。参考链接只指向原项目，来源原件、当前 Fact、审核行为、估值参数与签署按本项目实际事件登记。完成阶段后更新本工作区交接。
""")
        ReviewStore(path).sync()
        path.rename(project)


class Selections:
    def __init__(self, data_dir):
        self.root = data_dir
        self.registry = data_dir / 'selections.json'

    def rows(self):
        return read_json(self.registry, {'schema_version': 1, 'candidates': []})

    def project(self, candidate):
        return self.root / 'projects' / candidate['id']

    def mutate(self, action, params):
        with locked(self.root):
            state = self.rows()
            candidates = state['candidates']
            if action == 'register':
                key, market, code = identity(params)
                if any(item['id'] == key for item in candidates):
                    raise WorkbenchError('此市场与代码已登记。请在候选列表打开。')
                name = clean(params, 'company', 90)
                if any(char in name for char in '\r\n'):
                    raise WorkbenchError('公司名称使用单行。')
                profile = params.get('profile', 'general')
                if profile not in PROFILES:
                    raise WorkbenchError('行业适配类型无效。')
                row = {
                    'id': key, 'market': market, 'code': code, 'company': name, 'profile': profile,
                    'rationale': clean(params, 'rationale', 700, optional=True), 'events': [],
                }
                add_event(row, 'registered', detail=row['rationale'])
                candidates.append(row)
            else:
                row = next((item for item in candidates if item['id'] == params.get('id')), None)
                if row is None:
                    raise WorkbenchError('未找到候选。')
                if action == 'confirm' and not any(e['action'] == 'confirmed' for e in row['events']):
                    if params.get('confirm_scope') != 'yes':
                        raise WorkbenchError('请先明确确认研究对象。')
                    add_event(row, 'confirmed', clean(params, 'reviewer', 80), clean(params, 'basis', 700))
                elif action == 'create':
                    if not any(e['action'] == 'confirmed' for e in row['events']):
                        raise WorkbenchError('请先确认研究对象。')
                    target = self.project(row)
                    if not target.exists():
                        scaffold(target, row)
                    elif read_json(target / 'work/selection.json', {}).get('id') != row['id']:
                        raise WorkbenchError('该目录已有其他工作区，已保留。')
                    if not any(e['action'] == 'workspace-created' for e in row['events']):
                        add_event(row, 'workspace-created')
                elif action not in {'confirm', 'create'}:
                    raise WorkbenchError('未知登记操作。')
            save_json(self.registry, state)
            return row

    def save_reference(self, params, catalog):
        cid = params.get('id')
        reference_id = params.get('reference')
        references = [r for r in catalog if r.get('id') == reference_id]
        if len(references) != 1:
            raise WorkbenchError('请选择唯一的资料或成果编号。')
        candidate = next((r for r in self.rows()['candidates'] if r['id'] == cid), None)
        if candidate is None:
            raise WorkbenchError('未找到候选。')
        project = self.project(candidate)
        ReviewStore(project)
        reference = references[0]
        with locked(project):
            file = project / 'work/reference-links.json'
            data = read_json(file, {'references': []})
            if not any(r['id'] == reference_id for r in data['references']):
                data['references'].append({
                    **{key: reference.get(key) for key in ('id', 'company', 'stage', 'topic', 'version', 'entry')},
                    'reason': clean(params, 'reason', 700), 'saved_at': timestamp(), 'status': '外部参考',
                })
                save_json(file, data)


def coverage():
    path = ROOT / 'docs/super-atlas/coverage.json'
    rows = read_json(path, [])
    return rows if isinstance(rows, list) else rows.get('entries', [])


def link(path, label, *, button=False):
    return f'<a {"class=button " if button else ""}href="{escape(path, quote=True)}">{escape(label)}</a>'


def form(action, token, fields, button, candidate_id=''):
    hidden = f'<input type="hidden" name="token" value="{escape(token)}">'
    if candidate_id:
        hidden += f'<input type="hidden" name="id" value="{escape(candidate_id)}">'
    return f'<form method="post" action="{action}">{hidden}{fields}<button>{escape(button)}</button></form>'


def native_url(candidate_id):
    return '/?' + urlencode({'project': candidate_id})


def page(title, guidance, body, research):
    nav = ' · '.join((
        link('/select', '候选登记'), link('/references', '可引用资料'),
        link('/knowledge', '共享方法库'), link(research + '/atlas/', '五家公司超级图册'),
    ))
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>
<style>{STYLES}</style></head><body><header><div><nav aria-label="工作台导航">{nav}</nav>
<h1>{escape(title)}</h1><p class="meta">{escape(guidance)}</p></div></header>
<main>{body}</main></body></html>"""


def selection_page(store, token, research):
    company_form = form('/select/register', token, """
<label>公司名称<input name="company" required maxlength="90"></label>
<label>市场<input name="market" placeholder="例如 SSE、HKEX、NASDAQ" required maxlength="16"></label>
<label>证券代码<input name="code" placeholder="例如 600000、00001" required maxlength="20"></label>
<label>行业适配<select name="profile"><option value="general">通用</option><option value="consumer">消费</option>
<option value="industrial">工业</option><option value="financial">金融</option></select></label>
<label>预选理由<textarea name="rationale" rows="3" maxlength="700"></textarea></label>""", '登记候选')
    cards = []
    for item in store.rows()['candidates']:
        key = item['id']
        approval = next((e for e in item['events'] if e['action'] == 'confirmed'), None)
        has_project = (store.project(item) / 'project.json').is_file()
        status = '已建独立工作区' if has_project else ('已确认研究对象' if approval else '待确认')
        output = (
            f'<article><h3>{escape(item["company"])}</h3>'
            f'<p class=meta><code>{escape(key)}</code> · {status}</p>'
        )
        if item['rationale']:
            output += f'<p>{escape(item["rationale"])}</p>'
        if approval:
            output += (
                '<details><summary>对象确认记录</summary>'
                f'<p>{escape(approval["actor"])} · {escape(approval["at"])}</p>'
                f'<p>{escape(approval["detail"])}</p></details>'
            )
        if has_project:
            output += '<div class=actions>' + link(native_url(key), '打开独立工作区', button=True)
            output += link('/references?' + urlencode({'id': key}), '关联已有资料') + '</div>'
        elif approval:
            output += form('/select/create', token, '', '创建独立工作区', key)
        else:
            output += form('/select/confirm', token, """
<label>确认人<input name="reviewer" required maxlength="80" autocomplete="name"></label>
<label>确认依据<textarea name="basis" required rows="2" maxlength="700"></textarea></label>
<label class="check"><input type="checkbox" name="confirm_scope" value="yes" required>我确认这是本轮研究对象</label>""",
                           '确认研究对象', key)
        cards.append(output + '</article>')
    body = (
        '<ol class=steps><li>登记候选与预选理由</li><li>由负责成员确认研究对象与依据</li>'
        '<li>按市场和代码创建工作区，登记来源后进入研究与出稿</li></ol>'
        '<div class=grid><section class=panel><h2>登记候选</h2>' + company_form +
        '</section><section aria-labelledby="candidates"><h2 id="candidates">候选与工作区</h2>' +
        (''.join(cards) or '<p class=meta>候选列表为空。登记后可逐项确认。</p>') + '</section></div>'
    )
    return page('预选公司详细工作台', '从候选到可分工、可复核的独立研究空间。', body, research)


def ref_page(store, token, research, params):
    candidate_id = params.get('id', '')
    term = params.get('q', '').strip().casefold()[:120]
    raw_catalog = coverage()
    catalog = [
        r for r in raw_catalog
        if not term or term in ' '.join(str(r.get(k, '')) for k in ('id', 'company', 'topic', 'stage')).casefold()
    ]
    matches = [r for r in store.rows()['candidates'] if r['id'] == candidate_id]
    candidate = matches[0] if matches else None
    entries = []
    options = []
    for row in catalog:
        ident, topic = str(row.get('id', '')), str(row.get('topic', ''))
        entry = str(row.get('entry', ''))
        where = research + entry if entry.startswith('/') and not entry.startswith('//') else ''
        href = link(where, '在研究工作台查看') if where else ''
        entries.append(f'<li><strong>{escape(topic)}</strong><br><code>{escape(ident)}</code> · '
                       f'{escape(str(row.get("company", "")))} · 阶段 {escape(str(row.get("stage", "")))} {href}</li>')
        options.append(f'<option value="{escape(ident, quote=True)}">{escape(ident + " · " + topic)}</option>')
    body = (
        '<section class=panel><h2>查找五家公司已有资料</h2><form method="get" action="/references">'
        f'<input type="hidden" name="id" value="{escape(candidate_id, quote=True)}">'
        f'<label>按公司、主题或编号查询<input type="search" name="q" value="{escape(term, quote=True)}"></label>'
        f'<button>查找</button></form><p class=meta>共 {len(catalog)} 项。'
        '新工作区在保存引用后，可依已有来源 URL 和指纹恢复原件并单独核验。</p></section>'
    )
    if candidate and (store.project(candidate) / 'project.json').is_file():
        notes = read_json(store.project(candidate) / 'work/reference-links.json', {'references': []})['references']
        body += '<section class=panel><h2>' + escape(candidate['company']) + '的参考资料</h2>'
        if options:
            fields = '<label>资料或成果<select name="reference" required>' + ''.join(options)
            fields += '</select></label><label>引用目的<textarea name="reason" required maxlength="700"></textarea></label>'
            body += form('/references', token, fields, '保存外部引用', candidate_id)
        body += '<ul class=sources>' + ''.join(
            f'<li><code>{escape(str(row["id"]))}</code> · {escape(str(row["reason"]))}</li>' for row in notes
        ) + '</ul>' + link(native_url(candidate_id), '回到独立工作区') + '</section>'
    return page('研究参考资料', '引用保留原成果编号、阶段和版本。原账户的核验与签署留在原项目。',
                body + '<ul class="sources">' + ''.join(entries) + '</ul>', research)


def handler_for(server, store, research):
    base = server.RequestHandlerClass
    token = server.workbench_token
    ui_path = SHARED / 'runtime/companybench/ui.js'

    class SelectionHandler(base):
        def custom_html(self, content, status=200):
            payload = content.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def redirect(self, path):
            self.send_response(303)
            self.send_header('Location', path)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def send(self, data, *args, **kwargs):
            if isinstance(data, str) and urlsplit(self.path).path == '/' and 'id="project-select"' in data:
                actions = re.compile(r'<div class="project-actions">.*?</div>')
                data = actions.sub('<div class="project-actions"><a class="help-link" href="/select">候选与工作区</a>'
                                   '<a class="help-link" href="/references">参考资料</a></div>', data, count=1)
            super().send(data, *args, **kwargs)

        def do_GET(self):
            if not self.host_ok():
                return self.send({'error': '仅接受工作台本机地址。'}, 403)
            route = urlsplit(self.path)
            params = {k: v[-1] for k, v in parse_qs(route.query).items()}
            if route.path == '/' and not params.get('project'):
                return self.redirect('/select')
            if route.path == '/select':
                return self.custom_html(selection_page(store, token, research))
            if route.path == '/references':
                return self.custom_html(ref_page(store, token, research, params))
            if route.path == '/assets/ui.js':
                script = ui_path.read_text(encoding='utf-8')
                old = "selected=localStorage.getItem('yt-project')||''"
                new = "selected=new URLSearchParams(location.search).get('project')||localStorage.getItem('yt-project')||''"
                return self.send(script.replace(old, new, 1), content='text/javascript; charset=utf-8')
            return super().do_GET()

        def do_POST(self):
            path = urlsplit(self.path).path
            if path in {'/api/new', '/api/link'}:
                return self.send({'error': '从候选登记页确认研究对象后创建独立工作区。'}, 403)
            if path not in {'/select/register', '/select/confirm', '/select/create', '/references'}:
                return super().do_POST()
            try:
                port = server.server_address[1]
                allowed = {None, f'http://127.0.0.1:{port}', f'http://localhost:{port}'}
                if not self.host_ok() or self.headers.get('Origin') not in allowed:
                    return self.send({'error': '请求来源不符。'}, 403)
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 15000:
                    raise WorkbenchError('表单超过大小限制。')
                params = {k: v[-1] for k, v in parse_qs(
                    self.rfile.read(length).decode('utf-8'), max_num_fields=16).items()}
                if not compare_digest(params.pop('token', '').encode(), token.encode()):
                    return self.send({'error': '表单令牌已失效，请重开候选页。'}, 403)
                if path == '/references':
                    store.save_reference(params, coverage())
                    return self.redirect('/references?' + urlencode({'id': params['id']}))
                action = path.rsplit('/', 1)[1]
                item = store.mutate(action, params)
                return self.redirect(native_url(item['id']) if action == 'create' else '/select')
            except (WorkbenchError, ValueError, OSError) as error:
                detail = f'<p class="notice">{escape(str(error))}</p>' + link('/select', '返回候选页')
                return self.custom_html(page('未保存本次操作', '已登记的候选和原件保留。', detail, research), 400)

    return SelectionHandler


def start(port=8781, data_dir=None, research_port=8780):
    storage = Path(data_dir).resolve() if data_dir else HERE / 'runtime'
    server = portal.make_server(storage, port)
    server.RequestHandlerClass = handler_for(server, Selections(storage), f'http://127.0.0.1:{research_port}')
    print(f'预选公司详细工作台 http://127.0.0.1:{server.server_address[1]}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8781)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--research-port', type=int, default=8780)
    args = parser.parse_args()
    start(args.port, args.data_dir, args.research_port)
