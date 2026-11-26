"""Read-only first-round checks using the delivered CSVs and a second PDF parser."""
import argparse
import csv
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import re

from pypdf import PdfReader

HERE=Path(__file__).resolve().parent

def table(base,file):
    with (base/file).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def verify(base):
    index={int(r["报告年度"]):r for r in table(base,"年报索引.csv")}
    assert sorted(index)==list(range(2019,2026))
    cells=table(base,"清洗底表.csv")
    by_id={r["单元ID"]:r for r in cells}
    assert len(cells)==len(by_id)
    for r in cells:
        meta=index[int(r["报告年度"])]
        assert r["来源SHA256"]==meta["SHA256"]
        assert 1<=int(r["PDF物理页"])<=int(meta["PDF总页数"])
        assert r["可获日期"]==meta["可获日期"]
        if r["单元状态"]=="原表空白":
            assert r["原字面值"]==r["标准值"]==""
        elif r["单元状态"]=="明确零值":
            assert F(r["标准值"])==0
    docs={}
    for y,m in index.items():
        f=Path(m["本地原件"])
        assert sha256(f.read_bytes()).hexdigest()==m["SHA256"]
        docs[y]=PdfReader(f)
        assert len(docs[y].pages)==int(m["PDF总页数"])

    def cell(y,t,row,col):
        found=[r for r in cells if r["报告年度"]==str(y) and r["表名"]==t
               and r["原行"]==row and r["原列"]==col]
        assert len(found)==1,(y,t,row,col,len(found))
        return found[0]

    def source_number(y,t,row,col,amount,label=None):
        r=cell(y,t,row,col)
        assert F(r["标准值"])==F(amount),r
        page=int(r["PDF物理页"])
        text=docs[y].pages[page-1].extract_text(extraction_mode="layout")
        compact=re.sub(r"\s+","",text)
        visible=re.sub(r"\s+","",r["原字面值"])
        assert visible in compact,(y,page,visible)
        if label:
            assert label in compact,(y,page,label)
        return F(r["标准值"])

    revenue="一、营业总收入"
    actual_revenues=["376070956.02","570829250.31","913439700.70","898491949.44",
                     "1407113183.52","1735455070.67","2195632312.92"]
    for y,amt in zip(index,actual_revenues):
        source_number(y,"合并利润表",revenue,f"{y}年度",amt,"营业总收入")
    source_number(2025,"合并资产负债表","应收账款","2025年12月31日","167471766.72","应收账款")
    source_number(2025,"合并现金流量表","经营活动产生的现金流量净额","2025年度","1104320726.22")
    cost23=source_number(2023,"合并利润表","其中：营业成本","2023年度","276714081.20")
    cost23_new=source_number(2024,"合并利润表","其中：营业成本","2023年度","281140773.82")
    sales23=source_number(2023,"合并利润表","销售费用","2023年度","91034592.85")
    sales23_new=source_number(2024,"合并利润表","销售费用","2023年度","86607900.23")
    assert cost23_new-cost23==sales23-sales23_new==F("4426692.62")
    line="管理层讨论与分析·主营业务分产品情况"
    old=source_number(2024,line,"平面解决方案","营业收入","1124812900.80","平面解决方案")
    new=source_number(2025,line,"平面解决方案","营业收入","1292909787.48","平面解决方案")
    new_c=source_number(2025,line,"平面解决方案","营业成本","238589506.50","平面解决方案")
    source_number(2019,line,"随动系统","营业收入","164602100","随动系统")
    vol="管理层讨论与分析·产销量情况分析表"
    for item,p,s,i in (("控制系统","67434","65064","7340"),("智能硬件","59626","56824","7963")):
        for category,x in (("生产量",p),("销售量",s),("库存量",i)):
            source_number(2025,vol,item,category,x,item)
    stats=table(base,"基础统计.csv")
    case=next(r for r in stats if r["年度"]=="2025" and r["维度"]==line and r["项目"]=="平面解决方案")
    assert abs(100*(new/old-1)-F(case["复算同比_pct"]))<=F("0.0000005")
    assert abs(100*(1-new_c/new)-F(case["原披露口径毛利率_pct"]))<=F("0.0000005")
    conflicts=[r for r in stats if r["维度"]==vol and r["原列机械变化_pct"]]
    assert len(conflicts)==6 and all(not r["复算同比_pct"] for r in conflicts)

    checks=table(base,"勾稽差额.csv")
    for r in checks:
        rhs=r["基准单元"]
        left=r["左侧单元"].split("；") if r["左侧单元"] else []
        if r["差额"]:
            lhs=sum((F(by_id[x[1:]]["标准值"])*(1 if x[0]=="+" else -1) for x in left),F(0))
            assert lhs==F(r["左侧值"]) and lhs-F(by_id[rhs]["标准值"])==F(r["差额"]),r
        if r["勾稽项"].startswith(("产品","地区","销售模式")) and r["结果"]=="差额待裁定":
            raise AssertionError(r)
    assert all(r["结果"]=="缺项" for r in checks if r["年度"] in ("2019","2020") and r["勾稽项"].startswith("销售模式"))
    print(json.dumps({"原件SHA与页数":len(docs),"底表来源引用":len(cells),
                      "双解析原格抽核":23,"勾稽复算":sum(bool(r["差额"]) for r in checks),
                      "2025平面收入同比":case["复算同比_pct"],"2025平面毛利率":case["原披露口径毛利率_pct"],
                      "跨年实物口径分歧":len(conflicts)},ensure_ascii=False,indent=2))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=HERE)
    verify(parser.parse_args().output)
