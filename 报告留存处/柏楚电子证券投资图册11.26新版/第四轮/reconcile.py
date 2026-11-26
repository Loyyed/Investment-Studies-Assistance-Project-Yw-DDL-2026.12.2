import csv,sys
from pathlib import Path
p=Path(sys.argv[1]);out=Path(sys.argv[2])
r=list(csv.DictReader((p/'清洗底表.csv').open(encoding="utf-8-sig")))
a=[x for x in r if x["报告年度"]=="2025" and x["表名"]=="合并利润表" and x["列角色"]=="本期"]
def f(prefix):
 z=next(x for x in a if x["原行"].startswith(prefix));return float(z["标准值"])/1e6,z["单元ID"],z["PDF物理页"]
core=next(__import__('json').loads((out/'模型.json').read_text(encoding='utf-8'))['history'][-1][k] for k in ['core_ebit'])
items=[dict(item="核心EBIT",amount=core,formula="收入−成本−税附−销管研＋信用减值",cell="见输入原格",page="125–126")]
s=core
for prefix,sign in [("加：其他收益",1),("财务费用",-1),("投资收益",1),("公允价值变动收益",1),("资产减值损失",1),("资产处置收益",1)]:
 v,i,pg=f(prefix);s+=v*sign;items.append(dict(item=prefix,amount=v*sign,formula="按原表符号" if sign==1 else "减财务费用原符号",cell=i,page=pg))
oper,_,_=f("三、营业利润");assert abs(s-oper)<1e-7,(s,oper)
items.append(dict(item="营业利润",amount=oper,formula="上项合计",cell=f("三、营业利润")[1],page="126"))
for prefix,sign in [("加：营业外收入",1),("减：营业外支出",-1),("减：所得税费用",-1)]:
 v,i,pg=f(prefix);s+=v*sign;items.append(dict(item=prefix,amount=v*sign,formula="税及支出扣除",cell=i,page=pg))
net,_,_=f("五、净利润");assert abs(s-net)<1e-7
items.append(dict(item="合并净利润",amount=net,formula="上项合计",cell=f("五、净利润")[1],page="126"))
minor,i,pg=f("2.少数股东损益");items.append(dict(item="少数损益扣除",amount=-minor,formula="合并净利减少数损益",cell=i,page=pg))
items.append(dict(item="归母净利润",amount=net-minor,formula="上项合计",cell="B07-A03原Fact与p126原格",page="126"))
with (out/'历史利润桥.csv').open('w',encoding='utf-8-sig',newline='') as fh:
 w=csv.DictWriter(fh,items[0].keys());w.writeheader();w.writerows(items)
print("历史利润桥闭合")
