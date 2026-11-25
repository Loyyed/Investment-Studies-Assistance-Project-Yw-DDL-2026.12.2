"""Extract accession-pinned issuer annual reports into source cells and checks."""
import argparse
import csv
from collections import Counter, defaultdict
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import pymupdf

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
COMPANY = REPO / "companies/688188_柏楚电子"
WORKSPACE = REPO.parent / "投资学工作空间"
ARCHIVE = REPO.parent / "688188-deep-research-batch-2"
ISSUER = "上海柏楚电子科技股份有限公司及年度合并子公司"
MDA = "管理层讨论与分析·"
SOURCE_IDS = [1207650766,1209366984,1212923874,1216370312,1219348501,1222993275,1225091045]
# Physical pages, 1-based. Expense table range includes continuations.
# MD&A start/end, balance sheet start, cash flow start, revenue note, AR start,
# inventory start, cash-flow note start, last expense page, AR provision table.
PAGES = {
    2019:(21,23,83,91,160,130,138,168,162,131),
    2020:(24,26,93,102,168,140,148,177,171,141),
    2021:(25,28,105,113,182,151,159,190,184,153),
    2022:(25,28,98,106,174,142,149,182,177,143),
    2023:(24,27,101,109,184,145,157,192,186,146),
    2024:(25,28,108,115,205,159,173,213,208,161),
    2025:(27,30,121,129,221,171,188,229,224,173),
}
STATEMENTS = ("合并资产负债表","合并利润表","合并现金流量表")
SCOPE = {
    2019:("171–175","非同一控制下企业合并"),
    2020:("180–181","其他原因栏列新设子公司"),
    2021:("192–194","合并范围变更各栏列不适用"),
    2022:("185–186","其他原因栏列新设子公司"),
    2023:("196–197","其他原因栏列新设子公司"),
    2024:("218","本年其他原因栏列不适用，另说明2023年12月新设子公司"),
    2025:("234","合并范围变更各有关栏列不适用"),
}
# Start page, printed fragment, full label. The numeric cells can be on either leaf.
SPLIT_ROWS = {
    (2021,110,"（一）归属母公司所有者的其他综"):(111,"合收益的税后净额","（一）归属母公司所有者的其他综合收益的税后净额"),
    (2021,113,"支付给职工及为职工支付的"):(114,"现金","支付给职工及为职工支付的现金"),
    (2024,112,"投资收益（损失以“－”号填"):(113,"列）","投资收益（损失以“－”号填列）"),
    (2024,116,"收到其他与投资活动有关的"):(117,"现金","收到其他与投资活动有关的现金"),
    (2025,130,"四、汇率变动对现金及现金等价"):(131,"物的影响","四、汇率变动对现金及现金等价物的影响"),
}
SPLIT_ENDS = {(y,q,end):(p,start,full) for (y,p,start),(q,end,full) in SPLIT_ROWS.items()}
NUM = re.compile(r"[+\-−－]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
HEAD = re.compile(r"(合并|母公司)(?:资产负债表|利润表|现金流量表|所有者权益变动表)|\d+[、.](?:销售费用|管理费用|研发费用|财务费用|现金流量表补充资料)")
TOTALS = ("合计","总计")

def clean(s):
    return re.sub(r"\s+", "", s or "")

def number(s):
    s=clean(s)
    if not NUM.fullmatch(s):
        return None
    return D(s.replace(",", "").replace("−","-").replace("－","-"))

def state(s):
    v=number(s)
    if v is not None:
        return "明确零值" if v==0 else "数值"
    s=clean(s)
    if not s:
        return "原表空白"
    if s in {"-","—","－","--","–","/","不适用"}:
        return "原表符号或不适用"
    return "原表文字"

def display(x):
    return "" if x is None else format(x,"f")

def write_csv(out,name,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with (out/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,keys,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def page_grids(pg):
    marks=[]
    for block in pg.get_text("dict")["blocks"]:
        for line in block.get("lines",[]):
            s=clean("".join(span["text"] for span in line["spans"]))
            if HEAD.fullmatch(s):
                marks.append((s,line["bbox"][1]))
    tables=[(t.bbox,t.extract()) for t in pg.find_tables().tables]
    return sorted(marks,key=lambda x:x[1]),tables

def grid_rows(grids,pages):
    for page in pages:
        for table_index,(bbox,rows) in enumerate(grids.get(page, ([], []))[1],1):
            yield page,table_index,bbox,rows

class Extract:
    def __init__(self,y,meta,doc,grids):
        self.y=y
        self.meta=meta
        self.doc=doc
        self.grids=grids
        self.cells=[]
        self.catalog=defaultdict(list)

    def emit(self,p,t,n,table,row,col,literal,observed=None,unit="人民币元",
             kind="审计财务报表及附注",role="本期",basis="",extra=""):
        value=number(literal)
        ix=f"A{self.y}-P{p:03d}-T{t}-R{n:02d}-{len(self.cells)+1:04d}"
        factor=10000 if unit=="人民币万元" else 1
        self.cells.append(dict(单元ID=ix,报告年度=self.y,数据年度=self.y if observed is None else observed,
             可获日期=self.meta["date"],PDF物理页=p,印刷页=p,页内表序=t,表内行序=n,表名=table,原行=row,
             原列=col,列角色=role,披露类型=kind,合并范围=ISSUER,原单位=unit,原字面值=(literal or "").replace("\n"," "),
             单元状态=state(literal),标准值=display(value*factor if value is not None else None),
             标准单位="人民币元" if factor==10000 else unit,业务口径=basis,
             来源编号=self.meta["id"],来源SHA256=self.meta["sha256"],备注=extra))
        if p not in self.catalog[table]:
            self.catalog[table].append(p)
        return self.cells[-1]

    def statement(self, b, c):
        y=self.y
        for p,t,(x0,top,x1,bottom),rows in grid_rows(self.grids,range(b,c+5)):
            marks=[(h,q,yy) for q in range(b,p+1) for h,yy in self.grids[q][0]
                   if q!=p or yy<top]
            h=marks[-1][0] if marks else ""
            if h not in STATEMENTS or len(rows[0])!=4:
                continue
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if not label or label=="项目":
                    continue
                source_location=""
                key=(y,p,label)
                if key in SPLIT_ENDS:
                    prev,start,full=SPLIT_ENDS[key]
                    if all(not clean(r[j]) for j in (2,3)):
                        continue
                    source_location=f"原行名跨PDF第{prev}–{p}页；本页为金额格"
                    label=full
                if key in SPLIT_ROWS:
                    next_page,fragment,full=SPLIT_ROWS[key]
                    ends=[r2 for _,_,_,rs in grid_rows(self.grids,[next_page]) for r2 in rs
                          if len(r2)==4 and clean(r2[0])==fragment]
                    if all(not clean(r[j]) for j in (2,3)) and any(clean(e[j]) for e in ends for j in (2,3)):
                        continue
                    source_location=f"原行名跨PDF第{p}–{next_page}页；本页为起行"
                    label=full
                # Ignore merged section labels. Retain existing blank value cells.
                if r[2] is None and r[3] is None:
                    continue
                for j in (0,1):
                    col=(f"{y-j}年12月31日" if h==STATEMENTS[0] else f"{y-j}年度")
                    unit="人民币元/股" if "每股收益" in label else "人民币元"
                    self.emit(p,t,n,h,label,col,r[2+j],y-j,unit,role="比较" if j else "本期",
                              extra=source_location or (f"原附注栏 {clean(r[1])}" if r[1] else ""))

    def operations(self,m,m2):
        y=self.y
        unit="人民币万元" if y==2019 else "人民币元"
        first_section=""
        cost_section=""
        group=""
        for p,t,bbox,rows in grid_rows(self.grids,range(m,m2+1)):
            cols=len(rows[0])
            labels=[clean(r[0]) for r in rows]
            if "主要产品" in labels and cols==8:
                for n,r in enumerate(rows,1):
                    label=clean(r[0])
                    if clean(r[1])!="套":
                        continue
                    for j,name in enumerate(("生产量","销售量","库存量","生产量同比","销售量同比","库存量同比")):
                        self.emit(p,t,n,MDA+"产销量情况分析表",label,name,r[2+j],
                                  unit="套" if j<3 else "%",kind="管理层讨论表格",
                                  basis="发行人披露的产品统计范围")
                continue
            is_cost=(cols==8 and ("分行业情况" in labels or "分产品情况" in labels or
                    (cost_section and any(clean(r[1]) in ("原材料","人工成本","制造费用","运费","实施成本","小计","合计") for r in rows))))
            if is_cost:
                cost_unit="人民币万元" if y<=2020 else "人民币元"
                for n,r in enumerate(rows,1):
                    label=clean(r[0])
                    item=clean(r[1])
                    if label in ("分行业情况","分产品情况"):
                        cost_section=label
                        group="工业自动化控制" if label=="分行业情况" else ""
                        continue
                    if not cost_section or not item or "成本构成" in item:
                        continue
                    if cost_section=="分产品情况" and label:
                        if y==2025 and label in ("平面","解决方案"):
                            label="平面解决方案"
                        group=label
                    elif cost_section=="分行业情况":
                        group="工业自动化控制"
                    if not group or not (number(r[2]) is not None or number(r[4]) is not None):
                        continue
                    for j,(c0,off,u0) in enumerate((("本期金额",0,cost_unit),("本期占总成本比例",0,"%"),
                         ("上年同期金额",1,cost_unit),("上年同期占总成本比例",1,"%"),("本期金额同比",0,"%"))):
                        self.emit(p,t,n,MDA+"成本分析表·"+cost_section,group+"｜"+item,c0,r[2+j],y-off,u0,
                                  "管理层讨论表格","比较" if off else "本期",group)
                continue
            if cols not in (7,8):
                continue
            if not first_section and "主营业务分行业情况" not in labels:
                continue
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if label.startswith("主营业务分") and label.endswith("情况"):
                    first_section=label
                if label in ("分行业","分产品","分地区","销售模式"):
                    first_section="主营业务"+("分" if label=="销售模式" else "")+label+"情况"
                if not first_section or not label or number(r[1]) is None or number(r[2]) is None:
                    continue
                to_extract=r[4:8] if cols==8 else r[3:7]
                table=MDA+first_section
                basis=("管理层表覆盖合并营业总额" if y<=2021 else "管理层表覆盖主营业务")
                for j,(name,v) in enumerate(zip(("营业收入","营业成本","毛利率","营业收入同比","营业成本同比","毛利率同比变动"),list(r[1:3])+list(to_extract))):
                    self.emit(p,t,n,table,label,name,v,unit=unit if j<2 else "%" if j<5 else "百分点",
                              kind="管理层讨论表格",basis=basis)
        assert sum(x["原列"]=="销售量" for x in self.cells)>=2

    def notes(self,rv,ar,inv,cf,ex,ar_bad):
        y=self.y
        for p,t,_,rows in grid_rows(self.grids,[rv]):
            if len(rows[0])!=5 or not any(clean(r[0])=="主营业务" for r in rows):
                continue
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if label not in ("主营业务","其他业务","合计"):
                    continue
                for j,c in enumerate(("本期发生额·收入","本期发生额·成本","上期发生额·收入","上期发生额·成本")):
                    self.emit(p,t,n,"营业收入和营业成本附注",label,c,r[1+j],y-(j>=2),role="比较" if j>=2 else "本期")
        # Aging schedule stops at its total. 2019–2022 print a current column only.
        age_started=False
        age_end=False
        for p,t,_,rows in grid_rows(self.grids,range(ar,ar+2)):
            if len(rows[0])!=(2 if y<2023 else 3):
                continue
            if clean(rows[0][0])=="账龄":
                age_started=True
            if not age_started or age_end:
                continue
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if not label or label=="账龄" or label.startswith("其中"):
                    continue
                for j,v in enumerate(r[1:]):
                    self.emit(p,t,n,"应收账款附注·按账龄披露",label,("期末账面余额","期初账面余额")[j],
                              v,y-j,role="比较" if j else "本期")
                if label=="合计":
                    age_end=True
                    break
        for p,t,_,rows in grid_rows(self.grids,[ar_bad]):
            if not any(clean(r[0])=="类别" and clean(r[1])=="期末余额" and len(r)>=11 for r in rows):
                continue
            indices=(1,2,3,4,5,6,8,10,12,13) if y==2023 else tuple(range(1,11))
            names=("账面余额","比例","坏账准备金额","计提比例","账面价值")
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if not label or label in ("类别","其中："):
                    continue
                for j,k in enumerate(indices):
                    self.emit(p,t,n,"应收账款附注·按坏账计提方法分类披露",label,
                              ("期末·" if j<5 else "期初·")+names[j%5],r[k],y-(j>=5),
                              "%" if j%5 in (1,3) else "人民币元",role="比较" if j>=5 else "本期")
        inv_started=False
        inv_end=False
        for p,t,_,rows in grid_rows(self.grids,[inv,inv+1]):
            if len(rows[0])!=7:
                continue
            if any(any(clean(v)=="账面价值" for v in r) for r in rows[:2]):
                inv_started=True
            if not inv_started or inv_end:
                continue
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if not label or label=="项目":
                    continue
                for j,v in enumerate(r[1:]):
                    self.emit(p,t,n,"存货附注·存货分类",label,("期末·" if j<3 else "期初·")+
                              ("账面余额","跌价或履约成本减值准备","账面价值")[j%3],
                              v,y-(j>=3),role="比较" if j>=3 else "本期")
                if label=="合计":
                    inv_end=True
                    break
        exp_start=[]
        for p in range(rv,ex+1):
            for h,yy in self.grids[p][0]:
                if h.endswith("费用"):
                    exp_start.append((p,yy,re.split(r"[、.]",h,maxsplit=1)[1]))
        for p,t,(_,top,*_),rows in grid_rows(self.grids,range(rv,ex+1)):
            active=[(q,yy,h) for q,yy,h in exp_start if (q,yy)<(p,top)]
            if not active or len(rows[0]) not in (3,4):
                continue
            h=active[-1][2]
            if h in self.catalog_totals:
                continue
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if not label or label=="项目":
                    continue
                for j,v in enumerate(r[1:3]):
                    self.emit(p,t,n,h+"附注",label,("本期发生额","上期发生额")[j],v,y-j,
                              role="比较" if j else "本期")
                if label=="合计":
                    self.catalog_totals.add(h)
                    break
        cash=False
        for p,t,_,rows in grid_rows(self.grids,[cf,cf+1]):
            if len(rows[0])!=3:
                continue
            if clean(rows[0][0])=="补充资料":
                cash=True
            if not cash:
                continue
            for n,r in enumerate(rows,1):
                label=clean(r[0])
                if not label or label=="补充资料":
                    continue
                for j,v in enumerate(r[1:3]):
                    self.emit(p,t,n,"现金流量表补充资料",label,("本期金额","上期金额")[j],v,y-j,
                              role="比较" if j else "本期")
                if label=="现金及现金等价物净增加额":
                    cash=False
                    break

    def run(self):
        m,m2,b,c,rv,a,inv,cf,ex,ar_bad=PAGES[self.y]
        self.catalog_totals=set()
        self.statement(b,c)
        self.operations(m,m2)
        self.notes(rv,a,inv,cf,ex,ar_bad)
        if self.y==2024:
            p=153
            for _,t,_,rows in grid_rows(self.grids,[p]):
                for n,r in enumerate(rows,1):
                    if len(r)==3 and clean(r[1]) in ("无影响","营业成本","销售费用"):
                        self.emit(p,t,n,"重要会计政策变更附注",clean(r[1]),"影响金额·2023年（合并）",
                                  r[2],2023,role="重述影响",extra=clean(r[0]))
        return self.cells

def report_data(raw, cache=None):
    manifest=json.loads((COMPANY/"sources/manifest.json").read_text(encoding="utf-8"))["sources"]
    all_cells=[]
    index=[]
    for y,accession in zip(PAGES,SOURCE_IDS):
        entry=next(x for x in manifest if x["path"].endswith(f"_{accession}.pdf"))
        filename=Path(entry["path"]).name
        source=raw/filename
        assert sha256(source.read_bytes()).hexdigest()==entry["sha256"],source
        date=filename[:10]
        m,m2,b,c,rv,a,inv,cf,ex,ar_bad=PAGES[y]
        selected=set(range(m,m2+1))|set(range(b,c+5))|set(range(rv,ex+2))|set(range(a,a+5))|{inv,inv+1,cf,cf+1}|({153} if y==2024 else set())
        with pymupdf.open(source) as doc:
            if cache:
                saved=json.loads((cache/f"{y}.json").read_text(encoding="utf-8"))
                grids={int(p):(x["marks"],[(t["bbox"],t["rows"]) for t in x["tables"]]) for p,x in saved.items()}
            else:
                grids={p:page_grids(doc[p-1]) for p in sorted(selected)}
            extract=Extract(y,{**entry,"date":date},doc,grids)
            all_cells.extend(extract.run())
            index.append(dict(报告年度=y,可获日期=date,文件名=filename,PDF总页数=len(doc),来源编号=entry["id"],
                  SHA256=entry["sha256"],本地原件=str(source.resolve()),
                  公司目录相对路径=entry["path"],合并范围变更附注物理页=SCOPE[y][0],合并范围变更列报=SCOPE[y][1],页码基准="从PDF封面起算，物理页与本批相关印刷页一致",
                  **{f"{table}物理页":"、".join(map(str,pgs)) for table,pgs in extract.catalog.items()}))
    return all_cells,index
