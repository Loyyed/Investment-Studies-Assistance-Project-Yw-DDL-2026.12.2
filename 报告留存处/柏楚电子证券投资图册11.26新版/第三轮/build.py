"""Build the shared Markdown and offline HTML review edition."""
import csv,html,json,re,os,runpy
from decimal import Decimal as D
from pathlib import Path
from hashlib import sha256
import mistune
import pymupdf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams.update({"font.family":["Microsoft YaHei","sans-serif"],"font.size":11,"axes.spines.top":False,
                     "axes.spines.right":False,"axes.spines.left":False,"axes.grid":True,"grid.alpha":.16,
                     "axes.axisbelow":True,"figure.facecolor":"#f4faf8","axes.facecolor":"#f4faf8","axes.unicode_minus":False})
HERE=Path(__file__).resolve().parent
STAGE=HERE.parent
REPO=STAGE.parents[1]
FIRST,SECOND=STAGE/"第一轮",STAGE/"第二轮"
REPORT=STAGE.parent/"柏楚电子证券投资分析报告11.26新版.md"
CHARTS=HERE/"charts"
CHARTS.mkdir(exist_ok=True)
def rows(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write(p,data):
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,data[0].keys(),lineterminator="\n");w.writeheader();w.writerows(data)
for name,expected in json.loads((HERE/"输入指纹.json").read_text(encoding="utf-8")).items():
    assert sha256((HERE/name).read_bytes()).hexdigest()==expected,name
source={int(r["报告年度"]):r for r in rows(FIRST/"年报索引.csv")}
for yr,meta in source.items():
    local=Path(meta["本地原件"])
    if not local.exists():local=STAGE/"第四轮/年报原件"/local.name
    assert sha256(local.read_bytes()).hexdigest()==meta["SHA256"],yr
    meta["本地原件"]=str(local)
cells={r["单元ID"]:r for r in rows(FIRST/"清洗底表.csv")}
bridge=rows(SECOND/"经营桥明细.csv")
value={(r["计算段"],r["数据期"],r["项目"]):r for r in bridge}
def get(b,y,k):return float(value[b,str(y),k]["精确结果"])
def ids_for(*bs):return sorted({i for r in bridge if r["计算段"] in bs for i in r["第一轮底表单元"].split("；") if i})
def src(s):return str(Path(source[s]["本地原件"]))
def relative(p,base):return os.path.relpath(p,base).replace("\\","/")
# Physical PDF cell extraction, a new supplement to the frozen round-one data.
doc=pymupdf.open(src(2025))
table=next(t.extract() for t in doc[212].find_tables().tables if any(r[0]=="预提销售折扣" for r in t.extract()))
liab=[]
for n,r in enumerate(table,1):
    if r[0] in ("预提销售折扣","货款","合计"):
        for j,y in ((1,2025),(2,2024)):
            liab.append(dict(单元ID=f"L213-R{n}-C{j}",报告年度=2025,数据年度=y,PDF物理页=213,表名="合同负债情况",原行=r[0],
              原列="期末余额" if j==1 else "期初余额",原字面值=r[j],标准值=str(D(r[j].replace(",",""))),
              单位="人民币元",主体="上海柏楚电子科技股份有限公司及合并子公司",
              可获日期=source[2025]["可获日期"],来源SHA256=source[2025]["SHA256"]))
write(HERE/"合同负债补充原格.csv",liab)
lv={(int(r["数据年度"]),r["原行"]):D(r["标准值"]) for r in liab}
assert lv[2025,"预提销售折扣"]+lv[2025,"货款"]==lv[2025,"合计"]
assert lv[2024,"预提销售折扣"]+lv[2024,"货款"]==lv[2024,"合计"]
liab_calc=[
 dict(项目="折扣占期末余额",公式="114106284.20÷132387565.31×100",值=str(lv[2025,"预提销售折扣"]/lv[2025,"合计"]*100)),
 dict(项目="折扣占余额增量",公式="(114106284.20−94384129.34)÷(132387565.31−101328453.74)×100",
      值=str((lv[2025,"预提销售折扣"]-lv[2024,"预提销售折扣"])/(lv[2025,"合计"]-lv[2024,"合计"])*100))]
write(HERE/"合同负债计算.csv",liab_calc)
# Evidence used by both the report and chart drawer.
evidence=[
("E01","2025", "6、12–18","加工流程、产品功能、CAM、NC及传感控制","B04"),
("E02","2025","14、17、161–162","主要经营模式、标准产品安装、现场支持","B08"),
("E03","2025","119、160–162","合同、签收验收、年度折扣与软件确认政策","B08"),
("E04","2021–2025","2021 p25–26；2022 p26；2023 p25；2024 p26；2025 p28","直销分母与金额","B08"),
("E05","2024–2025","2024 p25、205；2025 p27–28、221","平面及其余场景的收入与毛利","B03、B04"),
("E06","2024–2025","2024 p25–26；2025 p28","地区收入与增量","B07"),
("E07","2019–2025","合并三表，逐年页码见单元索引","收入、利润和现金历史","B01、B02"),
("E08","2022","24–27、102–107、174、182–186","压力期、旧产品、现金及范围变化","B02、B05、B09"),
("E09","2024","112–113、153、205","2023比较成本质保重列","B02、B03"),
("E10","2025","125–126、222–224","扩张利润、费用、少数股东损益","B02"),
("E11","2024–2025","2024 p25–27；2025 p27–30","毛利中点分解与成本性质","B04、B06"),
("E12","2024–2025","2024 p26–27；2025 p27–30","软硬组合、实物结构与成本","B06、B11"),
("E13","2022、2024、2025","2022 p106–108、182–183；2024 p116–117、213–214；2025 p129–131、229–230","直接与间接现金桥、购建、现金转换","B01、B09"),
("E14","2024–2025","2024 p108–109；2025 p121–122、188","营运占用与资本","B10"),
("E15","2025","161–162、213","年度折扣政策及合同负债构成","L213"),
("E16","2024–2025","2024 p26；2025 p29","硬件库存差额","B11"),
("E17","2025","6、14–18、26、41","接口复用、竞争、成本与服务，研究反方","B01、B04、B09"),
]
write(HERE/"主张来源映射.csv",[dict(证据ID=i,报告年度=y,PDF物理页=pg,主张=t,计算段=b,单元索引="图表取数.csv及原格索引.csv") for i,y,pg,t,b in evidence])
refids=ids_for(*sorted({r["计算段"] for r in bridge}))
write(HERE/"原格索引.csv",[cells[i] for i in refids])
write(HERE/"图表取数.csv",bridge)
palette=["#328675","#679bd0","#ba8dc2","#d8a35b"]
groups=["平面解决方案","管材解决方案","三维解决方案","其他"]
chartmeta={}
def save(fig,key,title,unit,period,eid,blocks):
    fig.tight_layout(pad=2)
    fig.savefig(CHARTS/(key+".png"),dpi=155,bbox_inches="tight")
    plt.close(fig)
    chartmeta[key]=dict(title=title,unit=unit,period=period,evidence=eid,blocks=blocks,file="charts/"+key+".png")
def flow(key,title,items,foot):
    fig,ax=plt.subplots(figsize=(11,3.5));ax.axis("off")
    for i,(head,body) in enumerate(items):
        x=.02+i*.245
        ax.add_patch(FancyBboxPatch((x,.25),.215,.62,boxstyle="round,pad=.012,rounding_size=.04",
                   transform=ax.transAxes,facecolor=["#dceee8","#e1edf8","#e8e2f1","#f1e7d5"][i],edgecolor="none"))
        ax.text(x+.018,.74,head,transform=ax.transAxes,fontsize=13,weight="bold",va="top")
        ax.text(x+.018,.56,body,transform=ax.transAxes,fontsize=11,va="top",linespacing=1.6)
        if i<3:ax.annotate("",xy=(x+.242,.56),xytext=(x+.218,.56),xycoords="axes fraction",arrowprops=dict(arrowstyle="->",color="#467065"))
    ax.text(.02,.10,foot,transform=ax.transAxes,fontsize=10,color="#48625e")
    ax.set_title(title,loc="left",fontsize=16,pad=14)
    save(fig,key,title,"流程示意","2025","E01" if key=="process" else "E02、E03",[])
flow("process","从加工图到工件",[
("CAD 图形","读图与排样\n安排材料使用"),
("CAM 工艺","选择工艺与路径\n处理实物偏差"),
("NC 数控","规划轨迹与速度\n生成运动指令"),
("随动与执行","传感反馈调间距\n配合激光切割")],"年报功能披露整理。材料、激光与整机设置共同影响工件质量。")
flow("contract","从采购到回款",[
("设备制造商","合同与订单\n采购控制及配套"),
("柏楚交付","组装测试与供货\n现场技术支持"),
("签收与验收","达到合同标准\n对应收入确认"),
("结算与服务","年度折扣调整\n收款与售后维修")],"标准软件一般只需简单安装；整机配置、工艺验证、培训的具体工作量待项目证据。")
for y in (2024,2025):
    fig,axs=plt.subplots(1,2,figsize=(10,4.7))
    for ax,metric,title in zip(axs,["收入","毛利额"],["主营收入","主营毛利额"]):
        amounts=[get("B04",y,g+"·"+metric)/1e6 for g in groups]
        base=sum(amounts)
        ax.barh(groups,amounts,color=palette,height=.65)
        ax.invert_yaxis();ax.set_xlim(0,max(amounts)*1.42);ax.set_xlabel("人民币百万元")
        for i,a in enumerate(amounts):ax.text(a+base*.015,i,f"{a:,.1f} | {a/base*100:.2f}%",va="center",fontsize=10)
        ax.set_title(f"{y} {title}")
    save(fig,"structure"+str(y),"主营收入与毛利结构","人民币百万元、% ",str(y),"E05",["B04"])
fig,ax=plt.subplots(figsize=(10,4.7))
for label,metric,color in [("营业收入","营业收入",palette[0]),("合并净利润","合并净利润",palette[1]),("经营现金流","经营现金流净额",palette[2])]:
    vals=[get("B01",y,metric)/1e6 for y in range(2019,2026)]
    ax.plot(range(2019,2026),vals,"o-",label=label,color=color,lw=2.4)
ax.set_xticks(range(2019,2026));ax.set_ylabel("人民币百万元");ax.axvspan(2021.8,2022.2,color="#dae8e1",alpha=.6)
ax.legend(frameon=False);ax.set_title("七年收入、净利润与经营现金",loc="left")
save(fig,"history","七年经营","人民币百万元","2019–2025","E07",["B01"])
fig,ax=plt.subplots(figsize=(9,4.5))
ms=[get("B04","2024→2025","主营毛利率组合权重贡献"),get("B04","2024→2025","主营毛利率组内贡献")]
ax.barh(["场景权重变化","场景内部毛利率变化"],ms,color=palette[:2],height=.5)
ax.invert_yaxis();ax.set_xlim(-1.65,0.12);ax.set_xlabel("百分点")
for i,x in enumerate(ms):ax.text(x-.04,i,f"{x:.4f}",va="center",ha="right")
ax.set_title("主营毛利率 80.53% → 77.92%",loc="left")
save(fig,"margin","主营毛利率变动分解","百分点","2024→2025","E11",["B04"])
for y in (2022,2025):
    window=f"{y-1}→{y}"
    keys=["合并净利润变化","存货调节变动","应收调节变动","应付调节变动","其他间接调节变化","经营现金流变化"]
    vals=[get("B09",window,k)/1e6 for k in keys]
    fig,ax=plt.subplots(figsize=(10,4.8))
    running=0
    for i,a in enumerate(vals):
        start=0 if i==len(vals)-1 else running
        ax.bar(i,a,bottom=start,color=palette[0] if i==len(vals)-1 else palette[1] if a>=0 else palette[3],width=.64)
        end=start+a
        ax.text(i,end+(6 if a>=0 else -6),f"{a:+.2f}",ha="center",va="bottom" if a>=0 else "top",fontsize=10)
        if i<len(vals)-1:running=end
    ax.set_xticks(range(len(keys)),["净利润\n变化","存货\n调节","应收\n调节","应付\n调节","其他\n调节","CFO\n变化"])
    ax.axhline(0,color="#627d74",lw=.7);ax.set_ylim(min(0,min(vals))*1.3-20,max(0,max(vals),running)*1.32+15);ax.set_ylabel("人民币百万元")
    ax.set_title(window+" 利润到经营现金变化桥",loc="left")
    save(fig,"cash"+str(y),"利润到现金桥","人民币百万元",window,"E13",["B09"])
fig,ax=plt.subplots(figsize=(9,4.7))
for i,y in enumerate((2024,2025)):
    a,b=float(lv[y,"预提销售折扣"])/1e6,float(lv[y,"货款"])/1e6
    ax.barh(str(y),a,color=palette[0],label="预提销售折扣" if i==0 else None)
    ax.barh(str(y),b,left=a,color=palette[1],label="货款" if i==0 else None)
    ax.text(a/2,i,f"{a:.2f}",ha="center",va="center",color="white")
    ax.text(a+b/2,i,f"{b:.2f}",ha="center",va="center")
ax.set_xlabel("人民币百万元");ax.legend(frameon=False);ax.set_title("合同负债中的折扣与货款",loc="left")
save(fig,"liability","合同负债构成","人民币百万元","2024年末、2025年末","E15",["L213"])
runpy.run_path(str(STAGE/"协作深化/11.26整合/graphs.py"))
chartmeta.update(json.loads((STAGE/"协作深化/11.26整合/新增图表映射.json").read_text(encoding="utf-8")))
(HERE/"图表映射.json").write_text(json.dumps(chartmeta,ensure_ascii=False,indent=2),encoding="utf-8")
growthtable=["| 场景 | 2025收入 | 主营毛利额 | 收入增量 | 毛利增量 |","| --- | --- | --- | --- | --- |"]
for g in groups:
    growthtable.append("| "+g+" | "+" | ".join(f'{get("B04",period,g+"·"+key)/1e6:,.2f}' for period,key in
        [(2025,"收入"),(2025,"毛利额"),("2024→2025","收入变化"),("2024→2025","毛利变化")])+" |")
growthtable="金额单位为人民币百万元。2024→2025 增量，主营口径。\n\n"+"\n".join(growthtable)
lt=["| 合同负债项目 | 2024年末（元） | 2025年末（元） | 增加（元） |","| --- | --- | --- | --- |"]
for k in ("预提销售折扣","货款","合计"):
    lt.append(f'| {k} | {lv[2024,k]:,.2f} | {lv[2025,k]:,.2f} | {lv[2025,k]-lv[2024,k]:,.2f} |')
liabilitytable="\n".join(lt)
markdown=mistune.create_markdown(escape=False,plugins=["table"])
def figure(key,base):
    m=chartmeta[key];f=relative(HERE/m["file"],base)
    caption=f'{m["period"]} · {m["unit"]} · {m["evidence"]}，年报定位和计算见来源索引'
    return f'![{m["title"]}]({f})\n\n*{caption}*'
def md_source(text,base):
    text=text.replace("{{growthtable}}",growthtable).replace("{{liabilitytable}}",liabilitytable)
    for token,keys in {"process":["process"],"contract":["contract"],"structure":["structure2024","structure2025"],
                       "history":["history"],"margin":["margin"],"cash":["cash2022","cash2025"],"liability":["liability"],"moat":["moat"],"memberoriginal":["memberoriginal"],"cashsurplus":["cashsurplus"]}.items():
        text=text.replace("{{"+token+"}}","\n\n".join(figure(k,base) for k in keys))
    return text
def html_fig(key):
    m=chartmeta[key]
    mobile=m.get("mobile")
    picture=(f'<picture><source media="(max-width:850px)" srcset="{relative(HERE/mobile,STAGE)}"><img class="flowgraph" src="{relative(HERE/m["file"],STAGE)}" alt="{m["title"]}"></picture>' if mobile else f'<img src="{relative(HERE/m["file"],STAGE)}" alt="{m["title"]}">')
    return f'<figure data-chart="{key}"><div class="plot" tabindex="0" aria-label="{m["title"]}，可横向滚动查看">{picture}</div><figcaption>{m["period"]} · {m["unit"]} · <a href="#sources">{m["evidence"]} 年报与计算</a></figcaption></figure>'
def html_chapter(text):
    text=text.replace("{{growthtable}}",growthtable).replace("{{liabilitytable}}",liabilitytable)
    for token,keys in {"process":["process"],"contract":["contract"],"structure":["structure2024","structure2025"],
                       "history":["history"],"margin":["margin"],"cash":["cash2022","cash2025"],"liability":["liability"],"moat":["moat"],"memberoriginal":["memberoriginal"],"cashsurplus":["cashsurplus"]}.items():
        content="".join(html_fig(k) for k in keys)
        if len(keys)>1:
            buttons="".join(f'<button type="button" data-select="{k}" aria-pressed="{str(i==len(keys)-1).lower()}">{chartmeta[k]["period"]}</button>' for i,k in enumerate(keys))
            content=f'<div class="switcher"><div class="controls" role="group" aria-label="选择图表年份">{buttons}</div>{content}</div>'
        text=text.replace("{{"+token+"}}",content)
    content=markdown(text)
    content=re.sub(r'\[(E\d{2}(?:[^\]]*)?)\]',lambda m:f'<a class="citation" href="#{re.match(r"E\d{2}",m[1])[0]}">{m[1]}</a>',content)
    content=re.sub(r"〔(M1-[^〕]+)〕",lambda m:" · ".join(f'<a class="citation" href="#{i}">{i}</a>' for i in re.findall(r"M1-\d{2}",m[1])),content)
    return content
chapters=json.loads((HERE/"章节清单.json").read_text(encoding="utf-8"))
header="# 柏楚电子证券投资分析报告11.26新版\n\n署名 刘翔宇\n\n11.26新版 · 2026-11-26 · 以11.25四轮已审成果为基线\n\n执行为成员四Codex实施Agent；原四轮审核记录保留。本版新增内容实际核对见11.26整合验收记录。\n\n"
mds=[];sections=[]
for ch in chapters:
    text=(HERE/"chapters"/(ch["id"]+".md")).read_text(encoding="utf-8")
    mds.append(re.sub(r"^(#{1,5}) ",r"#\1 ",md_source(text,REPORT.parent),flags=re.M))
    sections.append(f'<section id="ch{ch["id"]}" class="chapter">{html_chapter(text)}</section>')
# Source drawer binds textual claims to exact source/compute rows.
source_rows=[]
for eid,y,pages,claim,blocks in evidence:
    linked=[]
    years=[int(y)] if y.isdigit() else sorted({int(z) for z in re.findall(r"20\d{2}",y)})
    for yr in years:
        named_page=re.search(str(yr)+r" p(\d+)",pages)
        pg="213" if eid=="E15" else (named_page.group(1) if named_page else
           re.search(r"(\d+)",pages).group(1) if y.isdigit() and re.search(r"\d",pages) else "1")
        f=Path(src(yr))
        linked.append(f'<a href="{relative(f,STAGE)}#page={pg}">{yr}年报</a>')
    source_rows.append(f'<tr id="{eid}"><td>{eid}</td><td>{html.escape(claim)}</td><td>{" · ".join(linked)}<br>{html.escape(pages)}</td><td>{blocks}</td></tr>')
sources_html='<section id="sources" class="chapter"><h1>年报、计算与原格</h1><p>原件以当前本地路径打开。PDF物理页从封面起算。原表单位、列位、可获日期和来源SHA见原格索引。首次跳转可按下表页码在PDF阅读器内定位。</p><div class="table-scroll"><table><thead><tr><th>定位</th><th>主张</th><th>年报与物理页</th><th>计算段</th></tr></thead><tbody>'+"".join(source_rows)+'</tbody></table></div>'
sources_html+='<p>'+" · ".join(f'<a href="{relative(Path(src(y)),STAGE)}">{y}完整年报</a>' for y in source)+'</p>'
sources_html+='<p><a href="第三轮/图表取数.csv">图表计算与公式 CSV</a> · <a href="第三轮/原格索引.csv">第一轮原格索引 CSV</a> · <a href="第三轮/合同负债补充原格.csv">合同负债新增原格</a> · <a href="第三轮/验收记录.md">验收记录</a></p><details><summary>展开图表精确数据与来源单元</summary><label for="query">按项目或计算段筛选</label><input id="query" placeholder="平面、合同、B09"><div class="table-scroll"><table id="raw-data"><thead><tr><th>段</th><th>期间</th><th>项目</th><th>结果</th><th>单位</th><th>第一轮单元</th></tr></thead><tbody>'
for r in bridge:
    sources_html+="<tr>"+"".join("<td>"+html.escape(r[k])+"</td>" for k in ("计算段","数据期","项目","精确结果","单位","第一轮底表单元"))+"</tr>"
sources_html+='</tbody></table></div></details></section>'
source_md="## 依据与来源\n\n数值以第一轮获准底表与第二轮经营桥为主。合同负债构成由2025年报p213单列补充原格。机制判断沿已审第二轮材料，原文自述与研究推断在相邻段说明。\n\n| 索引 | 年报年度和物理页 | 内容及计算 |\n| --- | --- | --- |\n"
source_md+="\n".join(f"| {i} | {y} · {pg} | {t} · {b} |" for i,y,pg,t,b in evidence)
source_md+="\n\n[主张来源映射]("+relative(HERE/"主张来源映射.csv",REPORT.parent)+") · [图表取数与公式]("+relative(HERE/"图表取数.csv",REPORT.parent)+") · [第一轮原格索引]("+relative(HERE/"原格索引.csv",REPORT.parent)+") · [合同负债原格]("+relative(HERE/"合同负债补充原格.csv",REPORT.parent)+")\n"
REPORT.write_text(header+"[交互图册](柏楚电子证券投资图册11.26新版/index.html) · [护城河](#护城河怎样形成并兑现) · [18项采用与证据](柏楚电子证券投资图册11.26新版/协作深化/11.26整合/逐条采用表.md)\n\n"+"\n\n".join(mds)+"\n\n"+source_md,encoding="utf-8")
css="""*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}body{margin:0;background:#eff7f4;color:#203f37;font:17px/1.85 'Microsoft YaHei',system-ui,sans-serif}a{color:#276b58;text-underline-offset:4px}aside{position:fixed;left:0;top:0;width:244px;height:100vh;overflow:auto;padding:32px 20px;background:#e0efea;border-right:1px solid #c9e0d6}aside a{display:block;padding:9px 12px;text-decoration:none;border-radius:14px;line-height:1.55;margin:6px 0;font-size:15px}aside a:hover,aside a.active{background:#fff;color:#1b624f}main{max-width:1110px;margin-left:244px;padding:38px 48px}header{padding:24px 10px 40px}header h1{font-size:36px;line-height:1.4;max-width:780px}header p{color:#506e63}h1{font-size:27px;line-height:1.5}h2{font-size:22px}p{margin:1.15em 0}section.chapter{background:#fff;border:1px solid #dcebe4;border-radius:28px;padding:32px;margin-bottom:28px;box-shadow:0 8px 35px #315e4807}figure{margin:25px 0 12px;background:#f4faf8;border-radius:20px;padding:10px}.plot{overflow:auto}figure img{display:block;width:100%;height:auto;border-radius:14px}figcaption{font-size:14px;padding:8px 12px;color:#506e63;line-height:1.7}table{border-collapse:collapse;font-size:15px;min-width:100%;line-height:1.65}th,td{padding:11px 14px;border-bottom:1px solid #d9e9e1;text-align:left;vertical-align:top}th{background:#eaf4ee}td{max-width:480px;overflow-wrap:anywhere}.table-scroll{overflow:auto;border-radius:15px;margin:20px 0}button{font:inherit;border:1px solid #b5d4c5;background:#fff;color:#285744;padding:7px 19px;border-radius:22px;cursor:pointer}button[aria-pressed=true]{background:#317a62;color:white}.controls{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.switcher figure[hidden]{display:none}.citation{font-size:14px}details{padding:16px;background:#f1f7f3;border-radius:17px}summary{cursor:pointer}input{width:100%;font:inherit;padding:10px;border:1px solid #a9c8ba;border-radius:12px}#raw-data{font-size:14px}#raw-data td:last-child{min-width:260px}.brand{font-weight:bold;font-size:21px;margin-bottom:20px}@media(max-width:850px){aside{position:sticky;top:0;width:100%;height:auto;z-index:5;padding:8px 12px;border-right:0;box-shadow:0 4px 12px #315e4812}.brand{display:none}nav{display:flex;overflow:auto;gap:5px}aside a{white-space:nowrap;margin:0;padding:7px 12px;font-size:14px}main{margin:0;padding:20px 12px}header h1{font-size:29px}section.chapter{padding:23px 19px;border-radius:23px}h1{font-size:24px}figure{margin-left:-8px;margin-right:-8px}figure img{min-width:650px}.plot{scrollbar-width:thin}body{font-size:16px}.controls button{font-size:15px;padding:6px 14px}td,th{padding:9px;min-width:100px}}@media print{aside,.controls{display:none}main{margin:0;padding:0}section.chapter{break-before:page;box-shadow:none;border:0}details{display:block}figure[hidden]{display:block!important}}"""
js="""document.querySelectorAll('.switcher').forEach(group=>{const buttons=[...group.querySelectorAll('button')];const apply=k=>{group.querySelectorAll('figure').forEach(f=>f.hidden=f.dataset.chart!==k);buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.select===k)))};buttons.forEach(b=>b.addEventListener('click',()=>apply(b.dataset.select)));apply(buttons.at(-1).dataset.select)});document.querySelectorAll('.chapter table').forEach(t=>{if(!t.parentElement.classList.contains('table-scroll')){const wrap=document.createElement('div');wrap.className='table-scroll';t.before(wrap);wrap.append(t)}});document.getElementById('query').addEventListener('input',e=>{document.querySelectorAll('#raw-data tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(e.target.value.toLowerCase()))});const obs=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))}}),{rootMargin:'-15% 0px -65% 0px'});document.querySelectorAll('section').forEach(e=>obs.observe(e));"""
nav="".join(f'<a href="#ch{c["id"]}">{c["title"]}</a>' for c in chapters)+'<a href="#m1-evidence">成员一18项与八文</a><a href="#sources">来源与原格</a>'
title="柏楚电子证券投资图册11.26新版"
page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+css+'.flowgraph{min-width:0!important;width:100%}picture{display:block;max-width:100%}section img{max-width:100%}svg{max-width:100%}</style></head><body><aside><div class="brand">柏楚电子 · 经营研究</div><nav>'+nav+'</nav></aside><main><header><p>11.26 新版 · 成员一成果完整整合</p><h1>一张加工图，怎样成为柏楚的利润和现金</h1><p>署名 刘翔宇<br>2026-11-26版 · 11.25四轮已审基线 · 2019–2025年报<br>成员四Codex实施Agent统一构建；新增内容核对与最终独立裁定分别记录。</p><p><a href="../柏楚电子证券投资分析报告11.26新版.md">Markdown 阅读稿</a> · <a href="第三轮/验收记录.md">审核与复算</a></p></header>'+"".join(sections)+(STAGE/"协作深化/11.26整合/证据索引.html").read_text(encoding="utf8")+sources_html+'</main><script>'+js+'</script></body></html>'
(STAGE/"index.html").write_text(page,encoding="utf-8")
(HERE/"审阅版.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>柏楚第三轮审阅版</title><a href="../index.html">打开第三轮图册</a></html>',encoding="utf-8")
print(json.dumps({"chapters":len(chapters),"figures":len(chartmeta),"compute_rows":len(bridge),"source_cells":len(refids),"discount_pct":liab_calc[0]["值"],"discount_delta_pct":liab_calc[1]["值"]},ensure_ascii=False))
