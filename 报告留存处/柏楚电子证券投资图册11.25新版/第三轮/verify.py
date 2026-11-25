"""Verify the third-round source bindings and chart calculations."""
import csv,json,re,sys
from fractions import Fraction as F
from pathlib import Path
from hashlib import sha256
from pypdf import PdfReader
HERE=Path(__file__).resolve().parent
def rows(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
for f,h in json.loads((HERE/"输入指纹.json").read_text(encoding="utf-8")).items():
    assert sha256((HERE/f).read_bytes()).hexdigest()==h,f
raw=rows(HERE/"合同负债补充原格.csv")
liab={(int(r["数据年度"]),r["原行"]):F(r["标准值"]) for r in raw}
for y in (2024,2025):assert liab[y,"货款"]+liab[y,"预提销售折扣"]==liab[y,"合计"]
index=rows(HERE.parent/"第一轮/年报索引.csv")
source=next(r for r in index if r["报告年度"]=="2025")
p=Path(source["本地原件"])
assert sha256(p.read_bytes()).hexdigest()==source["SHA256"]
text=re.sub(r"\s+","",PdfReader(p).pages[212].extract_text(extraction_mode="layout"))
assert all(r["原字面值"] in text for r in raw)
a=liab[2025,"预提销售折扣"]/liab[2025,"合计"]*100
b=(liab[2025,"预提销售折扣"]-liab[2024,"预提销售折扣"])/(liab[2025,"合计"]-liab[2024,"合计"])*100
assert round(float(a),2)==86.19 and round(float(b),2)==63.50
bridge=rows(HERE/"图表取数.csv")
assert bridge==rows(HERE.parent/"第二轮/经营桥明细.csv")
v={(r["计算段"],r["数据期"],r["项目"]):F(r["精确结果"]) for r in bridge}
for year in (2022,2025):
    y=f"{year-1}→{year}"
    subtotal=sum(v["B09",y,k] for k in ("合并净利润变化","存货调节变动","应收调节变动","应付调节变动","其他间接调节变化"))
    assert abs(subtotal-v["B09",y,"经营现金流变化"])<F("1e-15")
assert abs(v["B04","2024→2025","主营毛利率组合权重贡献"]+v["B04","2024→2025","主营毛利率组内贡献"]-
           v["B04","2024→2025","主营毛利率变化"])<F("1e-15")
cells={r["单元ID"]:r for r in rows(HERE/"原格索引.csv")}
assert all(k in cells for r in bridge for k in r["第一轮底表单元"].split("；") if k)
html=(HERE.parent/"index.html").read_text(encoding="utf-8")
assert all(f'id="ch{i:02}"' in html for i in range(1,9))
assert "{{" not in html
assert not re.search(r'<(?:script|link)[^>]*(?:src|href)="https?://',html)
for f in sorted((HERE/"chapters").glob("*.md")):
    t=f.read_text(encoding="utf-8")
    assert "**" in t and "[E" in t
summary={"输入指纹":4,"合同负债原格":len(raw),"折扣期末占比":round(float(a),6),
"折扣增量占比":round(float(b),6),"章节":8,"图表变体":len(json.loads((HERE/"图表映射.json").read_text(encoding="utf-8"))),
"图表计算":len(bridge),"原格":len(cells),"现金桥与毛利分解":"Fraction复算通过"}
(HERE/"数据验收.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
