"""Independent PDF cell and valuation check. Use --raw to check local issuer files."""
import argparse
import csv
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/"deep-research-batch-1"
ROOT=HERE.parents[3]
ORG=ROOT/"companies/688188_柏楚电子"
OUT=HERE/"data"
D=Decimal
EVIDENCE= {
    "2022-FY": {"revenue","cost","reported_ebit","cfo","capex","inventory","parent_profit"},
    "2024-FY": {"revenue","cost","reported_ebit","cfo","capex","inventory","parent_profit"},
    "2025-FY": {"revenue","cost","reported_ebit","cfo","capex","inventory","parent_profit"},
    "2026-H1": {"revenue","cost","sales","admin","rd","surcharge","cfo","capex","reported_ebit"},
    "2026-YTD9": {"revenue","cost","sales","admin","rd","surcharge","cfo","capex","reported_ebit","inventory","parent_profit"},
}


def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as s:
        return list(csv.DictReader(s))


def number_groups(text):
    return [D(s.replace(",","")) for s in re.findall(r"-?[0-9][0-9,]*\.[0-9]{2}(?![0-9])",text)]


def issuer_file(entry, archive):
    suffix=Path(entry['path'])
    local=ORG/suffix
    if local.is_file() or archive is None:
        target=local
    else:
        target=archive/ORG.relative_to(ROOT)/suffix
    if not target.is_file():
        raise FileNotFoundError(f"缺原件：{entry['source_id']}，请按原件清单恢复或加 --from-archive")
    assert hashlib.sha256(target.read_bytes()).hexdigest()==entry['sha256'],entry['source_id']
    return target


def verify_raw(archive=None):
    from pypdf import PdfReader

    sources={r["period"]:r for r in read_csv(PRIOR/"originals.csv")}
    cells=read_csv(PRIOR/"filing-cells.csv")
    direct={}
    measurements=[]
    for report,keys in EVIDENCE.items():
        manifest=sources[report]
        file=issuer_file(manifest,archive)
        pdf=PdfReader(file)
        cached={}
        for r in cells:
            if r["report"]!=report or r["metric"] not in keys or r["column"] not in ("本期","比较","期末","上年末"):
                continue
            n=int(r["physical_page"])
            if n not in cached:
                cached[n]=pdf.pages[n-1].extract_text()
            text=cached[n]
            # Locate the label independently. Two-year statements sometimes wrap the name.
            label={
                "cost":"其中：营业成本","revenue":"一、营业总收入","capex":"购建固定资产",
                "cfo":"经营活动产生的现金流","reported_ebit":"三、营业利润","inventory":"存货",
                "admin":"管理费用","sales":"销售费用","rd":"研发费用","surcharge":"税金及附加",
                "parent_profit":"归属于母公司"
            }[r["metric"]]
            idx=0 if r["column"] in ("本期","期末") else 1
            found=None
            for match in re.finditer(re.escape(label),text):
                sub=text[match.start():].splitlines()
                for row in (sub[0], " ".join(sub[:2]), " ".join(sub[:3])):
                    values=number_groups(row)
                    # year headings and units are fixed on the individually reviewed pages.
                    if len(values)>=2:
                        if values[idx]==D(r["raw_value"]):
                            found=values[idx]
                        break
                if found is not None:
                    break
            assert found is not None, (report,n,r["metric"],r["original_row"])
            direct[(report,r["metric"],idx)]=found
            measurements.append(dict(report=report,source_id=manifest["source_id"],sha256=manifest["sha256"],
                                     page=n,field=r["metric"],column=r["column"],yuan=str(found),
                                     record="PDF原表定位与发行人指纹；未改账本"))
    measurements.extend(verify_group_and_equity(sources,archive))
    q={}
    for idx in (0,1):
        q[idx]={k:direct[("2026-YTD9",k,idx)]-direct[("2026-H1",k,idx)] for k in sorted(EVIDENCE["2026-H1"])}
        q[idx]["gross"]=q[idx]["revenue"]-q[idx]["cost"]
        q[idx]["core"]=q[idx]["gross"]-sum(q[idx][k] for k in ("sales","admin","rd","surcharge"))
        q[idx]["cfo_less_capex"]=q[idx]["cfo"]-q[idx]["capex"]
    nonrec_reader=PdfReader(issuer_file(sources["2026-YTD9"],archive))
    p1=nonrec_reader.pages[0].extract_text()
    row=next(l for l in p1.splitlines() if "除非经常性损益的净利润" in l)
    amounts=number_groups(row)
    assert amounts[:2]==[D("302120212.71"),D("20.83")]
    assert q[0]["revenue"]==D("601316609.49")
    m0=q[0]["gross"]/q[0]["revenue"]
    m1=q[1]["gross"]/q[1]["revenue"]
    calc=dict(revenue_z=(q[0]["revenue"]/q[1]["revenue"]-1),gross_pp=100*(m0-m1),
              core_z=q[0]["core"]/q[1]["core"]-1,
              single_cash_z=q[0]["cfo_less_capex"]/q[1]["cfo_less_capex"]-1,
              deduction_yuan=amounts[0],deduction_disclosed_yoy_pct=amounts[1])
    qr={k:str(v) for k,v in calc.items()}
    for col,z in q.items():
        qr[f'quarter_{col}']={k:str(v) for k,v in z.items()}
    for col in (0,1):
        qr[f'2022_CFO_less_capex_col_{col}']=str(direct["2022-FY","cfo",col]-direct["2022-FY","capex",col])
    return measurements,qr


def verify_group_and_equity(sources,archive):
    from pypdf import PdfReader

    def record(report,page,label,index,target):
        originals=sources[report]
        file=issuer_file(originals,archive)
        reader=PdfReader(file)
        text=reader.pages[page-1].extract_text()
        # Scalar input uses the first statement line matching the printed label and columns.
        matches=[]
        for line in text.splitlines():
            if re.search(re.escape(label),line):
                nums=number_groups(line)
                if len(nums)>index and nums[index]==D(target):
                    matches.append(nums)
        assert matches,(report,page,label,target)
        return dict(report=report,source_id=originals["source_id"],sha256=originals["sha256"],page=page,
                    field=label,column="本期／期末；成本第二值" if index else "本期／期末（首金额）",
                    yuan=str(matches[0][index]),record="新组原表及权益独立核验")

    checks=[]
    for report,page,gcol in (("2024-FY",25,"24"),("2025-FY",28,"25")):
        groups=read_csv(HERE.parent/"product-bridge.csv")
        for row in groups:
            label=row["group"] if row["group"]!="其他主营" else "其他"
            for i,key in enumerate(("revenue","cost")):
                value=(D(row[f"{key}_{gcol}"])*1000000).quantize(D(".01"))
                # In FY25 three group rows appear on physical p27. Q4 activity slides use official
                # printed file physical numbering rather than markdown pagination.
                if report=="2025-FY":
                    found=False
                    for n in (27,28):
                        try:
                            rec=record(report,n,label,i,str(value))
                            checks.append(rec)
                            found=True
                            break
                        except AssertionError:
                            pass
                    assert found,(report,label,i,value)
                else:
                    checks.append(record(report,page,label,i,str(value)))
    for page,label,target in ((5,"货币资金","2134541130.72"),(5,"交易性金融资产","3596031132.18"),
                              (7,"实收资本（或股本）","405984426"),(12,"六、期末现金及现金等价物余额","2134536530.72")):
        checks.append(record("2026-YTD9",page,label,0,target))
    checks.append(record("2026-H1",137,"货币资金",0,"4600"))
    return checks


def audit():
    model=json.loads((OUT/"model.json").read_text(encoding="utf-8"))
    baseline=json.loads((PRIOR/"valuation-reproduction.json").read_text(encoding="utf-8"))
    reception=model["receipt"]
    eq=math.fsum(float(x["source_balance_m"])*int(x["sign"]) for x in read_csv(OUT/"equity-bridge.csv"))
    assert abs(eq-5224.21495225)<1e-9
    forecast=[]
    margingrid=read_csv(OUT/"price-contours.csv")
    for case,m in model["scenarios"].items():
        physical=[]
        for row in m["path"]:
            cash=row["nopat"]+row["da"]-row["delta_nwc"]-row["cash_capex"]-row["lease_net_cash"]
            assert math.isclose(cash,row["fcff"],rel_tol=1e-12)
            assert math.isclose(row["ar"]+row["inventory"]-row["ap"]+row["other_nwc"],row["nwc"],rel_tol=1e-12)
            if row["year"]==2026:
                q=m["q4"]
                cash=(q["core_ebit"]*(1-.13)+q["da_proxy"]-q["capex"]-q["lease_cash"]
                      -q["closing_modeled_wc"]+q["opening_trade_wc"])*49/92
            else:
                assert abs(row["control_new"]+row["control_replacements"]-row["control_units"])<1e-8
                assert abs(row["control_revenue"]+row["hardware_revenue"]+row["residual_revenue"]-row["revenue"])<1e-9
            physical.append(cash/(1+m["wacc"])**row["t"])
        g=m["growth"]; w=m["wacc"]; k=m["roic"]
        assert 0<g<w and g<k
        terminal=m["path"][-1]["nopat"]*(1+g)*(1-g/k)/(w-g)/(1+w)**m["path"][-1]["t"]
        value=(math.fsum(physical)+terminal+eq)*1e6/reception["shares"]
        residual=value-m["price"]
        assert abs(residual)<1e-10
        forecast.append(dict(case=case,independent=value,generated=m["price"],residual=residual,
                             terminal_pv=terminal,explicit_pv=math.fsum(physical)))
    assert reception["shares"]==405557343+427083
    bridge=read_csv(OUT/"value-bridge.csv")
    assert abs(math.fsum(float(x["share_delta"]) for x in bridge)-model["scenarios"]["base"]["price"])<1e-11
    roots=[float(x["residual"]) for x in margingrid if x["root"]]
    assert len(roots)>2 and max(map(abs,roots))<2e-10
    return {
        "method":"Separate PDF lookup and recompute, no Forecast or original extractor imports. Price roots first author's path, independent legacy roots rerun separately.",
        "reviewer":"实施 Agent 的独立公式复核，无独立人审签署",
        "frozen":baseline["base"]["value"],"frozen_control":baseline["control"],"frozen_margin":baseline["margin"],
        "comparison":forecast,"root_cashflows_independently_verified": verify_root_paths(eq,reception["shares"]),
        "price_root_count":len(roots),"maximum_grid_residual":max(map(abs,roots)),
        "no_root_count":len(margingrid)-len(roots),"same_day_difference":model["scenarios"]["base"]["price"]-baseline["base"]["value"],
        "sources":reception["input_sha256"]
    }


def verify_root_paths(eq,shares):
    witnesses=json.loads((OUT/"price-witnesses.json").read_text(encoding="utf-8"))
    residual=[]
    for z in witnesses:
        w,g,roic=z["rates"]
        path=z["path"]
        explicit=math.fsum(r["valued_cash"]/(1+w)**r["t"] for r in path)
        terminal=path[-1]["nopat"]*(1+g)*(1-g/roic)/(w-g)/(1+w)**path[-1]["t"]
        price=(explicit+terminal+eq)*1e6/shares
        assert abs(price-96.20)<2e-10
        residual.append({"inventory_shift":z["inventory_days_shift"],"rebuilt_price":price,"error":price-96.20})
    return residual


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw",action="store_true")
    parser.add_argument("--from-archive",type=Path,help="从获准使用的原件档案根目录补读缺页；逐份验证SHA-256")
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    result=audit()
    if args.raw:
        originals,quarter=verify_raw(args.from_archive)
        result.update(raw_count=len(originals),raw_cells=originals,quarter=quarter)
    if args.write:
        (OUT/"independent-audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("raw_cells","sources")},ensure_ascii=False))
