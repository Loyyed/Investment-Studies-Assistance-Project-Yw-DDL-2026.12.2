"""Replace local PDF annotation targets with the published issue branch's evidence URLs."""
import argparse
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject

HERE=Path(__file__).resolve().parent
BRANCH="codex/688188-deep-research-batch-2"
PROJECT="https://github.com/Loyyed/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chromium_pdf",type=Path)
    parser.add_argument("--output",type=Path,default=HERE/"review.pdf")
    args=parser.parse_args()
    assert args.chromium_pdf.resolve()!=args.output.resolve()
    reader=PdfReader(args.chromium_pdf)
    assert len(reader.pages)==40
    writer=PdfWriter(clone_from=reader)
    fixed=0
    for page in writer.pages:
        for link in page.get("/Annots",[]):
            action=link.get_object().get("/A")
            if not action or "/URI" not in action:
                continue
            url=action["/URI"]
            if not url.startswith("file:"):
                continue
            match=re.search(r"/(docs/cases/688188/[^?#]+)(#[^\s]+)?$",url)
            if not match:
                raise ValueError(f"Unrecognized report link: {url}")
            action[NameObject("/URI")]=TextStringObject(
                f"{PROJECT}/blob/{BRANCH}/{match[1]}{match[2] or ''}")
            fixed+=1
    assert fixed>40
    writer.add_metadata({"/Title":"柏楚电子 · 证券投资分析审阅稿","/Subject":"688188.SH 研究审阅"})
    with args.output.open("wb") as stream:
        writer.write(stream)
    print(f"{len(writer.pages)} pages; {fixed} PDF evidence links made portable")


if __name__=="__main__":
    main()
