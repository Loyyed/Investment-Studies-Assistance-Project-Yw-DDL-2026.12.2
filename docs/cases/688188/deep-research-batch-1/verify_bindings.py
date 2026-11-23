"""查询当前柏楚发行人的有效绑定。可在有授权档案时恢复账本依赖。"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from extract_history import ROOT, COMPANY, HERE, csv_write

sys.path[:0]=[str(ROOT/"shared/runtime"),str(ROOT/"app")]
from companybench import core
from source_compat import enable


def run(archive=None):
    enable(core,ROOT)
    store=core.ReviewStore(COMPANY)
    manifest=json.loads((COMPANY/"sources/manifest.json").read_text(encoding="utf-8"))["sources"]
    ledger=json.loads((COMPANY/"evidence/ledger.json").read_text(encoding="utf-8"))
    ids={s["source_id"] for r in ledger["records"].values() for s in r.get("sources",[])}
    sources={s["id"]:s for s in manifest if s["id"] in ids}
    if archive:
        for s in sources.values():
            destination=COMPANY/s["path"]
            upstream=archive/COMPANY.relative_to(ROOT)/s["path"]
            if not destination.exists() and upstream.is_file():
                data=upstream.read_bytes()
                if sha256(data).hexdigest()==s["sha256"]:
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_bytes(data)
    facts=store.facts()
    rows=[]
    for fact in sorted(facts,key=lambda x:x["id"]):
        for source in fact["sources"]:
            info=sources.get(source["source_id"])
            rows.append(dict(id=fact["id"],value=fact.get("value"),state=fact["effective_state"],
                             source=source["source_id"],location=source["location"],
                             sha256=info["sha256"] if info else None,binding=fact.get("binding"),
                             event=fact.get("confirmation_event"),actor=fact.get("verifier"),
                             note="运行时事实状态，按当前机原件重查"))
    return facts,rows,hasattr(store,"change_facts")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--from-archive",type=Path)
    p.add_argument("--write",action="store_true")
    a=p.parse_args()
    facts,rows,has=run(a.from_archive)
    if a.write:
        assert any(r["id"]=="B07-A01" and r["value"]=="2195632312.92" for r in rows)
        csv_write(HERE,"review-bindings.csv",rows)
    print(f"柏楚发行人 facts()={len(facts)}，change_facts()={has}")
