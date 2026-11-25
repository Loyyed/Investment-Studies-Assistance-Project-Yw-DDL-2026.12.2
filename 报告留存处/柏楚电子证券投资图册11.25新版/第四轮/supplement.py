import sys,csv,json
from pathlib import Path
from hashlib import sha256
import pymupdf
p=Path(sys.argv[1]);d=Path(sys.argv[2])
idx=list(csv.DictReader((p/'年报索引.csv').open(encoding="utf-8-sig")))
out=[]
for m in idx:
 f=Path(m["本地原件"]);f=f if f.exists() else d/"年报原件"/m["文件名"];assert sha256(f.read_bytes()).hexdigest()==m["SHA256"]
 if m["报告年度"]!="2025":continue
 doc=pymupdf.open(f)
 for pg,anchor,claim in [(167,"10%","母公司所得税与软件增值税政策"),(213,"114,106,284.20","折扣与货款分别进入营运资本"),
 (216,"1,550,646.72","一年内租赁净负债"),(217,"14,350,570.43","未终止确认票据按融资义务条件扣除"),(219,"288,729,927.00","股份总数而非从股本推断"),(224,"121,902,550.38","其他收益及投资收益性质"),
 (225,"44,636,341.17","金融公允价值及资产减值"),(231,"4,600.00","冻结ETC保证金剔除")]:
  text=doc[pg-1].get_text(sort=True);assert anchor in text
  out.append(dict(year=2025,page=pg,anchor=anchor,claim=claim,unit="人民币元或税率，按原表",scope="合并；p167母公司及子公司税率分列",available=m["可获日期"],sha=m["SHA256"],file=m["文件名"]))
with (d/'补充来源.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,out[0].keys());w.writeheader();w.writerows(out)
