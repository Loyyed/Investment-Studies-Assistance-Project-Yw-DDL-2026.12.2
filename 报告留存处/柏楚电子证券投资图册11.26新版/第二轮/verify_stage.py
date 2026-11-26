"""Verify round-two source links and key calculations independently."""
from argparse import ArgumentParser
import csv
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import re

from pypdf import PdfReader

HERE=Path(__file__).resolve().parent

def table(f):
    with f.open(encoding="utf-8-sig",newline="") as h:
        return list(csv.DictReader(h))

def verify(first,out):
    pins=json.loads((HERE/"第一轮输入指纹.json").read_text(encoding="utf-8"))
    assert len(pins)==9
    for name,expected in pins.items():
        assert sha256((first/name).read_bytes()).hexdigest()==expected,name
    original={r["单元ID"]:r for r in table(first/"清洗底表.csv")}
    sources={int(r["报告年度"]):r for r in table(first/"年报索引.csv")}
    refs={r["单元ID"]:r for r in table(out/"底表引用索引.csv")}
    items={(r["计算段"],r["数据期"],r["项目"]):r for r in table(out/"经营桥明细.csv")}
    for r in items.values():
        for key in r["第一轮底表单元"].split("；"):
            assert key in refs and all(refs[key][k]==v for k,v in original[key].items()),key
    paths={y:Path(m["本地原件"]) for y,m in sources.items()}
    for y,p in paths.items():
        assert sha256(p.read_bytes()).hexdigest()==sources[y]["SHA256"],p
    docs={}
    evidence=[]
    for x in json.loads((HERE/"年报原文定位.json").read_text(encoding="utf-8")):
        y,n=x["year"],x["page"]
        if y not in docs:
            docs[y]=PdfReader(paths[y])
        page=docs[y].pages[n-1].extract_text(extraction_mode="layout")
        compact=lambda s:re.sub(r"\s+","",s)
        assert compact(x["anchor"]) in compact(page),(x["id"],y,n)
        m=sources[y]
        evidence.append(dict(原文编号=x["id"],报告年度=y,PDF物理页=n,可获日期=m["可获日期"],年报文件=m["文件名"],
                          来源编号=m["来源编号"],SHA256=m["SHA256"],小节=x["section"],原页锚点=x["anchor"],
                          披露摘要=x["summary"],证据边界=x["bound"],相关计算段=x["bridge"]))

    def v(code,period,k):
        return F(items[code,str(period),k]["精确结果"])

    def near(a,b):
        assert abs(a-b)<F("0.0000000001"),(a,b)

    plane="平面解决方案·"
    rev0=v("B04",2024,plane+"收入")
    rev1=v("B04",2025,plane+"收入")
    cost1=v("B04",2025,plane+"成本")
    main_r=v("B03","2024→2025","本期主营收入")
    main_c=v("B03","2024→2025","本期主营成本")
    near(100*rev1/main_r,v("B04",2025,plane+"主营收入占比"))
    near(100*(rev1-cost1)/(main_r-main_c),v("B04",2025,plane+"主营毛利占比"))
    near(100*(rev1/rev0-1),v("B04","2024→2025",plane+"收入同比"))
    near(v("B04","2024→2025","主营毛利率组合权重贡献")+v("B04","2024→2025","主营毛利率组内贡献"),
         v("B03","2024→2025","主营毛利率变化"))
    for window in ("2021→2022","2023→2024","2024→2025"):
        profit=lambda k:v("B02",window,k)
        near(profit("收入变化")-profit("营业成本变化"),profit("毛利额变化"))
        fees=sum((profit(k+"变化") for k in ("税金及附加","销售","管理","研发","财务")),F(0))
        op=profit("毛利额变化")-fees+profit("其他营业利润项目净变动")
        near(op,profit("营业利润变化"))
        near(op+profit("营业外收支净变动")-profit("所得税费用变化")-profit("少数股东损益变化"),
             profit("归母净利润变化"))
        c=lambda k:v("B09",window,k)
        working=sum((c(k+"调节变动") for k in ("存货","应收","应付")),F(0))
        near(c("合并净利润变化")+working+c("其他间接调节变化"),c("经营现金流变化"))
        direct=sum((c(k+"变化（CFO方向）") for k in ("销售收现","税费返还","采购付现","职工付现","税费付现")),F(0))
        near(direct+c("其他直接流量净变动"),c("经营现金流变化"))
        near(c("经营现金流变化")-c("购建付现变化"),c("简化现金余量变化"))
    for y in range(2021,2026):
        near(v("B08",y,"直销收入覆盖"),F(100))
    x=lambda y,k:v("B11",y,"智能硬件·"+k)
    near(x(2024,"库存量")+x(2025,"生产量")-x(2025,"销售量"),F(5929))
    assert v("B11",2025,"硬件库存差额")==-2034 and x(2025,"库存量")==7963
    with (out/"年报原文定位.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,evidence[0].keys(),lineterminator="\n")
        w.writeheader()
        w.writerows(evidence)
    stats={"锁定第一轮文件":len(pins),"原件指纹":len(paths),"原文锚点":len(evidence),
           "桥接记录":len(items),"引用第一轮单元":len(refs),"独立复算":29,
           "平面收入占比_pct":round(float(100*rev1/main_r),6),
           "平面毛利占比_pct":round(float(100*(rev1-cost1)/(main_r-main_c)),6),
           "硬件库存差额_套":-2034}
    print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    p.add_argument("--first",type=Path,default=HERE.parent/"第一轮")
    p.add_argument("--output",type=Path,default=HERE)
    a=p.parse_args()
    verify(a.first,a.output)
