"""Rebuild the first-round delivery from the seven pinned annual reports."""
import argparse
from collections import Counter
from decimal import Decimal as D
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

from extract_annual import (
    ARCHIVE, COMPANY, HERE, ISSUER, MDA, PAGES, REPO, SCOPE, STATEMENTS,
    TOTALS, WORKSPACE, display, number, report_data, write_csv,
)

BS, IS, CF = STATEMENTS
REV = "营业收入和营业成本附注"
AR = "应收账款附注·按坏账计提方法分类披露"
AGE = "应收账款附注·按账龄披露"
INV = "存货附注·存货分类"
CASH_NOTE = "现金流量表补充资料"
COST = MDA+"成本分析表·分产品情况"
COST_INDUSTRY = MDA+"成本分析表·分行业情况"
VOL = MDA+"产销量情况分析表"
MONEY = ("营业收入","营业成本")
DIM = {d:MDA+f"主营业务分{d}情况" for d in ("产品","地区","销售模式")}
METRICS = {
    "营业收入": (IS,r"^(一、)?营业总收入$"),
    "营业成本": (IS,r"^(其中[:：])?营业成本$"),
    "销售费用": (IS,r"^销售费用$"),
    "管理费用": (IS,r"^管理费用$"),
    "研发费用": (IS,r"^研发费用$"),
    "财务费用": (IS,r"^财务费用$"),
    "税金及附加": (IS,r"^税金及附加$"),
    "营业利润": (IS,r"^三、营业利润"),
    "净利润": (IS,r"^五、净利润"),
    "利润总额": (IS,r"^四、利润总额"),
    "所得税费用": (IS,r"^(减[:：])?所得税费用$"),
    "归母净利润": (IS,r"归属[于与]?母公司(?:股东|所有者)的?净利润"),
    "资产总计": (BS,r"^资产总计$"),
    "负债合计": (BS,r"^负债合计$"),
    "所有者权益合计": (BS,r"^所有者权益.*合计$"),
    "应收账款净额": (BS,r"^应收账款$"),
    "存货净额": (BS,r"^存货$"),
    "经营现金流净额": (CF,r"^经营活动产生的现金流量净额$"),
    "购建长期资产支付的现金": (CF,r"^购建固定资产、无形资产和其他长期资产支付的现金$"),
    "销售商品、提供劳务收到的现金": (CF,r"^销售商品、提供劳务收到的现金$"),
    "期初现金及现金等价物余额": (CF,r"期初现金及现金等价物余额$"),
    "现金及现金等价物净增加额": (CF,r"现金及现金等价物净增加额$"),
    "期末现金及现金等价物余额": (CF,r"期末现金及现金等价物余额$"),
}
# Separately stated FY2023 retrospective cost reclassification.
RESTATED={(2023,IS,"营业成本"),(2023,IS,"销售费用"),
          (2023,"销售费用附注","合计"),(2023,REV,"主营业务·成本"),(2023,REV,"合计·成本")}

def v(r):
    return number(r["标准值"]) if r else None

def ident(r):
    return r["单元ID"] if r else ""

def locator(r):
    if not r:
        return ""
    return f"{r['报告年度']}年报 p{r['PDF物理页']} {r['表名']}｜{r['原行']}｜{r['原列']}"

def metric_lookup(cells):
    buckets={}
    for r in cells:
        key=(r["报告年度"],r["表名"],r["原行"],r["原列"])
        if key in buckets:
            assert v(r)==v(buckets[key]) or v(r) is None or v(buckets[key]) is None,key
            if v(r) is None:
                continue
        buckets[key]=r
    return buckets

def first(rows,pattern):
    match=[r for r in rows if re.search(pattern,r["原行"])]
    with_numbers=[r for r in match if v(r) is not None]
    assert len(with_numbers)<=1,[(r["原行"],r["原列"],v(r)) for r in with_numbers]
    return (with_numbers or match or [None])[0]

def ratio(n,d):
    return None if n is None or d is None or d<=0 else 100*n/d

def growth(n,d):
    return None if n is None or d is None or d<=0 else 100*(n-d)/d

def gross(revenue,cost):
    return None if revenue is None or cost is None else ratio(revenue-cost,revenue)

def pct(x):
    return "" if x is None else str(x.quantize(D("0.000001")))

def fingerprint(f):
    return sha256(f.read_bytes()).hexdigest()

def fact_audit(cells,idx):
    by_source={r["来源编号"]:r for r in idx}
    sys.path[:0]=[str(REPO/"shared/runtime"),str(REPO/"app")]
    from companybench import core
    from source_compat import enable
    enable(core,REPO)
    local=core.ReviewStore(COMPANY)
    facts=local.facts()
    local_count=len(facts)
    archive_company=ARCHIVE/"companies/688188_柏楚电子"
    archive_count=None
    scope=COMPANY
    if all((archive_company/f).is_file() and fingerprint(archive_company/f)==fingerprint(COMPANY/f)
           for f in ("evidence/ledger.json","sources/manifest.json")):
        archive=core.ReviewStore(archive_company)
        archive_facts=archive.facts()
        archive_count=len(archive_facts)
        # The archived checkout contains complete dependencies for the same ledger.
        if {f["id"] for f in facts}<={f["id"] for f in archive_facts}:
            facts=archive_facts
            scope=archive_company

    spec=importlib.util.spec_from_file_location("investment_workspace_review_store",WORKSPACE/"scripts/review_store.py")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.path.insert(0,str(WORKSPACE/"scripts"))
    store=mod.ReviewStore(WORKSPACE)
    workspace_facts=store.facts()
    change_facts=store.change_facts()
    changes=[c for c in change_facts if re.search("688188|柏楚",json.dumps(c,ensure_ascii=False))]
    evidence=[]
    related={}
    for fact in sorted(facts,key=lambda f:f["id"]):
        if not fact["sources"] or not all(x["source_id"] in by_source for x in fact["sources"]):
            continue
        original=[]
        for src in fact["sources"]:
            meta=by_source[src["source_id"]]
            file=scope/meta["公司目录相对路径"]
            assert fingerprint(file)==meta["SHA256"]==fingerprint(Path(meta["本地原件"])),src
            original.append(f"{src['source_id']}｜{meta['SHA256']}｜{src['location']}")
        ids=[]
        for r in cells:
            if r["表名"] not in STATEMENTS or v(r)!=number(str(fact.get("value",""))):
                continue
            rpage=r["PDF物理页"]
            if not any(x["source_id"]==r["来源编号"] for x in fact["sources"]):
                if not fact["id"].startswith("B07-A") or r["报告年度"]!=r["数据年度"] or r["数据年度"]!=2024:
                    continue
            if fact["id"].startswith("B07-A"):
                no=int(fact["id"][-2:])
                if r["数据年度"]!=(2025 if no%2 else 2024):
                    continue
                pattern=[None,METRICS["营业收入"],METRICS["归母净利润"],METRICS["经营现金流净额"]][(no+1)//2]
                if r["表名"]!=pattern[0] or not re.search(pattern[1],r["原行"]):
                    continue
            elif not any(x["source_id"]==r["来源编号"] and f"第{rpage}页" in x["location"] for x in fact["sources"]):
                continue
            ids.append(r["单元ID"])
            related.setdefault(r["单元ID"],[]).append(fact["id"])
        assert ids,fact["id"]
        evidence.append(dict(Fact编号=fact["id"],既有核验值=fact["value"],核验状态=fact["effective_state"],
           既有核验人=fact.get("verifier"),原Fact位置与绑定="；".join(original),交叉对应底表单元="；".join(ids),
           对应关系="同一指标与期间对读，原Fact仍绑定原位置",审核账本目录=str(scope),
           绑定标识=fact.get("binding"),确认事件=fact.get("confirmation_event")))
    for r in cells:
        r["既有Fact对照"]="；".join(related.get(r["单元ID"],[]))
    return evidence,dict(工作空间原披露有效数=len(workspace_facts),工作空间变化有效数=len(change_facts),
      本公司变化Fact=len(changes),协作公司目录有效Fact=local_count,同账本证据归档有效Fact=archive_count,
      纳入本轮年报范围有效Fact=len(evidence))

def static_gaps():
    return [
      (2019,"销售模式","直销/经销分栏金额","未列金额表","2019年报 p21–22 分行业、分产品、分地区及后续产销量","各渠道金额与勾稽留缺"),
      (2020,"销售模式","直销/经销分栏金额","未列金额表","2020年报 p24–25 分行业、分产品、分地区及后续产销量","各渠道金额与勾稽留缺"),
      ("2021–2025","销售模式","单列经销收入及成本","直销表无经销行","各年报分销售模式表","用直销与表合计勾稽，单列经销原值留缺"),
      ("2019–2025","地区","独立境内/境外收入及成本","管理层分地区表无境外行","各年报管理层分地区表","保留地区原分类，归入其他的金额不可反推"),
      ("2019–2025","地区／方案／渠道","地区×方案×销售模式交叉矩阵","分向披露","各年报管理层分产品、地区、销售模式表","各维度分别勾稽"),
      ("2019–2023","方案","旧产品对新方案的逐项收入/成本分配","未披露跨维矩阵","2024年报 p25–27 分类说明与分产品成本比较","旧产品、新方案分轨；2023新方案成本见2024比较列"),
      (2023,"方案","2023年同口径解决方案分项绝对收入","原表仅给2024各组同比","2024年报 p25–27","金额及重算同比留缺，年报同比照录"),
      ("2022→2023","地区","东北及其他的可比前期绝对数","跨年分组变化","2022年报 p25–26；2023年报 p24","2022表无东北行；不反推基数"),
      (2023,"地区","2023年各区质保重分类后的成本","未给同口径绝对数","2024年报 p25–26、153","地区成本同比及毛利率同比仅保留披露值"),
      ("2019–2022","产销存","控制系统与智能硬件同2024口径的分组绝对数","未找到同口径原列","各年报产销量表；2024年报 p26","按旧产品字段留存"),
      (2022,"产销存","切割头独立生产量、销售量、库存量","2022表未列，后报只披露增长","2022年报 p26；2023年报 p25","独立绝对值留缺"),
      (2023,"产销存","控制系统与智能硬件同2024口径的分组绝对数","后报只列同比","2023年报 p25；2024年报 p26","旧分组不代新分类原值"),
      ("2024–2025","产销存","分平面/管材/三维的产销存","只有控制系统及智能硬件分组","2024年报 p26；2025年报 p29","保持两套分组"),
      ("2019–2022","应收账款","账龄表期初列","账龄表只列期末","2019 p130；2020 p140–141；2021 p151；2022 p142","优先用上年原表期末核对，期初披露列留缺"),
      ("2019、2020、2022、2023","合并范围","剔除范围变动后的固定范围同比","范围变化","见年报索引合并范围变更附注","同报两列可计算列报合并同比，固定范围同比留缺"),
      ("2019–2025","产销存","数量增减中的其他变动细项","未有逐组调节表","各年报产销量表","期初＋生产－销售－期末仅为差额检查"),
    ]

def method_bridge():
    return [
      ("分产品","2019–2022","随动系统／板卡系统／总线系统／其他","产品列原样保留","2019 p21；2020 p24；2021 p25；2022 p25"),
      ("分产品","2022→2023","其他→切割头、其他；板卡／总线比较成本也重分","使用后报披露的分项比较成本。相关前期收入绝对数留缺。随动成本可核；旧新剩余项不做逐行跨年直连","2022 p25；2023 p24、26"),
      ("分方案","2023→2024","旧随动、板卡、总线、切割头及其他→平面、管材、三维、其他","旧标签按产品设备维度，新标签按应用场景与组合。无逐项映射矩阵，只桥接主营合计与新场景比较成本","2023 p6、12、24；2024 p13–16、25–27"),
      ("分方案","2024→2025","平面解决方案／管材解决方案／三维解决方案／其他","按同名场景复算；成本用解决方案合计小计，成本性质另比","2024 p25、27；2025 p27–30"),
      ("分地区","2020→2021","中南→华中和华南","原标签分别保留；不在缺少地区明细时做等价映射","2020 p24；2021 p25"),
      ("分地区","2022→2023","2022无独立东北行；2023单列东北","其他和东北的精确可比基数留缺。公司披露同比原样保留","2022 p25–26；2023 p24"),
      ("分销售模式","2019–2025","2019–2020无销售模式金额表；2021起列直销","按适用总额分别勾稽；年报无独立经销行则留缺","2019 p21–22；2020 p24；2021 p25–26；2022 p26；2023 p25；2024 p26；2025 p28"),
      ("收入覆盖","2021→2022","管理层分项合并营业总额→主营业务","2019–2021分项按合并总额；2022–2025按附注主营业务；总额与主营分别保存","2021 p25、182；2022 p25–26、174"),
      ("会计政策","2023→2024","保证类质保费由销售费用转入营业成本","按2024年报上期列比较2024；各年原披露值供留档","2023 p105–106、184–185；2024 p112、153、205–207"),
      ("成本性质","2024→2025","平面组原材料与制造费用比较列相向调整","分项看2025比较列，报告原值和差额并列；算术守恒不给会计原因","2024 p27；2025 p29–30"),
      ("产销存","2023→2024","随动／板卡／总线／切割头→控制系统／智能硬件","新旧实物组保留；读取新组披露同比，分组数量无法从旧产品精确归并","2023 p25；2024 p26"),
    ]

def calculate(cells):
    ix=metric_lookup(cells)
    file_assets={}
    for r in cells:
        file_assets.setdefault((r["报告年度"],r["表名"],r["列角色"]),[]).append(r)
    def exact(y,t,row,col):
        return ix.get((y,t,row,col))
    def pick(y,t,pattern,role="本期"):
        return first(file_assets.get((y,t,role),[]),pattern)
    def rnote(y,row,c,prior=False):
        return exact(y,REV,row,("上期发生额·" if prior else "本期发生额·")+c)
    def selected(y,entry,role="本期"):
        return pick(y,*METRICS[entry],role)
    def byproduct(y,dim,row,col):
        return exact(y,DIM[dim],row,col)

    bridges=[]
    statistics=[]
    checks=[]
    gaps=[dict(年度=y,维度=d,缺项=x,状态=s,原表范围=p,处理=w) for y,d,x,s,p,w in static_gaps()]

    def bridge(y,s,label,orig,comp,adopt,rule,kind="前期比较列"):
        bridges.append(dict(数据年度=y,类别=s,项目=label,原列=locator(orig),原值=display(v(orig)),
          原列状态=orig["单元状态"] if orig else "未获原列",原单元=ident(orig),比较或重述列=locator(comp),
          比较或重述值=display(v(comp)),比较或重述状态=comp["单元状态"] if comp else "未获比较数值列",
          比较单元=ident(comp),比较列类型=kind,采用值=display(v(adopt)),采用单元=ident(adopt),
          比较减原值=display(v(comp)-v(orig)) if v(comp) is not None and v(orig) is not None else "",
          标准单位=next((r["标准单位"] for r in (orig,comp,adopt) if r),""),用途=rule))

    def check(y,s,formula,items,benchmark,tolerance=D("0"),scope="",optional=False):
        observed=[(r,sign) for r,sign in items if v(r) is not None]
        valid=bool(observed) and v(benchmark) is not None and (optional or len(items)==len(observed))
        lhs=sum((v(r)*sign for r,sign in observed),D(0)) if valid else None
        gap=lhs-v(benchmark) if valid else None
        checks.append(dict(年度=y,勾稽项=s,左侧公式=formula,左侧值=display(lhs),原表基准=display(v(benchmark)),
          差额=display(gap),容差=display(tolerance),单位=benchmark["标准单位"] if benchmark else "",
          结果="缺项" if gap is None else "零差额" if gap==0 else "披露精度内" if abs(gap)<=tolerance else "差额待裁定",
          左侧单元="；".join(("+" if sign==1 else "-")+ident(r) for r,sign in items if r),基准单元=ident(benchmark),口径=scope))

    for y in PAGES:
        for name in METRICS:
            original=selected(y,name)
            prior=selected(y,name,"比较")
            assert v(original) is not None,(y,name,locator(original))
            comp=selected(y+1,name,"比较") if y+1 in PAGES else None
            restated=(y,METRICS[name][0],name) in RESTATED
            adopt=comp if restated else original
            if comp:
                rule="最新横截面采用后报明确重列；本年同比保留当年报告比较窗" if restated else "当年原值；后报比较列对照"
                bridge(y,METRICS[name][0],name,original,comp,adopt,rule,"明确重述" if restated else "后报比较列")
            rv=selected(y,"营业收入")
            ratio_names=("销售费用","管理费用","研发费用","财务费用","税金及附加","营业利润","净利润","归母净利润","经营现金流净额","购建长期资产支付的现金")
            own=v(original)
            yoy=growth(own,v(prior))
            statistics.append(dict(年度=y,维度=METRICS[name][0],项目=name,实际原值=display(own),标准单位=original["标准单位"],
                 复算同比_pct=pct(yoy),占适用合计_pct=pct(ratio(own,v(rv))) if name in ratio_names else "",
                 采用横截面值=display(v(adopt)),当年原值单元=ident(original),当年同比基数=display(v(prior)),同比基数单元=ident(prior),
                 采用横截面单元=ident(adopt),占比基准单元=ident(rv) if name in ratio_names else "",
                 比较规则=("当年报告列报合并口径。本年原值÷同份比较列" if yoy is not None else "比较列空白或基数非正，留缺")))
        rv=selected(y,"营业收入")
        cv=selected(y,"营业成本")
        prv,pcv=(selected(y,k,"比较") for k in MONEY)
        gm=gross(v(rv),v(cv))
        pgm=gross(v(prv),v(pcv))
        adjusted_cv=selected(2024,"营业成本","比较") if y==2023 else cv
        statistics.append(dict(年度=y,维度=IS,项目="合并毛利率",原披露口径毛利率_pct=pct(gm),标准单位="%",
             毛利率同比_pp=pct(gm-pgm) if gm is not None and pgm is not None else "",
             采用横截面值=pct(gross(v(rv),v(adjusted_cv))),
             当年原值单元=f"{ident(rv)}；{ident(cv)}",同比基数单元=f"{ident(prv)}；{ident(pcv)}",
             采用横截面单元=f"{ident(rv)}；{ident(adjusted_cv)}",比较规则="（营业收入－营业成本）÷营业收入；同比为百分点差"))

        check(y,"合并净利润","利润总额－所得税费用",
              [(selected(y,"利润总额"),1),(selected(y,"所得税费用"),-1)],selected(y,"净利润"))
        check(y,"合并现金及现金等价物","期初现金及现金等价物余额＋净增加额",
              [(selected(y,"期初现金及现金等价物余额"),1),(selected(y,"现金及现金等价物净增加额"),1)],
              selected(y,"期末现金及现金等价物余额"))
        assets=selected(y,"资产总计")
        check(y,"合并资产负债表平衡","负债合计＋所有者权益合计",
              [(selected(y,k),1) for k in ("负债合计","所有者权益合计")],assets)
        for money,item in zip(MONEY,("收入","成本")):
            overall=selected(y,money)
            check(y,f"年报附注{item}加总","主营业务＋其他业务",
                  [(rnote(y,k,item),1) for k in ("主营业务","其他业务")],rnote(y,"合计",item))
            check(y,f"附注{item}合计核对合并利润表","营业收入和营业成本附注合计",[(rnote(y,"合计",item),1)],overall)
            for k in ("主营业务","其他业务","合计"):
                original=rnote(y,k,item)
                prev=rnote(y,k,item,True)
                comp=rnote(y+1,k,item,True) if y+1 in PAGES else None
                restated=(y,REV,f"{k}·{item}") in RESTATED
                adopt=comp if restated else original
                if comp:
                    bridge(y,REV,k+"·"+item,original,comp,adopt,
                           "横截面采用2024年报重列；本年同比采用当年报告两列" if restated else "采用当年原列",
                           "明确重述" if restated else "后报比较列")
                statistics.append(dict(年度=y,维度=REV,项目=k+"·"+item,实际原值=display(v(original)),标准单位="人民币元",
                  复算同比_pct=pct(growth(v(original),v(prev))),占适用合计_pct=pct(ratio(v(original),v(overall))),
                  采用横截面值=display(v(adopt)),当年原值单元=ident(original),当年同比基数=display(v(prev)),
                  同比基数单元=ident(prev),采用横截面单元=ident(adopt),占比基准单元=ident(overall),
                  比较规则="成本占比用合并营业成本；收入占比用合并营业收入"))
        for expense in ("销售费用","管理费用","研发费用","财务费用"):
            t=expense+"附注"
            ex=exact(y,t,"合计","本期发生额")
            check(y,expense+"附注勾稽","费用附注合计",[(ex,1)],selected(y,expense))
            comp=exact(y+1,t,"合计","上期发生额")
            if comp:
                restated=(y,t,"合计") in RESTATED
                bridge(y,t,"合计",ex,comp,comp if restated else ex,
                       "采用2024年报明确重列" if restated else "采用当年原列","明确重述" if restated else "后报比较列")
        for table,asset in ((AR,"应收账款净额"),(INV,"存货净额")):
            check(y,asset+"附注勾稽","附注账面价值合计",
              [(exact(y,table,"合计","期末·账面价值"),1)],selected(y,asset))
            allowance_col="期末·坏账准备金额" if table==AR else "期末·跌价或履约成本减值准备"
            check(y,asset+"账面净额","附注账面余额－附注减值准备",[(exact(y,table,"合计","期末·账面余额"),1),
               (exact(y,table,"合计",allowance_col),-1)],exact(y,table,"合计","期末·账面价值"))
        check(y,"应收账龄合计与账面余额","按账龄披露合计",
              [(exact(y,AGE,"合计","期末账面余额"),1)],exact(y,AR,"合计","期末·账面余额"))
        check(y,"现金流量表补充资料CFO","间接法经营活动产生的现金流量净额",
             [(exact(y,CASH_NOTE,"经营活动产生的现金流量净额","本期金额"),1)],selected(y,"经营现金流净额"))

        for dim,t in DIM.items():
            rows=file_assets.get((y,t,"本期"),[])
            labels=list(dict.fromkeys(r["原行"] for r in rows))
            total=next((l for l in labels if l in TOTALS),None)
            parts=[l for l in labels if l not in TOTALS]
            for money,item in zip(MONEY,("收入","成本")):
                total_cell=byproduct(y,dim,total,money)
                applicable=selected(y,money) if y<=2021 else rnote(y,"主营业务",item)
                # In 2019 each printed value has at most 50 yuan rounding error.
                unit_tol=D(50) if y==2019 else D(0)
                check(y,dim+"分项"+item,"各分项相加",
                    [(byproduct(y,dim,r,money),1) for r in parts],total_cell,unit_tol*(len(parts)+1),
                    "本维度分项独立对表内合计")
                check(y,dim+"总额"+item,"管理层表列合计",[(total_cell,1)],applicable,unit_tol,
                   "2019–2021合并营业总额；2022–2025主营业务附注")
            for label in labels:
                rev=byproduct(y,dim,label,MONEY[0]); cost=byproduct(y,dim,label,MONEY[1])
                rbase=byproduct(y-1,dim,label,MONEY[0]); cbase=byproduct(y-1,dim,label,MONEY[1])
                if label in TOTALS:
                    prev=next((r["原行"] for r in file_assets.get((y-1,t,"本期"),[]) if r["原行"] in TOTALS),None)
                    rbase=byproduct(y-1,dim,prev,MONEY[0]); cbase=byproduct(y-1,dim,prev,MONEY[1])
                dr=byproduct(y,dim,label,"营业收入同比")
                dc=byproduct(y,dim,label,"营业成本同比")
                dg=byproduct(y,dim,label,"毛利率同比变动")
                scope="同名原行；按各期年报合并范围"
                if y==2021 and dim=="地区" and label=="华中和华南":
                    rbase=cbase=None
                    scope="地区标签变化，绝对比较基数待证"
                if y==2022:
                    # The report explicitly uses the FY2021 main-revenue/cost
                    # aggregate, and the cost analysis gives exact group costs.
                    if label in (*TOTALS,"直销"):
                        rbase,cbase=rnote(2021,"主营业务","收入"),rnote(2021,"主营业务","成本")
                        scope="2022主营分组；2021基数采用2022年报附注上期主营业务列"
                        rbase,cbase=rnote(2022,"主营业务","收入",True),rnote(2022,"主营业务","成本",True)
                    else:
                        rbase=None
                        cbase=exact(y,COST,label+"｜小计","上年同期金额") if dim=="产品" else None
                        scope="2021分项总额→2022主营；只用本年成本表明示可比分组成本"
                if y==2023 and dim=="产品":
                    if label not in (*TOTALS,"随动系统"):
                        rbase=None
                        cbase=exact(y,COST,label+"｜小计","上年同期金额")
                        scope="2023产品拆分及比较成本重分；旧类收入基数留缺"
                mechanical_r=mechanical_c=None
                if y==2023 and dim=="地区" and label in ("其他","东北"):
                    mechanical_r,mechanical_c=rbase,cbase
                    rbase=cbase=None
                    scope="2022地区表无独立东北行；其他的可比绝对基数待证"
                if y==2024:
                    if label in (*TOTALS,"直销"):
                        rbase,cbase=rnote(y,"主营业务","收入",True),rnote(y,"主营业务","成本",True)
                        scope="使用2024年报附注对2023主营列的质保成本重列"
                    elif dim=="产品":
                        rbase=None
                        cbase=exact(y,COST,label+"｜小计","上年同期金额")
                        scope="场景分类重列。比较收入原值留缺，成本取同名方案小计"
                    else:
                        cbase=None
                        scope="分地区成本受质保重述影响，比较金额留缺"
                if y==2025 and dim=="产品":
                    cbase=exact(y,COST,label+"｜小计","上年同期金额") or cbase
                gr,gc=growth(v(rev),v(rbase)),growth(v(cost),v(cbase))
                mg=gross(v(rev),v(cost)); pmg=gross(v(rbase),v(cbase))
                mr=byproduct(y,dim,label,"毛利率")
                applicable=selected(y,MONEY[0]) if y<=2021 else rnote(y,"主营业务","收入")
                statistics.append(dict(年度=y,维度=t,项目=label,实际原值=display(v(rev)),实际成本=display(v(cost)),标准单位="人民币元",
                 复算同比_pct=pct(gr),复算成本同比_pct=pct(gc),占适用合计_pct=pct(ratio(v(rev),v(applicable))),
                 原披露口径毛利率_pct=pct(mg),毛利率同比_pp=pct(mg-pmg) if mg is not None and pmg is not None else "",
                 年报披露同比_pct=display(v(dr)),年报披露成本同比_pct=display(v(dc)),年报披露毛利率_pct=display(v(mr)),
                 年报披露毛利率同比=dg["原字面值"] if dg else "",
                 当年原值单元=ident(rev),当年成本单元=ident(cost),当年同比基数=display(v(rbase)),同比基数单元=ident(rbase),
                 成本同比基数=display(v(cbase)),成本比较基数单元=ident(cbase),占比基准单元=ident(applicable),
                 披露同比单元=f"{ident(dr)}；{ident(dc)}；{ident(dg)}",
                 原列机械变化_pct=pct(growth(v(rev),v(mechanical_r))),原列成本机械变化_pct=pct(growth(v(cost),v(mechanical_c))),
                 旧原列单元=ident(mechanical_r),旧原列成本单元=ident(mechanical_c),比较规则=scope))
                if y in (2022,2023,2024,2025) and cbase is not None and cbase["报告年度"]==y:
                    oldr=byproduct(y-1,dim,label,MONEY[1])
                    if label in TOTALS or label=="直销":
                        oldr=byproduct(y-1,dim,label,MONEY[1]) or byproduct(y-1,dim,"总计",MONEY[1])
                    if y==2024 and dim=="产品" and label not in TOTALS:
                        oldr=None
                    if y==2023 and dim=="产品" and label=="其他":
                        scope+="；旧其他为宽类，新其他为拆分后的分组，差额涉及范围变化"
                    bridge(y-1,t,label+"·成本",oldr,cbase,cbase,scope,
                           "直接披露的比较成本或主营总额")
                if y==2024 and dim=="产品" and label not in TOTALS:
                    bridge(2023,t,label+"·收入",None,None,None,"年报只披露同口径同比；金额留缺","应用场景重列")

        vol_groups=list(dict.fromkeys(r["原行"] for r in file_assets.get((y,VOL,"本期"),[])))
        for group in vol_groups:
            for m in ("生产量","销售量","库存量"):
                now=exact(y,VOL,group,m)
                prev=exact(y-1,VOL,group,m)
                stated=exact(y,VOL,group,m+"同比")
                direct=growth(v(now),v(prev))
                discrepant=direct is not None and v(stated) is not None and abs(direct-v(stated))>D("0.005")
                if discrepant:
                    gaps.append(dict(年度=y,维度=VOL,缺项=f"{group}·{m}可比基数",
                        状态="同名旧值推算与披露同比不符",原表范围=locator(prev)+"；"+locator(stated),
                        处理="并列两种同比，停止同口径复算",单元ID=ident(stated)))
                statistics.append(dict(年度=y,维度=VOL,项目=group+"·"+m,实际原值=display(v(now)),标准单位="套",
                    复算同比_pct=pct(None if discrepant else direct),年报披露同比_pct=display(v(stated)),当年原值单元=ident(now),
                    当年同比基数=display(v(prev)) if not discrepant else "",同比基数单元=ident(prev) if not discrepant else "",
                    原列机械变化_pct=pct(direct) if discrepant else "",旧原列数值=display(v(prev)) if discrepant else "",
                    旧原列单元=ident(prev) if discrepant else "",披露同比单元=ident(stated),
                    比较规则=("同名原列的机械变化与年报同比不同，停止同口径比较" if discrepant else
                               "同名上年原量可核时复算；披露同比独立保留")))
            check(y,group+"实物库存差额","上年期末＋当年生产－当年销售",
                [(exact(y-1,VOL,group,"库存量"),1),(exact(y,VOL,group,"生产量"),1),(exact(y,VOL,group,"销售量"),-1)],
                exact(y,VOL,group,"库存量"),scope="跨报告原列算术；若上年分类基数不同，差额同时含口径差。其他类可能存在组合发运")
        for t in (COST_INDUSTRY,COST):
            for r in file_assets.get((y,t,"本期"),[]):
                if r["原列"]!="本期金额" or y not in (2024,2025):
                    continue
                label=r["原行"]
                as_published=exact(y-1,t,label,"本期金额")
                comp=exact(y,t,label,"上年同期金额")
                if v(comp) is not None and (v(as_published)!=v(comp)):
                    if y==2024 and t==COST:
                        as_published=None
                    bridge(y-1,t,label,as_published,comp,comp,
                           "按后报同栏比较；方案或成本性质跨越披露调整",
                           "成本分析表比较列")
    for x in cells:
        if x["单元状态"] in ("原表空白","原表符号或不适用"):
            if x["表名"] in (INV,AR,AGE) or x["原行"] in ("实施成本","工业自动化控制｜实施成本"):
                gaps.append(dict(年度=x["数据年度"],维度=x["表名"],缺项=x["原行"]+"｜"+x["原列"],
                  状态=x["单元状态"],原表范围=locator(x),处理="保留原格，不填零",单元ID=x["单元ID"]))
    for x in checks:
        if x["结果"]=="差额待裁定":
            gaps.append(dict(年度=x["年度"],维度="勾稽差额",缺项=x["勾稽项"]+"的调节项目",
                状态="原列差额 "+x["差额"]+" "+x["单位"],原表范围="见勾稽差额的左侧与基准单元",
                处理=x["口径"],单元ID=x["基准单元"]))
    for r in statistics:
        y=r["年度"]
        r["年度合并范围附注"]=f"{y}年报 p{SCOPE[y][0]}｜{SCOPE[y][1]}"
        if y in (2019,2020,2022,2023) and r["维度"] in (*STATEMENTS,REV):
            r["列报合并同比_pct"]=r.pop("复算同比_pct","")
            r["列报合并毛利率变动_pp"]=r.pop("毛利率同比_pp","")
            r["比较规则"]+="；年度合并范围变动，列报同比单列，固定范围同比留缺"
    return bridges,statistics,checks,gaps

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--annual-dir",type=Path,default=COMPANY/"sources/raw/01_年报")
    p.add_argument("--output",type=Path,default=HERE)
    args=p.parse_args()
    run(args.annual_dir,args.output)

def run(raw,out,grid_cache=None):
    cells,idx=report_data(raw,grid_cache)
    evidence,fact_counts=fact_audit(cells,idx)
    bridges,stats,checks,gaps=calculate(cells)
    out.mkdir(parents=True,exist_ok=True)
    runtime=dict(年报数=len(idx),原表单元=len(cells),年度分布=dict(sorted(Counter(x["报告年度"] for x in cells).items())),
       空白与符号=dict(Counter(x["单元状态"] for x in cells)),数字口径桥=len(bridges),统计数=len(stats),
       勾稽=dict(Counter(x["结果"] for x in checks)),缺项数=len(gaps),**fact_counts)
    write_csv(out,"年报索引.csv",idx)
    write_csv(out,"清洗底表.csv",cells)
    write_csv(out,"口径桥.csv",bridges)
    write_csv(out,"分类映射.csv",[dict(维度=d,年度=y,原分类及变化=x,采用规则=n,原页=p) for d,y,x,n,p in method_bridge()])
    write_csv(out,"基础统计.csv",stats)
    write_csv(out,"勾稽差额.csv",checks)
    write_csv(out,"缺项表.csv",gaps)
    write_csv(out,"既有Fact对照.csv",evidence)
    (out/"复算摘要.json").write_text(json.dumps(runtime,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(runtime,ensure_ascii=False))
    return runtime

if __name__=="__main__":
    main()
