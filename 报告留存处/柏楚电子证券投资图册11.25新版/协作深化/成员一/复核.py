"""回到柏楚电子年报复核成员一的来源绑定和销量组间比。"""

import json
import re
import sys
from argparse import ArgumentParser
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

PUBLIC_PDFS = {
    "prospectus": (
        "宏石激光_招股书注册稿_2023-10-12.pdf",
        "b0ef9563516738d0dcfab6e1990406f01ae5a688e530772f2af187073945df44",
    ),
    "reply": (
        "宏石激光_深交所问询回复.pdf",
        "178485fdb5b598ba1f1e9b7f3b746d07ff1bf38bd54b0771bb394f3d0709cf8d",
    ),
    "manual": (
        "柏楚_FSCUT8000装机手册_V1.6.pdf",
        "49fc4dd3c46163e698d3d315d50047af2717ee0bed28f25796f3180b4b05cedc",
    ),
}


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


def open_public_pdf(folder, document):
    filename, fingerprint = PUBLIC_PDFS[document]
    path = folder / filename
    if not path.is_file():
        raise SystemExit(f"缺少公开补证原件 {path}。来源见《证据与改判》。")
    payload = path.read_bytes()
    if sha256(payload).hexdigest() != fingerprint:
        raise SystemExit(f"公开补证原件的 SHA-256 不匹配 {path}")
    return pymupdf.open(stream=payload, filetype="pdf")


def pdf_row(document, page_number, label):
    matching_rows = [
        line
        for line in document[page_number - 1].get_text(sort=True).splitlines()
        if label in line
    ]
    if len(matching_rows) != 1:
        raise SystemExit(f"PDF 物理第 {page_number} 页无法唯一定位 {label}")
    return matching_rows[0]


def decimal_fields(row):
    return [Decimal(cell.replace(",", "")) for cell in re.findall(r"\d[\d,]*\.\d{2}", row)]


def verify_public_evidence(member):
    originals = member / "公开补证原件"
    with open_public_pdf(originals, "prospectus") as prospectus:
        supplier_cells = decimal_fields(pdf_row(prospectus, 160, "系统控制类"))
        # p165 的项目名跨行，按已登记原格定位，同一行前四个小数为各期采购额。
        category_totals = decimal_fields(pdf_row(prospectus, 165, "4,388.51"))[:4]
        system_total_h1 = decimal_fields(pdf_row(prospectus, 156, "3,237.16"))[0]

    periods = ("2023 年上半年", "2022 年", "2021 年", "2020 年")
    for period, amount, reported, total in zip(
        periods, supplier_cells[::2], supplier_cells[1::2], category_totals, strict=True
    ):
        calculated = display(amount / total * 100)
        if calculated != reported:
            raise SystemExit(f"{period} 系统控制类采购占比复算与 p160 不一致。")
        print(f"宏石 {period} 系统控制类 {amount:,} / {total:,} = {calculated}%")

    with open_public_pdf(originals, "reply") as reply:
        cells = pdf_row(reply, 96, "1,300.46").split()
        if cells[0] != "柏楚电子" or cells[4:7] != ["-", "-", "-"]:
            raise SystemExit("问询回复 p96 的柏楚供应商行或 2022 年横线与记录不一致。")
        amount, reported, *_ = decimal_fields(" ".join(cells[1:]))
        calculated = display(amount / system_total_h1 * 100)
        if calculated != reported:
            raise SystemExit("宏石 2023 年上半年加工控制系统采购占比复算与 p96 不一致。")
        print(f"宏石 2023 年上半年加工控制系统 {amount:,} / {system_total_h1:,} = {calculated}%")
        print("宏石问询回复 p96 的 2022 年柏楚采购栏为横线。")

    with open_public_pdf(originals, "manual") as manual:
        for page_number, configuration in (
            (5, "8000A系统（搭配BLT切割头使用）"),
            (6, "8000A系统（搭配其他品牌切割头使用）"),
        ):
            page = re.sub(r"\s+", "", manual[page_number - 1].get_text())
            if configuration not in page:
                raise SystemExit(f"装机手册物理第 {page_number} 页找不到登记的配置。")
    print("三份公开原件的指纹、采购原格及 8000A 两种装机配置通过检查。")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--public-evidence", action="store_true", help="同时复核三份公开补证原件")
    args = parser.parse_args()

    member = Path(__file__).resolve().parent
    atlas = member.parents[1]
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
    if args.public_evidence:
        verify_public_evidence(member)


if __name__ == "__main__":
    main()
