"""从可编辑章节及已锁定的研究快照构建离线柏楚图册。Python 3.10+，标准库。"""
import csv
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DATA = ROOT / "data"
META = json.loads((SRC / "versions.json").read_text(encoding="utf-8"))
WIDGETS = ("overview", "roles", "history", "income", "cash", "projects", "forecast", "valuation", "review", "conclusion")


def read(path):
    return path.read_text(encoding="utf-8-sig")


def records(base):
    with (DATA / f"{base}.csv").open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def url(target, archive):
    if archive and not re.match(r"^(https?://|#|mailto:)", target):
        return "original/" + target
    return target


def inline(source, archive=False):
    # 保护链接、代码和强调边界，保持 Markdown 显示处和原件定位。
    pattern = r"(!?)\[([^\]\n]*)\]\(([^)\n]+)\)|" + chr(96) + r"([^"+chr(96)+r"\n]+)"+chr(96)+r"|\*\*([^*\n]+)\*\*"
    parts = []
    end = 0
    for match in re.finditer(pattern, source):
        parts.append(escape(source[end:match.start()]))
        image, label, target, code, emphasis = match.groups()
        if target:
            href = escape(url(target, archive), quote=True)
            if image:
                parts.append(f'<img loading="lazy" src="{href}" alt="{escape(label)}">')
            else:
                parts.append(f'<a href="{href}">{escape(label)}</a>')
        elif code:
            parts.append(f"<code>{escape(code)}</code>")
        else:
            parts.append(f"<strong>{inline(emphasis, archive)}</strong>")
        end = match.end()
    return "".join(parts) + escape(source[end:])


def table(headers, body):
    head = "".join(f'<th scope="col">{x}</th>' for x in headers)
    rows = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>" for cells in body)
    return f'<div class="tableframe" tabindex="0" role="region" aria-label="可左右滚动的数据表"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def markdown(text, archive=False):
    lines = text.splitlines()
    html = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        token = re.fullmatch(r"\{\{([a-z]+)\}\}", line)
        if token:
            html.append(f'<div id="widget-{token[1]}" class="mount"></div>')
        elif line.startswith(chr(96)*3):
            fence = line[3:]
            body = []
            index += 1
            while index < len(lines) and not lines[index].startswith(chr(96)*3):
                body.append(lines[index])
                index += 1
            code = f'<pre aria-label="{escape(fence or "代码")}">{escape(chr(10).join(body))}</pre>'
            if fence == "mermaid" and archive:
                fallbacks = {"figure-toc":"02-overview.png","figure-chain":"03-industry.png",
                    "figure-renewal":"05-renewal.png","figure-drivers":"28-drivers.png"}
                last = next((el for el in reversed(html) if el.startswith('<a id="figure-')), None)
                figure = re.search(r'id="([^"]+)"', last)[1] if last else ""
                if figure in fallbacks:
                    directory = META["archive_figures"]
                    label = next((el for el in reversed(html) if el.startswith("<h4>")), "")
                    plain = escape(re.sub(r"<[^>]+>", "", label))
                    href = escape("original/" + directory + "/" + fallbacks[figure])
                    html.append(f'<figure class="archive-fig"><img loading="lazy" src="{href}" alt="{plain}"></figure>')
                html.append(f'<details><summary>展开原 Mermaid 源</summary>{code}</details>')
            else:
                html.append(code)
        elif line.startswith("|") and index + 1 < len(lines) and re.fullmatch(r"[|: -]+", lines[index+1].strip()):
            cells = lambda row: [inline(x.strip(), archive) for x in re.split(r"(?<!\\)\|", row.strip().strip("|"))]
            head = cells(line)
            body = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                body.append(cells(lines[index]))
                index += 1
            html.append(table(head, body))
            continue
        elif re.fullmatch(r'<a name="[a-zA-Z0-9_-]+"></a>', line):
            if 'name="chapter-' not in line:
                html.append(line.replace("name=", "id="))
        elif re.match(r"^#{1,6} ", line):
            heading, title = line.split(" ", 1)
            level = max(3, len(heading))
            html.append(f"<h{level}>{inline(title, archive)}</h{level}>")
        elif re.match(r"^(- |\d+\. )", line):
            ordered = not line.startswith("- ")
            kind = "ol" if ordered else "ul"
            items = []
            while index < len(lines) and (m := re.match(r"^\s*(?:- |\d+\. )(.+)$", lines[index])):
                items.append(f"<li>{inline(m[1], archive)}</li>")
                index += 1
            html.append(f"<{kind}>" + "".join(items) + f"</{kind}>")
            continue
        elif line.startswith("!["):
            html.append(f'<figure class="archive-fig">{inline(line, archive)}</figure>')
        elif line == "---":
            html.append("<hr>")
        else:
            kind = ' class="takeaway"' if line.startswith(("**本章落点。**", "> **最终投资建议：")) else ""
            html.append(f"<p{kind}>{inline(line.removeprefix('> '), archive)}</p>")
        index += 1
    return "\n".join(html)


report = read(ROOT / "original" / "report.md")
report_parts = list(re.finditer(r"^## 第 ([1-9]) 章.*$", report, re.M))
boundary = report.index("## 依据与研究边界")
assert [int(part[1]) for part in report_parts] == list(range(1, 10))
chapters = []
nav = []
chapter_titles = []
for i, widget in enumerate(WIDGETS, 1):
    token = f"{i:02d}"
    authored = read(SRC / "chapters" / f"{token}.md")
    title, body = authored.removeprefix("# ").split("\n", 1)
    chapter_titles.append(title)
    assert "{{" + widget + "}}" in body
    original = ""
    if i <= len(report_parts):
        start = report_parts[i-1].end()
        stop = report_parts[i].start() if i < len(report_parts) else boundary
        archive = markdown(report[start:stop], True)
        original = f'    <details class="original"><summary>阅读本章归档研究正文</summary><div class="archive-body">{archive}</div></details>\n'
    nav.append(f'<a href="#chapter-{token}"><span>{token}</span>{escape(title.rstrip("？"))}</a>')
    jump = f'<a href="#chapter-{i+1:02d}">下一章 ↓</a>' if i < len(WIDGETS) else '<a href="#sources">版本与证据索引 ↓</a>'
    chapters.append(f'''<section class="chapter" id="chapter-{token}" aria-labelledby="title-{token}">
    <header class="chapter-header"><p class="kicker">第 {token} 章</p><h2 id="title-{token}">{escape(title)}</h2></header>
    <div class="prose">{markdown(body)}</div>
{original}    <div class="chapter-next">{jump}</div></section>''')

model = json.loads(read(DATA / "model.json"))
assumptions = json.loads(read(DATA / "assumptions.json"))
audit = json.loads(read(ROOT / "audit" / "负现金复算回执.json"))
verify = lambda path, expected: sha256(path.read_bytes()).hexdigest() == expected
assert verify(DATA / "model.json", META["model_sha256"])
assert verify(ROOT / "original" / "report.md", META["report_sha256"])
assert verify(DATA / "assumptions.json", model["receipt"]["input_sha256"]["deep-research-batch-2/assumptions.json"])
assert model["receipt"]["date"] == "2026-11-12" and model["receipt"]["market"] == 96.2
prices = [model["scenarios"][x]["price"] for x in ("stress", "base", "improve")]
assert [f"{x:.2f}" for x in prices] == ["42.02", "81.81", "134.83"]
cash = audit["calculation"]["cash"]
assert [f"{float(x['cash']):+.2f}" for x in cash] == ["+10.38", "-0.58"]

history = [{
    "year": int(row["period"][:4]),
    **{k: float(row[k]) / 1e6 for k in ("revenue", "core_ebit", "cfo", "capex", "cfo_less_capex")}
} for row in records("financial-bridge") if row["period"].endswith("-FY") and row["column"] == "本期"]
annual = records("annual-evidence")
forecast = [{k: row[k] for k in ("scenario", "year", "control_units", "revenue", "core_ebit", "fcff", "control_new", "control_replacements", "valued_cash")} for row in records("forecast")]
nodes = records("price-contours")
assert len(nodes) == 21 and sum(bool(row["root"]) for row in nodes) == 15
assert max(abs(float(row["residual"])) for row in nodes if row["root"]) < 1e-10
volume = records("volume-and-stock")
group_revenue = lambda year: float(volume[year]["combined_main_revenue_per_control_equivalent_cny"]) * float(volume[year]["control_units"]) / 1e6
base_volume, new_volume = (float(row["control_units"]) for row in volume)
base_price = float(volume[0]["combined_main_revenue_per_control_equivalent_cny"])
revenue_bridge = [
    {"item": "2024 主营", "value": group_revenue(0)},
    {"item": "控制出货当量", "value": (new_volume - base_volume)*base_price/1e6},
    {"item": "组均价及组合", "value": group_revenue(1)-new_volume*base_price/1e6},
    {"item": "2025 主营", "value": group_revenue(1)},
]
data = {
    "meta": META, "history": history, "preIpo": records("pre-ipo"), "annual": annual, "forecast": forecast,
    "market": model["receipt"]["market"], "prices": prices, "title": chapter_titles,
    "recent": model["scenarios"]["base"]["actual_ytd9"], "nodes": nodes, "cash": cash,
    "cashSources": audit["issuer"]["sources"], "facts": audit["issuer"]["current_fact_count"],
    "attach": assumptions["cohort"]["attach_2025"], "volume": volume, "revenueBridge": revenue_bridge,
    "gross": records("gross-contribution"), "groups": records("product-bridge"),
    "restatement": records("group-restatement"), "cost": records("cost-attribution"),
    "projects": records("commercialization-stages"), "projectStages":records("project-stages"),
    "bridge": records("value-bridge"), "equity": records("equity-bridge"),
    "cashHistory": records("cash-history"), "recentBridge": records("recent-income-bridge"),
    "major": model["receipt"]["major_changes"],
    "cases": {k: {x: v[x] for x in ("price", "terminal_share", "terminal_pv", "explicit_pv", "growth", "roic", "wacc", "enterprise_value", "equity_value")} for k,v in model["scenarios"].items()},
    "sourceRoot": META["source_root"],
}
linked = {r["file"]:r for r in records("index")}
for key in linked:
    if not (ROOT / key).is_file():
        raise ValueError(f"索引文件缺失 {key}")
source_rows = [[escape(r["chapter"]), f'<a href="{escape(r["file"])}">{escape(r["label"])}</a>', escape(r["scope"])] for r in linked.values()]
versions = f'<p>正文 <code>{escape(META["archive_commit"])}</code> 加 11 月 24 日两处证据接入。计算 <code>{escape(META["model_commit"])}</code>。图册采用的正文与模型指纹见版本清单。</p>'
source_block = f'''<section class="source-index" id="sources"><h2>版本与证据索引</h2>
    {versions}<div class="linkrow"><a href="src/versions.json">版本和指纹</a><a href="data/index.csv" download>图件与底表索引 CSV</a><a href="验收/体验验收.md">体验验收</a><a href="{escape(META['archive_url'])}">归档基线 ↗</a></div>
    <details><summary>展开图件、底表和原件索引</summary>{table(["章节","文件","用途"], source_rows)}</details>
    <details class="original" id="依据与研究边界"><summary>依据与研究边界</summary><div class="archive-body">{markdown(report[boundary:], True)}</div></details></section>'''
hero_labels = ["压力", "基准", "改善", "含权收盘"]
hero_values = prices + [data["market"]]
hero_band = "".join(f'<div class="{cls}"><small>{label}</small><strong>{value:.2f}</strong> <span>元／股</span></div>' for label,cls,value in zip(hero_labels, ["","baseline","","market"], hero_values))
template = read(SRC / "template.html")
for key, val in {
    "CSS": read(SRC / "atlas.css"), "JS": read(SRC / "atlas.js"),
    "NAV": "".join(nav), "CHAPTERS":"\n".join(chapters), "SOURCES":source_block,
    "HERO_STATS":hero_band, "DATA":json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
}.items():
    template = template.replace(f"@@{key}@@", val)
assert "@@" not in template
(ROOT / "index.html").write_text(template, encoding="utf-8", newline="\n")
print(f"图册已生成。{len(chapters)} 章，{len(history)} 个可比完整财年，{len(forecast)} 个预测行，{len(nodes)} 个价格节点，{len(linked)} 项索引。")
