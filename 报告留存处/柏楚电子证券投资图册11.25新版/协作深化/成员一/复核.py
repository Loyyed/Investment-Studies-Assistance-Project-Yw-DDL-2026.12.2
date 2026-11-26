"""回到柏楚电子年报复核成员一的来源绑定和销量组间比。"""

import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import pymupdf


ANNUAL_SOURCES = {
    2019: "688188-6280a199ff0f4384",
    2020: "688188-7ccffae9be109cca",
    2021: "688188-bf8b8265bc605711",
    2022: "688188-be6a5c9bc7b468ca",
    2023: "688188-d931e02dd1c67f13",
    2024: "688188-4daf701c6095d460",
    2025: "688188-a343f0dc3c27d114",
}

SALES_PAGES = {2024: 26, 2025: 29}
EXPECTED_SALES = {2024: (60993, 35118), 2025: (65064, 56824)}


def read_sales(payload, page_number):
    with pymupdf.open(stream=payload, filetype="pdf") as annual:
        page = annual[page_number - 1].get_text(sort=True)
    table = page.partition("产销量情况分析表")[2]
    sales = []
    for product in ("控制系统", "智能硬件"):
        # 单位后依次是生产量、销售量和库存量。只读第二个数。
        pattern = rf"{product}\s+套\s+[\d,]+\.00\s+([\d,]+)\.00"
        match = re.search(pattern, table)
        if match is None:
            raise SystemExit(f"PDF 第{page_number}页找不到{product}行的销售量。")
        sales.append(int(match.group(1).replace(",", "")))
    return tuple(sales)


def display(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def main():
    atlas = Path(__file__).resolve().parents[2]
    repo = atlas.parents[1]
    project = repo / "companies" / "688188_柏楚电子"
    sys.path.insert(0, str(repo / "shared" / "runtime"))
    from companybench.core import ReviewStore

    store = ReviewStore(project)
    if not store.history_valid():
        raise SystemExit("柏楚电子 ReviewStore 历史校验未通过。")
    manifest = {source["id"]: source for source in store.source_rows()}
    archive_path = atlas / f"{atlas.name}_离线包.zip"
    receipt_path = atlas / "第四轮" / "离线包回执.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if sha256(archive_path.read_bytes()).hexdigest() != receipt["sha256"]:
        raise SystemExit("11.25 离线包的 SHA-256 与发布回执不一致。")

    ratios = {}
    with ZipFile(archive_path) as archive:
        for year, source_id in ANNUAL_SOURCES.items():
            source = manifest[source_id]
            raw_path = project / source["path"]
            raw = raw_path.read_bytes()
            archived = archive.read(f"{atlas.name}/第四轮/年报原件/{raw_path.name}")
            if sha256(raw).hexdigest() != source["sha256"] or raw != archived:
                raise SystemExit(f"{year} 年报原件、清单和离线包的版本不一致。")
            print(f"{year} 年报 {source_id} {source['sha256']}")
            if year in SALES_PAGES:
                page = SALES_PAGES[year]
                control, hardware = read_sales(raw, page)
                if (control, hardware) != EXPECTED_SALES[year]:
                    raise SystemExit(f"{year} 年报第{page}页销量与交审原格不一致。")
                ratios[year] = Decimal(hardware) / Decimal(control) * 100
                print(f"  p{page} 销售量 {hardware:,} / {control:,} = {display(ratios[year])}%")

    facts = store.facts()
    print(f"ReviewStore 当前有效 Fact {len(facts)} 条")
    print(f"2025 较 2024 的组间销量比相差 {display(ratios[2025] - ratios[2024])} 个百分点")


if __name__ == "__main__":
    main()
