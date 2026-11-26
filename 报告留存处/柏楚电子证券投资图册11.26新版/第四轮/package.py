"""Create the self-contained offline atlas bundle and verify its entries."""
from pathlib import Path
import csv,json,zipfile,hashlib,sys,tempfile
HERE=Path(__file__).resolve().parent;STAGE=HERE.parent
report=STAGE.parent/"柏楚电子证券投资分析报告11.26新版.md"
dest=STAGE/"柏楚电子证券投资图册11.26新版_离线包.zip"
exclude={"第三轮重组前入口.md","离线包回执.json"}
with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
 z.write(report,report.name)
 for f in sorted(STAGE.rglob("*")):
  if not f.is_file() or f==dest or f.suffix==".zip" or f.name in exclude or "__pycache__" in f.parts:continue
  z.write(f,STAGE.name+"/"+f.relative_to(STAGE).as_posix())
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None
 names=z.namelist();assert len([n for n in names if "/年报原件/" in n and n.endswith(".pdf")])==7
receipt=dict(file=dest.name,size=dest.stat().st_size,entries=len(names),sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
(HERE/"离线包回执.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt,ensure_ascii=False))
