"""第三人静态复跑，检查离线文件、冻结指纹、现金和现价节点。"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from collections import Counter
from hashlib import sha256
from decimal import Decimal as D
import csv
import json

root = Path(__file__).resolve().parent.parent


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        self.urls.extend(attrs[k] for k in ("href", "src") if k in attrs)


def read_csv(name):
    with (root / "data" / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return sha256((root / path).read_bytes()).hexdigest()


def main():
    scan = Scan()
    scan.feed((root / "index.html").read_text(encoding="utf-8"))
    missing = []
    local_count = 0
    for url in scan.urls:
        parts = urlsplit(url)
        if parts.scheme:
            continue
        local_count += 1
        if parts.path and not (root / unquote(parts.path)).is_file():
            missing.append(url)
        elif not parts.path and parts.fragment and parts.fragment not in scan.ids:
            missing.append(url)
    duplicates = [key for key, number in Counter(scan.ids).items() if number > 1]
    meta = json.loads((root / "src" / "versions.json").read_text(encoding="utf-8"))
    contours = read_csv("price-contours.csv")
    priced = [abs(D(row["reprice"]) - D("96.20")) for row in contours if row["root"]]
    deltas = {}
    for row in read_csv("bundle-cash-thresholds.csv"):
        days = row["inventory_days"], row["ar_days"]
        if row["gross_margin"] != "0.5" or row["service_scenario"] != "5" or days not in {("110","45"),("150","65")}:
            continue
        def q(key):
            return D(row[key])
        sales, cost = q("net_sales"), q("cost")
        capital = (cost * (q("inventory_days") - q("ap_days")) + sales * q("ar_days")) / D(365)
        pretax = sales - cost - q("installation") - q("control_allowance") - q("service_scenario")
        actual = pretax * (1 - q("cash_tax")) - q("gross_capex") - capital
        assert abs(actual - q("first_cohort_cash")) < D("1e-12")
        deltas["/".join(days)] = str(actual)
    assert len(deltas) == 2 and len(priced) == 15 and len(contours) - len(priced) == 6
    assert sha("data/model.json") == meta["model_sha256"] and sha("original/report.md") == meta["report_sha256"]
    result = {
        "本地静态链接": local_count, "静态锚点": len(scan.ids), "缺链接": missing, "重复锚点": duplicates,
        "同价根最大残差": str(max(priced)), "两格独立十进制复算": deltas,
        "HTML SHA-256": sha("index.html"), "模型 SHA-256": sha("data/model.json")
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if missing or duplicates:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
