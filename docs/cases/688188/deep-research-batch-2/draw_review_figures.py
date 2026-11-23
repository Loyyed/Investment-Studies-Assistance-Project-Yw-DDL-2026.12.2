"""Render the reading edition's PNGs without changing forecast or evidence inputs."""
import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.ticker import FuncFormatter, PercentFormatter
import numpy as np

from forecast import CASE, HERE, OUT, PRIOR, read_json, rows, write_csv
from review_assets import DEFAULT_CACHE, FONT, ensure_asset

FIGURES = HERE / "figures"
PAPER, INK, MUTED, GRID = "#faf9f5", "#16323a", "#47616a", "#d5dfdb"
TEAL, RUST, BLUE, GOLD = "#157565", "#9f4b38", "#3e658c", "#ae7832"
CASES = {"stress": ("压力", RUST, "o"), "base": ("基准", TEAL, "s"), "improve": ("改善", BLUE, "^")}


def setup(font):
    fontManager.addfont(font)
    plt.rcParams.update({
        "font.family": FontProperties(fname=font).get_name(), "font.size": 12.5,
        "text.color": INK, "axes.labelcolor": MUTED, "axes.facecolor": PAPER,
        "axes.unicode_minus": False, "axes.edgecolor": GRID, "figure.facecolor": PAPER,
        "xtick.color": MUTED, "ytick.color": MUTED, "grid.color": GRID, "savefig.facecolor": PAPER,
    })
    FIGURES.mkdir(exist_ok=True)


def canvas(title, subtitle, size=(9.2, 4.2)):
    fig = plt.figure(figsize=size)
    fig.text(.055, .956, title, va="top", fontsize=20, weight="bold")
    fig.text(.055, .855, subtitle, va="top", fontsize=12.2, color=MUTED)
    return fig


def footer(fig, note):
    fig.text(.055, .035, note, color=MUTED, fontsize=9.6, va="bottom")


def save(fig, name):
    fig.savefig(FIGURES / name, dpi=150, metadata={"Software": "Bochu research chart renderer"})
    plt.close(fig)


def axes(fig, rect=(.13,.19,.79,.56), grid="y"):
    ax = fig.add_axes(rect)
    for k in ("top", "right"):
        ax.spines[k].set_visible(False)
    ax.tick_params(length=0, pad=6)
    if grid:
        ax.grid(axis=grid)
    ax.set_axisbelow(True)
    return ax


def value_dots(model):
    close = model["receipt"]["market"]
    fig = canvas("三情景如何落在收盘价两侧？",
                 "2026-11-12 同日含权口径｜元／股", (9.2,3.6))
    ax = axes(fig,(.115,.25,.81,.48),"x")
    ax.set_xlim(25,154)
    ax.set_ylim(-.49,2.55)
    ax.invert_yaxis()
    ax.set_yticks(list(range(3)),[x[0] for x in CASES.values()])
    ax.axvline(close,color=INK,linestyle="--",lw=1.8)
    ax.annotate(f"收盘 {close:.2f}",(close,-.38),xytext=(7,0),textcoords="offset points",
                va="center",color=INK)
    for p,(key,(_,color,marker)) in enumerate(CASES.items()):
        v=model["scenarios"][key]["price"]
        ax.hlines(p,min(v,close),max(v,close),color=color,alpha=.36,lw=3)
        ax.scatter(v,p,color=color,s=85,marker=marker,zorder=3)
        ax.annotate(f"{v:.2f}",(v,p),xytext=(8,-2),textcoords="offset points",va="center",color=color)
    footer(fig,"色点为条件估值，虚线为交易观察。来源：data/model.json。")
    save(fig,"01-valuation.png")


def history():
    fy=[r for r in rows(PRIOR/"financial-bridge.csv") if r["period"].endswith("FY") and r["column"]=="本期"]
    pre=defaultdict(dict)
    for r in rows(PRIOR/"pre-ipo.csv"):
        pre[int(r["期间"])][r["原行"]]=float(r["原披露值"])/1e6
    interim={r["item"]:r for r in rows(OUT/"recent-income-bridge.csv")}
    fig=canvas("三条经营线在哪些年份分化？","2016–2025 年度；右侧为前三季累计｜百万元人民币",(9.2,6.7))
    for i,(name,k,ipo_label,color) in enumerate((
      ("营业收入","revenue","营业总收入",TEAL), ("核心 EBIT","core_ebit",None,BLUE),
      ("经营活动现金流","cfo","经营活动产生的现金流量净额",RUST))):
        y=.62-i*.216
        ax=axes(fig,(.128,y,.596,.164))
        side=axes(fig,(.772,y,.15,.164))
        vals={int(r["period"][:4]):float(r[k])/1e6 for r in fy}
        points=[float(interim[k][key])/1e6 for key in ("ytd25","ytd26")]
        ceiling=max(max(vals.values()),*points)*1.24
        for panel in (ax,side):
            panel.set_ylim(0,ceiling)
            panel.locator_params(axis="y",nbins=3)
        ax.set_ylabel(name,fontweight="bold",color=color)
        ax.set_xlim(2015.75,2025.35)
        ax.axvspan(2015.75,2018.5,color="#ebe7dc",alpha=.8)
        ax.axvspan(2021.65,2022.35,color="#ecd9d2",alpha=.8)
        for year in (2023,2024):
            ax.axvline(year,color="#7c8882",ls=":" if year==2023 else "--",lw=1)
        if ipo_label:
            ax.plot(sorted(pre),[pre[year][ipo_label] for year in sorted(pre)],marker="o",
                    color=color,lw=1.65,ls="--",mfc=PAPER)
        ax.plot(list(vals),list(vals.values()),color=color,lw=2.0,marker="o",ms=4)
        # Comparable cumulative observations stand in their own panel.
        side.scatter([0,1],points,s=56,c=[color,color],marker="D")
        side.set_xlim(-.45,1.45)
        side.set_yticklabels([])
        ax.set_xticks([2016,2018,2020,2022,2023,2024,2025])
        side.set_xticks([0,1],["25前三季","26前三季"],fontsize=10.5)
        if i!=2:
            ax.set_xticklabels([])
            side.set_xticklabels([])
    fig.text(.128,.802,"年度原列｜上市前虚线；核心 EBIT 早期无同口径值",fontsize=11.3,color=MUTED)
    fig.text(.76,.802,"近期独列",fontsize=11.3,color=MUTED)
    footer(fig,"浅棕：上市前。浅红：2022 压力期。点线：2023 质保重列；虚线：2024 分类断点。")
    fig.text(.055,.012,"来源：首批招股书、财务与重述桥；近期利润桥。年度实绩与季度累计之间留空。",fontsize=9.6,color=MUTED)
    save(fig,"09-operating-history.png")


def waterfall(ax, labels, book, changes, end, unit, lower=None):
    total=book
    cells=[(0,book,TEAL,book)]
    for change in changes:
        cells.append((min(total,total+change),abs(change),TEAL if change>=0 else RUST,change))
        total+=change
    cells.append((0,end,BLUE,end))
    scale=max(book,end)-min(book,end)
    for i,(bottom,height,color,label) in enumerate(cells):
        ax.bar(i,max(height,1e-12),bottom=bottom,color=color,width=.60,zorder=3)
        maximum=bottom+height
        labelstr=(f"{label:+.2f}" if i not in (0,len(cells)-1) else f"{label:,.2f}")
        if i not in (0,len(cells)-1) and abs(label)<.005 and label!=0:
            labelstr=f"{label:+.6f}"
        ax.annotate(labelstr,(i,maximum),xytext=(0,6),textcoords="offset points",
                    ha="center",fontsize=10.4,color=INK)
        if i<len(cells)-1:
            link=bottom if i and label<0 else maximum
            ax.plot([i+.30,i+.70],[link,link],color=MUTED,ls=":",lw=1.0)
    ax.set_xticks(range(len(labels)),labels,fontsize=10.8)
    ceiling=max(x[0]+x[1] for x in cells)
    ax.set_ylim(lower if lower is not None else 0,ceiling+max(scale*.27,ceiling*.023))
    ax.set_ylabel(unit)


def operating_waterfalls():
    solution=rows(OUT/"group-restatement.csv")
    starts=sum(float(r["revenue24"]) for r in solution)/1e6
    ends=sum(float(r["revenue25"]) for r in solution)/1e6
    op=read_json(CASE/"operating-summary.json")
    dv=op["volume_contribution_m"]
    mix=op["realisation_mix_contribution_m"]
    residue=ends-starts-dv-mix
    fig=canvas("主业多卖的收入有多少来自控制当量？",
               "2024→2025 主营收入｜百万元人民币；纵轴从 1,600 起")
    ax=axes(fig)
    waterfall(ax,["2024 主营","控制当量","组价与结构","2025 主营"],starts,[dv,mix],ends,"百万元",1600)
    footer(fig,f"较精确合计尾差 {residue:+.2e} 百万元。组价含结构。来源：operating-summary.json 与分组底表。")
    save(fig,"14-revenue-bridge.png")

    def margin(yr):
        gross=sum(float(r["revenue"+yr]) - float(r["cost"+yr]) for r in solution)
        return 100*gross/sum(float(r["revenue"+yr]) for r in solution)
    changes=[r for r in rows(OUT/"gross-contribution.csv") if r["period"]=="24→25"]
    m1,m2=(sum(float(r[k]) for r in changes) for k in ("margin_mix_pp","margin_inside_pp"))
    a,b=margin("24"),margin("25")
    fig=canvas("主业扩张为何压低了毛利率？","2024→2025 主营毛利率｜水平为 %，变化为百分点；纵轴从 76 起")
    ax=axes(fig)
    waterfall(ax,["2024 毛利率","组合权重","组内毛利","2025 毛利率"],a,[m1,m2],b,"毛利率（%）",76)
    footer(fig,f"中点法均摊交互项，合计尾差 {b-a-m1-m2:+.2e} 个百分点。来源：gross-contribution.csv。")
    save(fig,"15-gross-margin.png")


def quarter():
    inc={r["item"]:r for r in rows(OUT/"recent-income-bridge.csv")}
    values=lambda name:[float(inc[name][k])/1e6 for k in ("q3_25","q3_26")]
    revenue,core,cash=(values(k) for k in ("revenue","core_ebit","cfo_less_capex"))
    gross=[100*a/b for a,b in zip(values("gross"),revenue)]
    fig=canvas("2026Q3 四个指标为什么走出不同方向？",
               "2025Q3 与 2026Q3 单季｜金额单位为百万元人民币，毛利率单位为 %",(9.2,5.0))
    for i,(name,pts,margin) in enumerate((
        ("营业收入",revenue,False),("核心 EBIT",core,False),
        ("毛利率",gross,True),("CFO－购建",cash,False))):
        bottom=.48 if i<2 else .145
        ax=axes(fig,(.135+(i%2)*.45,bottom,.31,.22))
        ax.set_ylim(0,max(pts)*1.31)
        ax.bar([0,1],pts,color=["#a7bab9",TEAL if pts[1]>=pts[0] else RUST],width=.49)
        ax.set_xlim(-.50,1.63)
        ax.set_xticks([0,1],["2025Q3","2026Q3"],fontsize=9.6)
        d=f"{pts[1]-pts[0]:+.2f} 个百分点" if margin else f"{pts[1]/pts[0]-1:+.2%}"
        ax.set_title(f"{name}  {d}",fontsize=12.9,loc="left",color=INK,pad=4)
        for j,v in enumerate(pts):
            ax.text(j,v+max(pts)*.028,f"{v:.2f}",ha="center",fontsize=10.1)
        ax.set_yticks([])
    footer(fig,"实绩及累计差分。CFO－购建不是模型 FCFF。来源：recent-income-bridge.csv。")
    save(fig,"17-quarter-signals.png")


def bundle_heatmap():
    basis=[r for r in rows(OUT/"bundle-cash-thresholds.csv") if float(r["gross_margin"])==.50]
    cost,net,tax,ap,install,capex,allowance,service=(
        float(basis[0][k]) for k in ("cost","net_sales","cash_tax","ap_days","installation","gross_capex",
                                    "control_allowance","service_scenario"))
    def cash(inv,ar):
        return ((net-cost-install-allowance-service)*(1-tax)
                - (cost*inv/365+net*ar/365-cost*ap/365) - capex)
    for r in basis:
        assert abs(cash(float(r["inventory_days"]),float(r["ar_days"]))-float(r["first_cohort_cash"]))<1e-9
    inv=np.arange(70,181,5)
    ar=np.arange(20,91,5)
    xx,yy=np.meshgrid(inv,ar)
    zz=cash(xx,yy)
    write_csv("bundle-cash-heatmap.csv",[
        dict(inventory_days=int(x),ar_days=int(y),margin=.50,net_sales=net,hardware_cost=cost,
             installation=install,control_allowance=allowance,cash_tax=tax,ap_days=ap,
             gross_capex=capex,service=service,first_cohort_cash=float(cash(x,y)),
             unit="元／每100元增量净收入",source="bundle-cash-thresholds.csv")
        for y in ar for x in inv])
    fig=canvas("同样的毛利，配套回款什么时候转负？",
               "50% 硬件毛利｜库存天数 × 应收天数｜每 100 元增量净收入的首批现金",(9.2,5.25))
    ax=axes(fig,(.13,.20,.70,.53),None)
    image=ax.pcolormesh(inv,ar,zz,cmap="BrBG",norm=TwoSlopeNorm(vcenter=0),shading="nearest")
    ax.set_xlim(70,180); ax.set_ylim(20,90)
    ax.contour(xx,yy,zz,levels=[0],colors=[INK],linewidths=2)
    ax.set_xlabel("库存（天）"); ax.set_ylabel("应收（天）")
    for x,y,dx,dy in [(110,45,-49,-33),(150,65,8,19)]:
        ax.scatter([x],[y],marker="o",s=70,color=INK,edgecolor="white",lw=1.3,zorder=4)
        ax.annotate(f"{x}／{y}天：{cash(x,y):+.2f}元",(x,y),xytext=(dx,dy),textcoords="offset points",
                    arrowprops={"arrowstyle":"-","color":INK,"lw":.8},fontsize=11.5,
                    bbox={"facecolor":PAPER,"alpha":.94,"pad":4,"edgecolor":"none"})
    cax=fig.add_axes((.86,.20,.017,.53))
    fig.colorbar(image,cax=cax,label="首批现金（元）")
    footer(fig,"黑线为零现金；负值在右上。安装 4 元、让利 2 元、售后 5 元、购建 3 元、现金税率 13%。")
    fig.text(.055,.013,"应付固定 50 天。条件试算；来源：bundle-cash-thresholds.csv。", fontsize=9.6,color=MUTED)
    save(fig,"23-bundle-heatmap.png")


def commercial_stages():
    inputs=rows(OUT/"project-conditional-scale.csv")
    # Current evidence labels stay in the original project table. The matrix
    # shows exactly which links can be used without matching individual orders.
    stages=(
      ("切割头增量", ("无独立分母","产品已有","见批量销售","缺单批链","缺配套回款","缺独立回报"),
                   "批量销售", "既有硬件保留；额外增量需同订单毛利、服务、周转"),
      ("免示教弧焊", ("有行业场景","方案／合作","缺匹配订单","缺通过批次","缺对应回款","缺已兑现值"),
                   "方案及合作", "核连续批次的验收、复购、回款及资本"),
      ("锂电激光焊", ("有规划场景","技术路径","未匹配","未匹配","未匹配","仅规划 IRR"),
                   "预算及技术路径", "核工位订单、良率、验收与回款"),
      ("超快精密微加工", ("有产品场景","功能与研发","未匹配","未匹配","未匹配","缺独立回报"),
                   "功能及研发", "核量产替代、验收和重复回款"),
    )
    heads=("可服务需求","适配","订单","验收","回款","资本回报")
    found={r["project"]:r for r in inputs}
    write_csv("commercialization-stages.csv",[
        dict(project=name,**dict(zip(heads,cells)),highest_stage=key,model_gate=gate,
             original_evidence=found[name]["highest_evidence"],locator=found[name]["locator"],
             source="project-conditional-scale.csv；首批 project-stages.csv")
        for name,cells,key,gate in stages])
    fig=canvas("四项业务各自走到了哪一步？","公开材料的证据阶段｜截至 2026-11-23；期后表述独列",(9.75,5.1))
    a=fig.add_axes((.035,.29,.93,.45)); a.axis("off")
    tab=a.table(cellText=[(n,*c) for n,c,_,_ in stages],colLabels=("项目",*heads),loc="center",
                cellLoc="center",colWidths=[.21]+[.128]*6)
    tab.auto_set_font_size(False);tab.set_fontsize(11)
    marks={(1,2),(1,3),(2,2),(3,2),(4,2)}
    for (i,j),cell in tab.get_celld().items():
        cell.set_edgecolor("#f7f6ef")
        cell.set_height(.18 if i==0 else .198)
        cell.set_facecolor("#d3e5dc" if (i,j) in marks else "#e5ece8" if i==0 or j==0 else "#f1eee6")
        cell.get_text().set_color(INK)
    for i,(name,_,stage,gate) in enumerate(stages):
        fig.text(.058,.256-i*.043,f"{name} · {stage}｜{gate}",color=INK,fontsize=10.55)
    footer(fig,"深色代表有对应进展材料；空缺字段继续查证。来源：项目条件表、募投与路演证据。")
    save(fig,"24-commercial-stage.png")


def cash_path(model):
    fig=canvas("实际收现与三情景 FCFF 怎样接续？",
               "金额为百万元人民币｜实际 CFO－购建与情景 FCFF 分面展示",(10.0,4.85))
    a=axes(fig,(.085,.28,.18,.43)); b=axes(fig,(.34,.28,.42,.43)); c=axes(fig,(.825,.28,.135,.43))
    fig.text(.085,.752,"实际累计",fontsize=12.5,color=INK)
    fig.text(.34,.752,"全年估计及逐年情景",fontsize=12.5,color=INK)
    fig.text(.815,.752,"估值日后桩段",fontsize=11.7,color=INK)
    row=next(x for x in rows(OUT/"recent-income-bridge.csv") if x["item"]=="cfo_less_capex")
    bars=[float(row[k])/1e6 for k in ("ytd25","ytd26")]
    a.bar([0,1],bars,color=["#96aaa6",TEAL],width=.50)
    a.set_ylim(0,1050)
    a.set_xticks([0,1],["25前三季","26前三季"],fontsize=9.4)
    for j,n in enumerate(bars):
        a.text(j,n+22,f"{n:.0f}",ha="center",fontsize=10.6)
    b.axvspan(2025.6,2026.40,color="#ebeadc")
    for k,(name,color,marker) in CASES.items():
        s=model["scenarios"][k]
        numbers=[r["fcff"] for r in s["path"]]+[s["stable_2036"]["fcff"]]
        b.plot(range(2026,2037),numbers,lw=2.0,color=color,marker=marker,ms=3.8,label=name)
        b.scatter([2026],[numbers[0]],color=color,edgecolor=PAPER,s=35,zorder=4)
        c.scatter([s["path"][0]["valued_cash"]],[list(CASES).index(k)],c=color,marker=marker,s=62)
    b.set_xticks([2026,2027,2029,2031,2033,2036],["26E","27","29","31","33","36"],fontsize=10.5)
    b.set_ylim(0)
    b.legend(frameon=False,ncols=3,loc="upper left",fontsize=10.1,handlelength=1.25,columnspacing=.7)
    c.set_yticks([0,1,2],["压力","基准","改善"],fontsize=9.7)
    c.invert_yaxis()
    c.set_xlim(60,225);c.set_xticks([80,150,220])
    fig.text(.085,.155,"历史现金代理",fontsize=10.5,color=MUTED)
    fig.text(.34,.155,"2026 浅色带为全年估计；2036 为稳定期",fontsize=10.5,color=MUTED)
    fig.text(.808,.155,"2026-11-12 后未折现",fontsize=10.5,color=MUTED)
    footer(fig,"各分面纵轴各异，实际累计与全年估计之间不连线。来源：近期利润桥、forecast.csv 及 model.json。")
    save(fig,"31-fcff-path.png")


def valuation_bridge():
    data=rows(OUT/"value-bridge.csv")
    start=float(data[0]["price_after"])
    last=float(data[-1]["price_after"])
    changes=[float(r["share_delta"]) for r in data[1:]]
    fig=canvas(f"同一天的估值为何从 {start:.2f} 降到 {last:.2f}？",
               "2026-11-12｜每股元；纵轴从 75 起；边际差额按桥接顺序")
    ax=axes(fig,(.11,.24,.83,.50))
    waterfall(ax,["冻结基准","日后桩段","显性\nNOPAT","显性\n净再投资","终值","WACC",
                  "现金差额","新版基准"],start,changes,last,"元／股",75)
    footer(fig,f"逐项勾稽尾差 {last-start-sum(changes):+.2e} 元。资料：value-bridge.csv。")
    save(fig,"34-value-bridge.png")


def contours(model):
    grid=rows(OUT/"price-contours.csv")
    cash=model["receipt"]["market"]
    cond={25:("库存 +25 天／售后 +2pp",RUST,"^",(0,(2,2))),
          0:("库存、售后维持基准",TEAL,"o","-"),
          -25:("库存 −25 天／售后 −0.6pp",BLUE,"s","--")}
    fig=canvas(f"{cash:.2f} 元要求多少控制量和稳定利润率？",
               "2026-11-12 同价反推｜横轴为 2027 控制量增速，纵轴为稳定核心 EBIT 率",(9.2,5.5))
    ax=axes(fig,(.127,.33,.80,.43))
    all_x=sorted({round(100*float(r["computed_2027_volume_growth"]),7) for r in grid})
    any_root={round(100*float(r["computed_2027_volume_growth"]),7) for r in grid if r["root"]}
    missing=[x for x in all_x if x not in any_root]
    if missing:
        right=(max(missing)+min(any_root))/2
        ax.axvspan(min(all_x)-.48,right,color="#ece6dd",alpha=.9)
        ax.text(np.mean(missing),.94,"无解网格",transform=ax.get_xaxis_transform(),
                ha="center",va="top",color=MUTED,fontsize=11)
    for inv,(label,color,marker,style) in cond.items():
        group=sorted((z for z in grid if int(z["inventory_days_shift"])==inv),
                     key=lambda r:float(r["computed_2027_volume_growth"]))
        x=[100*float(r["computed_2027_volume_growth"]) for r in group]
        y=[100*float(r["stable_core_ebit_margin"]) if r["root"] else np.nan for r in group]
        ax.plot(x,y,lw=1.8,marker=marker,color=color,ls=style,ms=5,label=label)
    ax.set_xlim(min(all_x)-.48,max(all_x)+.60)
    ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_xlabel("2027 控制量增速");ax.set_ylabel("稳定核心 EBIT 率")
    ax.legend(loc="upper center",bbox_to_anchor=(.5,-.33),ncols=2,frameon=False,fontsize=10.25,columnspacing=1.3)
    footer(fig,"缺根时断线。阴影只标各条件均无解的已测网格，实际边界见上下限价格。来源：price-contours.csv。")
    save(fig,"37-price-contour.png")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache",type=Path,default=DEFAULT_CACHE)
    opt=parser.parse_args()
    setup(ensure_asset(FONT,opt.cache))
    model=read_json(OUT/"model.json")
    value_dots(model)
    history()
    operating_waterfalls()
    quarter()
    bundle_heatmap()
    commercial_stages()
    cash_path(model)
    valuation_bridge()
    contours(model)
    print("10 data charts; 2 derived CSVs")


if __name__=="__main__":
    main()
