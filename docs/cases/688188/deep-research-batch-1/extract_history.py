"""对读固定发行人 PDF 的报表与比较列。输出 CSV，不改核验账本。"""
import argparse
import csv
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COMPANY = ROOT / "companies/688188_柏楚电子"
ISSUER = "上海柏楚电子科技股份有限公司（合并）"
REPORTS = {
    "2019-FY":"1207650766", "2020-FY":"1209366984", "2021-FY":"1212923874",
    "2022-FY":"1216370312", "2023-FY":"1219348501", "2024-FY":"1222993275",
    "2025-FY":"1225091045", "2025-H1":"1224531818", "2025-YTD9":"1224745509",
    "2026-Q1":"1225259202", "2026-H1":"1225477071", "2026-YTD9":"1225622322",
}
HEADERS = {"IS":"合并利润表", "BS":"合并资产负债表", "CF":"合并现金流量表"}
METRICS = {
    "IS": {"revenue":"^(一、)?营业总收入", "cost":"^(其中[:：])?营业成本",
           "surcharge":"^税金及附加", "sales":"^销售费用", "admin":"^管理费用",
           "rd":"^研发费用", "fin":"^财务费用", "other_income":"^(加[:：])?其他收益",
           "investment":"^投资收益", "valuation":"^公允价值变动收益",
           "credit":"^信用减值损失", "impairment":"^资产减值损失",
           "disposal":"^资产处置收益", "reported_ebit":"^三、营业利润",
           "income_tax":"^减[:：]所得税费用", "net_profit":"^五、净利润",
           "parent_profit":"^(1\\.|1、|\\(一\\)|（一）)?归属[于与]母公司(所有者|股东)(的)?净利润",
           "eps":"^[(（]一[)）]基本每股收益"},
    "BS": {"ar":"^应收账款", "inventory":"^存货", "ap":"^应付账款",
           "fixed":"^固定资产", "cip":"^在建工程", "shares":"^(股本|实收资本)"},
    "CF": {"cfo":"^经营活动产生的现金流",
           "capex":"^购建固定资产、无形资产",
           "cash_taxes_all":"^支付的各项税费"},
}
NUM = re.compile(r"(?<![\d.,\w])[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2,4}(?![\d.])")
ANN = {
    2019:(160, None), 2020:(None,None), 2021:(None,None),
    2022:(None,None), 2023:(None,None), 2024:(205,25), 2025:(221,27),
}


def compact(value):
    return re.sub(r"\s+", "", value)


def numbers(value):
    return [D(v.replace(",", "").replace("−", "-")) for v in NUM.findall(value)]


def find_row(pages, page_indices, pattern, columns=2):
    for number in page_indices:
        lines = pages[number-1].splitlines()
        for index,line in enumerate(lines):
            if not re.search(pattern, compact(line)) or compact(line).endswith("："):
                continue
            snippet = line
            vals = numbers(line)
            # A long label can wrap, with amounts between the two fragments.
            if not vals:
                for line2 in lines[index+1:index+4]:
                    continuation = compact(line2)
                    if not re.match(r'^(?:[“”"（(－−-]*(?:填|列|号|以|量净额|净额|额|净亏损|亏损|[其]?他长期|期资产支付|资产支付|产支付|支付的现金)|[-−]?\d|七、)', continuation):
                        break
                    snippet += " "+line2
                    vals = numbers(line2)
                    if vals:
                        break
            if vals:
                return number, index+1, snippet.strip(), vals[:columns]
    return None


def locate_reports():
    manifest = json.loads((COMPANY/"sources/manifest.json").read_text(encoding="utf-8"))["sources"]
    return {period:next(s for s in manifest if s["path"].endswith(f"_{number}.pdf"))
            for period,number in REPORTS.items()}


def csv_write(dest, name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (dest/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f, fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def annual_note(pages):
    for index,page in enumerate(pages):
        if index>110 and re.search(r"(?m)^主营业务\s+[-\d]",page) and re.search(r"(?m)^其他业务\s+[-\d]",page):
            return index+1
    return None


def source_row(period, meta, table, metric, found, position, value, formula="原值"):
    date = Path(meta["path"]).name[:10]
    return dict(report=period, available=date, entity=ISSUER, table=table, metric=metric,
                physical_page=found[0], text_line=found[1], original_row=found[2], column=position,
                unit="元/股" if metric=="eps" else "人民币元", raw_value=value,
                formula=formula, source_id=meta["id"],sha256=meta["sha256"],
                url=f"https://static.cninfo.com.cn/finalpage/{date}/{REPORTS[period]}.PDF",
                state="原表对读")


def extract(dest):
    sources=locate_reports()
    cells=[]
    products=[]
    missing=[]
    originals=[]
    for period,meta in sources.items():
        path=COMPANY/meta["path"]
        if not path.is_file():
            raise FileNotFoundError(f"{path}，先按 README 恢复原件")
        content=path.read_bytes()
        assert sha256(content).hexdigest()==meta["sha256"],path
        file=PdfReader(path)
        pages=[pg.extract_text() for pg in file.pages]
        year=int(period[:4])
        blob = ""
        if period.endswith("FY"):
            rel=path.relative_to(ROOT).as_posix()
            blob=subprocess.check_output(["git","hash-object","--no-filters",str(path)],cwd=ROOT,text=True).strip()
            assert blob==subprocess.check_output(["git","rev-parse","HEAD:"+rel],cwd=ROOT,text=True).strip()
        originals.append(dict(period=period,available=path.name[:10],source_id=meta["id"],
                              path=meta["path"], sha256=meta["sha256"],git_blob=blob,pages=len(pages)))
        for table,metrics in METRICS.items():
            heading=HEADERS[table]
            start=next(i+1 for i,txt in enumerate(pages)
                       if (i>50 or ("FY" not in period and "H1" not in period))
                       and any(compact(line)==heading for line in txt.splitlines()))
            section = pages.copy()
            end = min(start+4,len(pages)+1)
            for num in range(start,end):
                lines = pages[num-1].splitlines()
                markers = [i for i,line in enumerate(lines)
                           if compact(line)==heading.replace("合并","母公司")]
                if markers:
                    section[num-1]="\n".join(lines[:markers[0]])
                    end=num+1
                    break
            for metric,label in metrics.items():
                found=find_row(section,range(start,end),label)
                if not found:
                    missing.append(dict(report=period,table=table,metric=metric,from_physical_page=start,
                                        reason="原表留白或抽取未定位"))
                    continue
                # Amount rows with one number are not assigned to a period by guess.
                if len(found[3]) != 2:
                    missing.append(dict(report=period,table=table,metric=metric,from_physical_page=start,
                                        reason="仅一列有数，保留原行待列位核对",original=found[2]))
                    continue
                for j,v in enumerate(found[3]):
                    column=("期末" if j==0 else "上年末") if table=="BS" else ("本期" if j==0 else "比较")
                    cells.append(source_row(period,meta,heading,metric,found,column,v))
        if period.endswith("FY") or period.endswith("H1"):
            note=annual_note(pages)
            if note:
                for metric in ("主营业务","其他业务","合计"):
                    found=find_row(pages,[note],'^'+metric,4)
                    if found and len(found[3])==4:
                        for j,v in enumerate(found[3]):
                            col=("本期" if j<2 else "比较")+("收入" if j%2==0 else "成本")
                            products.append(source_row(period,meta,"营业收入和营业成本附注",metric,found,col,v))
        if year in (2024,2025) and period.endswith("FY"):
            pp=ANN[year][1]
            groups=["平面解决方案","管材解决方案","三维解决方案","其他"]
            views = [("主营业务分产品情况", groups, pp, 0),
                     ("主营业务分地区情况", ["华中和华南","华东","华北","东北","其他"], pp, 1),
                     ("主营业务分销售模式情况", ["直销"], pp+1, 0)]
            for caption,groups,first,skip in views:
                for group in groups:
                    selected=range(first,first+2) if group != "其他" or not skip else [pp+1]
                    if caption == "主营业务分地区情况" and group == "其他" and year==2025:
                        # The same page contains both product and regional '其他'.
                        source=pages[pp].split(caption,1)[1]
                        match=find_row([source],[1],r"^其他(?=\d)",2)
                        offset=pages[pp].split(caption,1)[0].count("\n")
                        found=(pp+1,match[1]+offset,match[2],match[3]) if match else None
                    else:
                        found=find_row(pages,selected,f"^{group}"+r"(?=\d|[-−])",2)
                    if found:
                        for j,v in enumerate(found[3]):
                            products.append(source_row(period,meta,caption,group,found,
                                                       ("本期收入","本期成本")[j],v))
    csv_write(dest,"originals.csv",originals)
    csv_write(dest,"filing-cells.csv",cells)
    csv_write(dest,"disclosure-gaps.csv",missing)
    csv_write(dest,"classification-cells.csv",products)
    return cells, products


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=HERE)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    cells, products=extract(args.output)
    print("原表单元格",len(cells),"分类单元格",len(products))


if __name__=="__main__":
    main()
