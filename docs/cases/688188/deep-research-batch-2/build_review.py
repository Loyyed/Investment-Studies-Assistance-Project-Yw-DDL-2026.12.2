"""Render one continuous Markdown/HTML report from chapters and the audit tables."""
from html import escape
import re

from forecast import CASE, HERE, OUT, PRIOR, read_json, rows

CHAPTERS = ("摘要与判断","商业模式与竞争","多年经营阶段","收入、成本和费用","资本、现金和回报",
            "新业务和海外","逐年预测和留出","估值、权益和反推","反方与裁定")
COLORS = ("#1c705e","#8b6947","#537890")


def make_table(headers, values):
    header = "".join(f"<th>{escape(str(x))}</th>" for x in headers)
    body = "".join("<tr>"+"".join(f"<td>{escape(str(x))}</td>" for x in row)+"</tr>" for row in values)
    md = "\n".join(["| "+" | ".join(map(str,headers))+" |",
                    "| "+" | ".join("---" for _ in headers)+" |",
                    *("| "+" | ".join(map(str,row))+" |" for row in values)])
    return '<div class="tablewrap"><table><thead><tr>'+header+'</tr></thead><tbody>'+body+'</tbody></table></div>',md


def machine_flow(pieces):
    html = '<div class="flow">'+"".join(f"<span><b>{escape(k)}</b>{escape(v)}</span>" for k,v in pieces)+"</div>"
    return html,"\n\n".join(f"**{k}**　{v}" for k,v in pieces)


def legends(series):
    return '<div class="legend">'+"".join(f'<span style="--c:{COLORS[i]}">{escape(s)}</span>'
                                         for i,s in enumerate(series))+"</div>"


def bars(labels, series, data, fmt=lambda n:f"{n:.1f}"):
    maximum=max(abs(x) for group in data for x in group) or 1
    markup=[]
    for label,values in zip(labels,data):
        stack=[]
        for i,x in enumerate(values):
            height=90*abs(x)/maximum
            color=COLORS[i] if x>=0 else "#ae6046"
            stack.append(f'<i class="bar" style="--bp:{height:.5f};--c:{color}" title="{escape(series[i])} {fmt(x)}"><strong>{fmt(x)}</strong></i>')
        markup.append('<div class="bar-group"><div class="bar-stack">'+"".join(stack)+f'</div><span class="bar-name">{escape(label)}</span></div>')
    table=make_table(("期间",*series),[(x,*(fmt(y) for y in z)) for x,z in zip(labels,data)])
    html = ('<div class="chart"><div aria-hidden="true" class="bars" style="--n:'+str(len(labels))+'">'
            +"".join(markup)+'</div>'+legends(series)+table[0]+"</div>")
    return html,table[1]


def contour_graph(grid):
    runs=[(25,"备货与售后负担高"),(0,"基准周转与售后"),(-25,"周转与售后较轻")]
    svg=['<div class="cross-plot">']
    for i in (52,54,56,58,60,62):
        svg.append(f'<span class="yl" style="--y:{(i-50)*100/16}%">{i}%</span>')
    for i in (6,8,10,12,14):
        svg.append(f'<span class="xl" style="--x:{(i-5)*100/10}%">{i}%</span>')
    table = []
    for i,(inventory,label) in enumerate(runs):
        series=[r for r in grid if int(r["inventory_days_shift"])==inventory and r["root"]]
        pts = []
        for r in series:
            x0=float(r["computed_2027_volume_growth"])*100
            y0=float(r["stable_core_ebit_margin"])*100
            if not (5<=x0<=15 and 50<=y0<=66):
                continue
            x,y=(x0-5)*10,(y0-50)*6.25
            pts.append((x,100-y))
            svg.append(f'<b style="--x:{x}%;--y:{y}%;--c:{COLORS[i]}" title="{label} 量增{x0:.2f}% 利润率{y0:.2f}%"></b>')
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
            shape=f"{x1}% {y1-.35}%,{x1}% {y1+.35}%,{x2}% {y2+.35}%,{x2}% {y2-.35}%"
            svg.insert(1,f'<i class="segment" style="--shape:{shape};--c:{COLORS[i]}"></i>')
        r=next(r for r in series if float(r["control_new_shock_of_prior_units"])==.06)
        table.append((label,f"{float(r['computed_2027_volume_growth']):.2%}",f"{float(r['stable_core_ebit_margin']):.2%}",f"{float(r['reprice']):.2f}"))
    return "".join(svg)+"</div>"+legends([x[1] for x in runs])+make_table(("资本与履约条件","2027控制量增速","所需稳定核心率","回代元"),table)[0],make_table(("资本与履约条件","2027控制量增速","所需稳定核心率","回代元"),table)[1]


def m(x):
    return f"{float(x)/1e6:,.2f}"


def ins(x):
    return f"{float(x):,.2f}"


def pct(x):
    return f"{float(x):.2%}"


def build_tables(model, audit, first_pages):
    a={}
    def put(k,title,chart,source,description):
        a[k]=(title,chart,source,description)
    def drv(k,title,pieces,source,desc):
        put(k,title,machine_flow(pieces),source,desc)
    def tab(k,title,headers,values,source,desc):
        put(k,title,make_table(headers,values),source,desc)
    def b(k,title,labels,series,data,source,desc,fmt=ins):
        put(k,title,bars(labels,series,data,fmt),source,desc)

    rec=model["receipt"]
    cases=model["scenarios"]
    names={"base":"基准","stress":"压力","improve":"改善"}
    base=cases["base"]
    cash=rows(OUT/"cash-history.csv")
    facts=rows(PRIOR/"financial-bridge.csv")
    years=[r for r in facts if r["period"].endswith("FY") and r["column"]=="本期"]
    qtr={r["item"]:r for r in rows(OUT/"recent-income-bridge.csv")}
    gm=rows(OUT/"gross-contribution.csv")

    tab("scenarios","每股估值与含权价差",("经营情景","每股价值·元","较96.20元价差","收益率差额","终值占EV"),
        [(names[n],ins(c["price"]),f"{c['price']-rec['market']:+.2f}",f"{c['price']/rec['market']-1:+.2%}",pct(c["terminal_share"]))
         for n,c in cases.items()],"data/model.json","截至同日可得资料，三情景无概率权重。")
    t='<ul class="toc">'+"".join(f'<li><a href="#page-{p}"><span>{i+1:02d} {name}</span><span>{p:02d}</span></a></li>'
                                for i,(name,p) in enumerate(zip(CHAPTERS,first_pages)))+"</ul>"
    put("toc","九章阅读路径",(t,"\n".join(f"- {i+1:02d} {name}　p{p}" for i,(name,p) in enumerate(zip(CHAPTERS,first_pages)))),
        "README.md","正文 40 页；逐年明细和原件索引在同目录证据包。")
    drv("chain","设备、验收与收款的流向",[
        ("光源／光学","为工艺提供能量及传输"),("控制与头","图纸、刀路、工艺、随动协调"),
        ("OEM／集成","选型、组装、调试、交工"),("终端制造","按可用产出和合同验收"),
        ("现金回流","终端付整机价；OEM付部件、系统及约定服务")],
        "../deep-research-batch-1/mechanisms.md","流程为产业机制；实际付款和质保依订单。")
    t23=rows(OUT/"2023-product-original.csv")
    tab("p23","旧产品分类与主营闭合",("原产品", "收入·百万元","成本·百万元","毛利·百万元"),
        [(r["classification"],m(r["revenue"]),m(r["cost"]),m(r["gross"])) for r in t23],
        "data/2023-product-original.csv","2023年报 p24 原本期，质保重列前。")
    drv("renewal","续购应分别看到选择、现场成本与价格",[
        ("首选验证","比较合格工件、兼容和调机工时"),("原机留存","同机型需重新选择的批次作为分母"),
        ("单位经济","净报价＋停机、良率、培训"),
        ("竞价风险","同协议多供或自研且报价更低")],
        "../deep-research-batch-1/mechanisms.md","客户覆盖、实际可重选数和复购数分列。")
    tab("delivery","合同边界与现金暴露",("交付物","付款人及验收","增量资金风险"),[
        ("控制","OEM；约定系统功能及机型调试","研发、量产备件、OEM账期"),
        ("控制＋头","OEM；成套匹配及质保","部件入库、适配、维修、折扣"),
        ("整线及项目","集成或工厂；工位与现场验收","预收、发出、驻场、尾款和项目购建")],
        "data/bundle-cash-thresholds.csv","典型合同责任分析；具体订单条款待核。")
    tab("counting","同一合同额和设备怎样计一次",("对象","条件分母与边界","可核对字段"),[
        ("客户覆盖","有交易或服务的OEM，不等到期设备","客户ID和当期活跃"),
        ("新机份额","同地域功率、完成采购的设备","OEM终验台数、采购明细"),
        ("续购","本期重选且可下单的同机型","选择、供应商变更、净价"),
        ("附着","同一订单有控制和头的验收批次","订单头、控制料号与服务")],
        "../deep-research-batch-1/external-evidence.csv","分母不足的市场数字留在取证表。")
    ipo=rows(PRIOR/"pre-ipo.csv")
    after={str(r["期间"]):{q["原行"]:q["原披露值"] for q in ipo if q["期间"]==r["期间"]} for r in ipo}
    tab("ipo","招股书年报原量",("年度","收入·百万元","营业利润·百万元","CFO·百万元"),
        [(i,m(e["营业总收入"]),m(e["营业利润"]),m(e["经营活动产生的现金流量净额"])) for i,e in sorted(after.items())],
        "../deep-research-batch-1/pre-ipo.csv","招股书 p249、p250；2018与2019年报比较列相勾稽。")
    b("history","经营规模与现金的拐点（百万元）",[x["period"][:4] for x in years],
      ("合并收入","核心EBIT","CFO−购建"),
      [[float(v[k])/1e6 for k in ("revenue","core_ebit","cfo_less_capex")] for v in years],
      "../deep-research-batch-1/financial-bridge.csv","集团合并现列；历史成本重分类影响毛利、同额销售费用。",lambda x:f"{x:,.0f}")
    y22=next(x for x in years if x["period"]=="2022-FY")
    y21=next(x for x in years if x["period"]=="2021-FY")
    tab("shock22","2022年压力的两条线",("合并指标","2021·百万元","2022·百万元","变化·百万元"),
      [(label,m(y21[k]),m(y22[k]),m(float(y22[k])-float(y21[k]))) for label,k in
       [("收入","revenue"),("核心EBIT","core_ebit"),("报表CFO","cfo"),("现金购建","capex"),("CFO−购建","cfo_less_capex")]],
      "data/independent-audit.json","2022年报p98、p102–103及p107独立抽核。")
    b("turns","出货增速分化（套／件当量）",["2024","2025"],("控制系统","智能硬件"),
        [[float(x["control_units"]),float(x["hardware_units"])] for x in rows(CASE/"volume-and-stock.csv")],
        "../volume-and-stock.csv","同名范围有随动集成断点，硬件包含配套及单卖。",lambda x:f"{x:,.0f}")
    tab("recent","年内累计与单季闭合",("指标","2025Q3·百万元","2026Q3·百万元","2026前三季·百万元"),
        [(label,m(qtr[k]["q3_25"]),m(qtr[k]["q3_26"]),m(qtr[k]["ytd26"])) for label,k in [
          ("收入","revenue"),("核心EBIT","core_ebit"),("报告营业利润","reported_ebit"),("CFO−购建","cfo_less_capex")]],
         "data/recent-income-bridge.csv","本期和比较均以三季累计减同年上半年。")
    groups=rows(OUT/"group-restatement.csv")
    tab("group","按解决方案重组收入（百万元）",("分组","2023桥接下限","2023闭合采用","2023桥接上限","2024","2025"),
      [(r["group"],*(m(r[f]) for f in ["revenue23_lower","revenue23_adopted","revenue23_upper","revenue24","revenue25"])) for r in groups],
      "data/group-restatement.csv","2023三列保留到0.001百万元见CSV。采用值与主营精确闭合；比较成本直接取重列表。")
    op=read_json(CASE/"operating-summary.json")
    tab("volume","2024→2025主营量与组价桥",("项目","增加·百万元","下一次核对"),
        [("主营收入增量",ins(op["volume_contribution_m"]+op["realisation_mix_contribution_m"]),"四组收入和其他业务"),
         ("控制当量所示量",ins(op["volume_contribution_m"]),"同订单设备、控件和替换"),
         ("组均实现与结构",ins(op["realisation_mix_contribution_m"]),"同机型净价、退返、配套分布")],
        "../operating-summary.json","组均额叠加组合影响，保留参数代理边界。")
    g25=[r for r in gm if r["period"]=="24→25"]
    g24=[r for r in gm if r["period"]=="23→24"]
    tab("gross","主营毛利率中点贡献（百分点）",("分组","23→24权重","23→24组内","24→25权重","24→25组内"),
        [(x["group"],f"{float(x['margin_mix_pp']):+.3f}",f"{float(x['margin_inside_pp']):+.3f}",
          f"{float(y['margin_mix_pp']):+.3f}",f"{float(y['margin_inside_pp']):+.3f}") for x,y in zip(g24,g25)]
        +[("合计",*(f"{sum(float(r[k]) for r in g):+.3f}" for g in (g24,g25) for k in ("margin_mix_pp","margin_inside_pp")))],
        "data/gross-contribution.csv","每段按两期中点，交叉项均摊；含2023则组收入为区间估计。")
    tab("costs","材料、人工与制造的比较桥",("性质","2023重列·百万元","2024原列","2024次年比较","2025"),
        [(r["name"],*(m(r[k]) if r[k] else "—" for k in ("year23_comparison","year24_original","year24_comparison","year25")))
         for r in rows(OUT/"cost-attribution.csv")],"data/cost-attribution.csv","2025余项不按质保分配；2024材料与制造比较列等额变动。")
    tab("quarterprofit","2026Q3带来的利润变化",("核心桥（百万元）","2025Q3","2026Q3","绝对变动"),
        [(label,*(m(qtr[k][x]) for x in ("q3_25","q3_26","q3_change"))) for label,k in [
        ("收入","revenue"),("成本","cost"),("毛利","gross"),("核心营业利润","core_ebit"),("其他收益","其他收益"),
        ("报告营业利润","reported_ebit"),("归母","parent_profit")]],
        "data/recent-income-bridge.csv","其他收益来自独立累计差分；扣非归母3.0212亿元是季报首页披露。")
    drv("normalization","从销售到归母的口径链",[
        ("核心EBIT","营业收入减成本及四项经营费"),
        ("报表营业利润","扣原符号财务费，加其他收益、投资公允、减值、处置"),
        ("合并净利","计营业外收支，扣报表所得税"),
        ("归母","从合并净利扣少数损益"),
        ("扣非归母","发行人按法定非经常项目调整")],
        "../analysis-ebit-bridge.csv","利息收入是财务费用子项，调整只进一次。")
    tab("cashhistory","历史现金回收的三种尺度",("年度","CFO·百万元","CFO−购建","经营FCFF代理","差额"),
        [(r["year"],*(ins(r[k]) for k in ("cfo_m","cfo_less_capex_m","fcff_proxy_m","bridge_residue_m"))) for r in cash],
        "data/cash-history.csv","历史代理缺长期租赁及完整其他营运资本，差额保留。")
    tab("cfostream","前三季现金流同比贡献",("现金流量单项","2025·百万元","2026·百万元","对CFO变化"),
        [(r["item"],*(m(r[k]) for k in ("ytd25","ytd26","cfo_effect"))) for r in rows(OUT/"cfo-change.csv")],
        "data/cfo-change.csv","现金流量正负为净流影响；净增58.8023百万元。")
    bal=rows(PRIOR/"working-capital.csv")
    rec_wc=[r for r in bal if r["column"]=="期末" and r["report"] in ("2025-YTD9","2026-H1","2026-YTD9")]
    tab("working","贸易营运资本分项",("期末","应收·百万元","存货","应付","净贸易占款"),
        [(r["report"],*(m(r[k]) for k in ("ar","inventory","ap","trade_working_subset"))) for r in rec_wc],
        "data/trade-days.csv","占款仅包含贸易子项；表头为期末，天数用平均余额另算。")
    tab("roic","窄口径历史资本与回报",("年度","平均经营资本·百万元","NOPAT代理","平均ROIC","增量ROIC"),
        [(r["year"],ins(r["avg_capital_m"]) if r["avg_capital_m"] else "—",ins(r["nopat_m"]),
          pct(r["roic_proxy"]) if r["roic_proxy"] else "—",pct(r["incremental_roic_proxy"]) if r["incremental_roic_proxy"] else "—")
         for r in rows(OUT/"capital-returns.csv")],
        "data/capital-returns.csv","研发费用化、小资本分母等限制跨业务比较。")
    tab("bundle","50%硬件毛利时的首批现金敏感性",("库存／应收天","首批占款·元","服务5元后现金","售后上限"),
        [(r["inventory_days"]+"／"+r["ar_days"],*(ins(r[k]) for k in (
            "opening_trade_cash_cost","first_cohort_cash","maximum_service_for_positive_cash")))
         for r in rows(OUT/"bundle-cash-thresholds.csv") if float(r["gross_margin"])==.50],
        "data/bundle-cash-thresholds.csv","每100元增量净收入的条件试算；首批建立资本。")
    drv("pipeline","项目进入基准要逐层通过",[
        ("需求","可服务工厂、可适配设备数及规格"),
        ("适配","试样合格率、验证周期及成本"),
        ("订单","净价、批次和取消条款"),
        ("验收","交付、工位利用与保修"),
        ("收款·回报","按账期到账，分摊并回收购建")],
        "data/project-conditional-scale.csv","设备测试与公司公告是证据层，不是订单已转化。")
    fund=[r for r in rows(PRIOR/"project-stages.csv") if r["项目"]=="智能切割头扩产"]
    tab("funding","切割头支出范围（万元）",("取数范围","原项目投资","募集承诺","已投入募集资金","物理页"),
        [(r["阶段"],r["原项目总投资万元"],r["募集资金承诺或调减万元"],r["募集资金实际投入万元"],r["PDF物理页"])
         for r in fund],"../deep-research-batch-1/project-stages.csv","批次表原项目预算重复列示；聚合承诺和实际，不能把原投资加两次。")
    projects=rows(OUT/"project-conditional-scale.csv")
    tab("projects","条件规模与首批现金区间",("项目","条件台数／工位","条件营收·百万元","剔专用购建首批现金·百万元"),
        [(z["project"],z["condition_units"]+"–"+y["condition_units"],
          m(z["condition_revenue_yuan"])+"–"+m(y["condition_revenue_yuan"]),
          m(z["first_cohort_cash_before_special_capex"])+"–"+m(y["first_cohort_cash_before_special_capex"]))
         for z,y in zip(projects[::2],projects[1::2])],
         "data/project-conditional-scale.csv","均为明确情景尺度。前三个新项目增量不纳入三条主预测。")
    tab("followup","路演期后答复及下一步",("议题","可回读管理层答复","需要的披露"),[
        ("高功率","收入和市场地位表述，未给分母","按功率段、地区及OEM装机"),
        ("配套","丰富方案，未给实际附着及上限","同订单硬件附着与净价"),
        ("船舶焊接","设备厂合作、方案方向","订单有效期、验收与收款"),
        ("备货","前置安全库存与供应韧性","积压年龄、订单覆盖及扣退货现金")],
        "data/post-window.csv","2026-11-20会后转录，隔离于含权估值窗。")
    drv("drivers","每台设备只经过一个控制订单池",[
        ("新机","候选量 × 技术适配 × 赢单份额"),
        ("存量","过往控制曝险 ÷ 周期 × 同机型留存"),
        ("收入","控制量×组价＋硬件和残余，配套以验收为门"),
        ("现金","组毛利、费用、税，再扣周转及购建")],
        "assumptions.json","系统销量锚可核，池规模和客户转化为条件。")
    tab("cohorts","基准前四年控制与硬件量",("年度","新机当量","换机当量","配套接受","单卖硬件","控制组价·元"),
        [(r["year"],*(f"{r[k]:,.0f}" for k in ("control_new","control_replacements","accepted_attached","head_single","net_price_control_cny")))
         for r in base["path"][1:5]],"data/forecast.csv","预测；接受含前期未验收且本期接回的条件数量。")
    tab("q4","2026Q4预测与前三季保持隔离",("路径","Q4控制量","组价·元","Q4收入·百万元","Q4核心EBIT","估值桩段折现"),
        [(names[k],f"{x['q4']['control_units']:,.0f}",f"{x['q4']['control_price_cny']:,.0f}",
          ins(x["q4"]["revenue"]),ins(x["q4"]["core_ebit"]),ins(x["path"][0]["pv"])) for k,x in cases.items()],
        "data/model.json","Q4量价为条件；桩段现金折现使用11月12日至12月31日。")
    tab("forecast_short","三情景逐年现金（百万元）",("期间","压力收入","压力FCFF","基准收入","基准FCFF","改善收入","改善FCFF"),
        [(label,*[ins(x["path"][i][k]) for x in cases.values() for k in ("revenue","fcff")])
         for i,label in enumerate([2026,2027,2028,2029,2030])]+
        [(2035,*[ins(x["path"][-1][k]) for x in cases.values() for k in ("revenue","fcff")]),
         (2036,*[ins(x["stable_2036"][k]) for x in cases.values() for k in ("revenue","fcff")])],
        "data/forecast.csv","2026展示全年，估值只折现桩段。2036取稳定期。中间年及各费用在CSV。")
    tab("holdouts","封存原财年后的留出误差",("目标年","截止日","预测百万元","实际百万元","误差"),
        [(r["target"],r["cutoff"],m(r["predicted_yuan"]),m(r["actual_yuan"]),f"{float(r['error_pct']):+.2f}%")
         for r in rows(OUT/"annual-holdouts.csv") if r["method"]=="三份年报增长中位数"],
        "data/annual-holdouts.csv","同时保留原规模持平基线，所有目标实际均来自次年公告。")
    broker=[r for r in rows(PRIOR/"forecast-holdout.csv") if r["metric"] in ("集团营业收入","三维解决方案")]
    tab("brokers","同年集团与分业务外部留出",("预测口径","预计·百万元","实际·百万元","误差"),
        [(r["firm"]+" "+r["metric"],m(r["predicted_yuan"]),m(r["actual_yuan"]),f"{float(r['error_pct']):+.2f}%")
         for r in broker],"../deep-research-batch-1/forecast-holdout.csv","华创三维成本原印及单位诊断见同源补表。")
    tab("valuechange","从冻结估值到新稿（元/股）",("桥项","边际价差","过桥价"),
        [(r["item"],("起点" if i==0 else f"{float(r['share_delta']):+.3f}"),f"{float(r['price_after']):.3f}")
         for i,r in enumerate(rows(OUT/"value-bridge.csv"))],
        "data/value-bridge.csv","沿用同日的WACC、合并证券权利及权益桥；完整精度留在CSV。")
    terminal=rows(OUT/"terminal-sensitivity.csv")
    tab("wacc","同一长期增长下的资本纪律对照",("WACC","g","新增ROIC","价值·元","终值占EV"),
        [(pct(r["wacc"]),pct(r["g"]),pct(r["incremental_roic"]),ins(r["price"]),pct(r["terminal_share"]))
         for r in terminal if float(r["g"])==.023 and (float(r["incremental_roic"])==.235 or
            abs(float(r["wacc"])-rec["wacc"])<1e-7)],"data/terminal-sensitivity.csv","联合变化层的完整网格可下载。")
    anames=["货币资金","交易性金融资产","经营现金保留","回购通知／额外缓冲","金融负债","融资类租赁",
            "少数归属","单列项目负债","非现金等价物差额"]
    tab("equity","企业价值到普通股权益",("权益项","正负贡献·百万元","每股·元"),
        [(n,(f"{float(r['delta_m']):.4f}" if r["item"]=="cash_not_equivalent" else ins(r["delta_m"])),(f"{float(r['delta_per_share']):.6f}" if r["item"]=="cash_not_equivalent" else ins(r["delta_per_share"]))) for n,r in zip(anames,rows(OUT/"equity-bridge.csv"))]
        +[("净权益桥",ins(rec["cash_bridge"]),ins(rec["cash_bridge"]/(rec["shares"]/1e6)))],
        "data/equity-bridge.csv","证券桥读原三季报及阶段17；冻结金融资产使用权为代理。")
    put("contour","96.20 元等值线｜纵轴稳定核心 EBIT 率，横轴 2027 控制量增速",
        contour_graph(rows(OUT/"price-contours.csv")),"data/price-contours.csv","点为等价根，无解点和两侧界价留在CSV。")
    tab("relative","自身不同估值日的同口径 P/E",("市场日","原价·元","股数·百万","滚动归母·百万元","P/E"),
        [(r["date"],ins(r["price_unadjusted"]),ins(r["shares_m"]),ins(r["trailing_parent_profit_m"]),ins(r["pe"]))
         for r in rows(OUT/"own-relative.csv")],"data/own-relative.csv","只用该日可得分母，历史报价采用原研报时点。")
    tab("switches","正反两种经营下的重算（元/股）",("方向","27控制量增速","库存天数变化","稳定核心率","每股价值","较基准"),
        [(k,pct(r["growth_2027"]),r["inventory_days_change"],pct(r["stable_margin"]),ins(r["price"]),f"{r['change']:+.2f}")
         for k,r in zip(("局部上修","局部下修"),(rec["major_changes"]["up"],rec["major_changes"]["down"]))],
        "data/model.json","阈值需要利润率和现金验证，局部上修仍低于市场价。")
    tab("actions","团队裁定与参数方向",("待字段","核对入口／负责人","参数及方向"),[
        ("同机型续购、报价与工时","OEM配对；产业研究","净价与取得份额↑／竞价相反"),
        ("合格订单附着、库龄及售后","订单＋三表；财务复核","毛利兑现、应收与库存↓／负面反转"),
        ("项目实付、验收及已回款","合同／专户／项目经理","够门槛方加FCFF与资本"),
        ("限制资金及未归属激励","募资专项＋登记；估值复核","可用资产与证券分母"),
        ("路演与券商单位原稿","交易所与券商原PDF；证据复核","不进冻结窗；修订外部诊断")],
        "data/claims-and-figures.csv","团队审阅邀请与投资决定另留正式记录。")
    return a


def format_inline(string):
    esc = escape(string)
    esc = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",r'<a href="\2">\1</a>',esc)
    return re.sub(r"\*\*(.*?)\*\*",r"<strong>\1</strong>",esc)


def assemble():
    model=read_json(OUT/"model.json")
    audit=read_json(OUT/"independent-audit.json")
    grid=rows(OUT/"price-contours.csv")
    rec,base=model["receipt"],model["scenarios"]["base"]
    rr=[next(r for r in grid if float(r["control_new_shock_of_prior_units"])==.06 and
                int(r["inventory_days_shift"])==k) for k in (-25,25)]
    substitutions={"base":ins(base["price"]),"change":ins(base["price"]-rec["frozen_baseline"]),
        "base_gap":f"{base['price']/rec['market']-1:+.2%}","tv_share":pct(base["terminal_share"]),
        "root_growth":pct(rr[0]["computed_2027_volume_growth"]),"root_lean":pct(rr[0]["stable_core_ebit_margin"]),
        "root_heavy":pct(rr[1]["stable_core_ebit_margin"]),"root_both":[r["reprice"] for r in rr],
        "q4_revenue":ins(base["q4"]["revenue"]/100),"q4_core":ins(base["q4"]["core_ebit"]/100),
        "vol27":f"{base['path'][1]['control_units']:,.0f}","vol30":f"{base['path'][4]['control_units']:,.0f}",
        "exvalue":f"{base['price']-.582:.3f}","grid_count":audit["price_root_count"],
        "grid_missing":audit["no_root_count"],"grid_residual":f'{audit["maximum_grid_residual"]:.2e}',
        "up":ins(rec["major_changes"]["up"]["price"]),"down":ins(rec["major_changes"]["down"]["price"]),
        "raw_count":audit["raw_count"],"audit_residual":f'{max(abs(r["residual"]) for r in audit["comparison"]):.2e}'}
    pages=[]
    first_pages=[]
    for i,file in enumerate(sorted((HERE/"chapters").glob("*.md"))):
        first_pages.append(len(pages)+1)
        pages.extend((i, p.strip()) for p in file.read_text(encoding="utf-8").split(":::page"))
    assert len(pages)==40
    exhibits=build_tables(model,audit,first_pages)
    css=(HERE/"review.css").read_text(encoding="utf-8")
    html=[f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>柏楚电子 · 证券投资分析审阅稿</title><style>{css}</style><body>',
          '<nav class="reader-nav"><strong>柏楚电子 · 研究审阅</strong><span><a href="#page-2">目录</a>　<a href="review.pdf">PDF</a>　<a href="README.md">复算与证据</a></span></nav><main>']
    markdown=[]
    used=[]
    for p,(chapter,text) in enumerate(pages,1):
        def substitute(match):
            return str(substitutions[match[1]])
        start,*paragraphs=re.split(r"\n\s*\n",re.sub(r"\{\{(\w+)\}\}",substitute,text))
        title=start.splitlines()[0].removeprefix("## ")
        if len(start.splitlines())>1:
            paragraphs.insert(0,"\n".join(start.splitlines()[1:]))
        html.append(f'<section class="sheet{" hero" if p==1 else ""}" id="page-{p}"><div class="mast"><span>柏楚电子 · 688188.SH</span><span>{CHAPTERS[chapter]}　/　团队审阅</span></div><div class="sheet-content"><h1>{escape(title)}</h1>')
        markdown.append("## "+title)
        for paragraph in paragraphs:
            key=re.fullmatch(r"\[\[(\w+)\]\]",paragraph.strip())
            if key:
                name=key[1]
                titlex,(graph,matrix),source,desc=exhibits[name]
                label=f"图表 {len(used)+1:02d}"
                html.append(f'<figure id="figure-{name}"><h2>{label}　{escape(titlex)}</h2>{graph}<figcaption>{escape(desc)} <a href="{escape(source,quote=True)}">同源底表／证据</a></figcaption></figure>')
                markdown.append(f"**{label}　{titlex}**\n\n{matrix}\n\n{desc} [同源底表／证据]({source})")
                used.append(dict(figure=label,chapter=CHAPTERS[chapter],page=p,key=name,claim=titlex,summary=desc,
                                 file=source,report_anchor=f"review.html#figure-{name}"))
            else:
                html.append("<p>"+format_inline(paragraph).replace("\n","<br>")+"</p>")
                markdown.append(paragraph)
        html.append(f'</div><footer class="foot"><span>同日估值 2026-11-12　·　截至 2026-11-23</span><span>{p:02d} / 40</span></footer></section>')
    html.append("</main></body></html>")
    from forecast import write_csv
    write_csv("claims-and-figures.csv",used)
    (HERE/"review.html").write_text("\n".join(html)+"\n",encoding="utf-8",newline="\n")
    (HERE/"review.md").write_text("# 柏楚电子证券投资分析审阅稿\n\n"+"\n\n".join(markdown)+"\n",encoding="utf-8",newline="\n")
    print(f"{len(pages)} pages, {len(used)} figures, {len(re.findall(r'[\u4e00-\u9fff]', ''.join(s for _,s in pages)))} Chinese body-source characters")


if __name__=="__main__":
    assemble()
