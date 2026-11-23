"""Check the GitHub reading edition against the frozen research and linked files."""
from hashlib import sha256
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

from forecast import HERE, OUT, rows

BASELINE="aa2ddd8bd06971fde02802b4ffb715d8810a7079"
FROZEN=("data/model.json","data/forecast.csv","data/value-bridge.csv","data/price-contours.csv",
        "data/price-witnesses.json","data/independent-audit.json","assumptions.json","review.pdf")


def original_hash(repo, path):
    result=subprocess.run(["git","show",f"{BASELINE}:{path.relative_to(repo).as_posix()}"],
                          cwd=repo,check=True,capture_output=True)
    return sha256(result.stdout).hexdigest()


def links_in(path):
    text=path.read_text(encoding="utf-8")
    return re.findall(r"\]\(([^)\s]+)\)",text)


def check():
    repo=HERE.parents[3]
    for name in FROZEN:
        path=HERE/name
        assert sha256(path.read_bytes()).hexdigest()==original_hash(repo,path),name
    chapter_links=[f"chapter-{chapter:02d}" for chapter in range(1,10)]
    figures=rows(OUT/"claims-and-figures.csv")
    md=(HERE/"review.md").read_text(encoding="utf-8")
    html=(HERE/"review.html").read_text(encoding="utf-8")
    anchors=[*chapter_links,*(f'figure-{r["key"]}' for r in figures)]
    assert len(anchors)==len(set(anchors))==49
    for anchor in anchors:
        assert md.count(f'<a name="{anchor}"></a>')==1,anchor
    assert all(f"](#{anchor})" in md for anchor in chapter_links)
    assert md.count("```mermaid")==4
    for source in ("README.md","review.md","figures/README.md"):
        file=HERE/source
        for url in links_in(file):
            if url.startswith(("https://","http://")):
                continue
            name,_,target=url.partition("#")
            linked=(file.parent/unquote(name)).resolve() if name else file
            assert linked.exists(),(source,url)
            if target and (linked==HERE/"review.md"):
                assert target in anchors,(source,url)
    images=[]
    for index,row in enumerate(figures,1):
        key=row["key"]
        assert row["figure"]==f"图表 {index:02d}"
        assert row["markdown_anchor"]==f"review.md#figure-{key}"
        assert f'id="figure-{key}"' in html
        for name in row["data_sources"].split("；"):
            assert (HERE/name).is_file(),name
        if file:=row["figure_file"]:
            assert (HERE/file).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),file
            assert f'src="{file}"' in html and f']({file})' in md
            images.append(file)
            if row["mermaid_source"]:
                assert (HERE/row["mermaid_source"]).is_file()
    assert len(images)==len(set(images))==14
    print("49 anchors, 40 original exhibits, 14 images, 4 Mermaid blocks, 8 unchanged research/PDF files")


if __name__=="__main__":
    check()
