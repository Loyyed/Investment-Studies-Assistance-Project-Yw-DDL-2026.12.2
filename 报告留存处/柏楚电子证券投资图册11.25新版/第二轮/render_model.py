"""Render the round-two device transaction and four operating links."""
from pathlib import Path
import csv
from decimal import Decimal

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
font = FontProperties(family=["Microsoft YaHei","sans-serif"])
with (HERE/"经营桥明细.csv").open(encoding="utf-8-sig",newline="") as fh:
    values={(r["计算段"],r["数据期"],r["项目"]):Decimal(r["精确结果"]) for r in csv.DictReader(fh)}

def revenue_magnitude(code,period,label,d=1):
    return f"{values[code,period,label]/d:.2f}"

margin = f'{100*(1-values["B03","2024→2025","本期主营成本"]/values["B03","2024→2025","本期主营收入"]):.2f}'
cfo = revenue_magnitude("B01","2025","经营现金流净额",10**8)
capex = revenue_magnitude("B01","2025","购建长期资产付现",10**8)
cash = revenue_magnitude("B01","2025","简化现金余量",10**8)
ink, muted = "#11283a", "#345066"
fig, ax = plt.subplots(figsize=(12.8,7.3),dpi=160)
fig.patch.set_facecolor("#f7fafb")
ax.set(xlim=(0,12.8),ylim=(0,7.3))
ax.set_position((0,0,1,1))
ax.axis("off")

def words(x,y,s,size=12,color=ink):
    ax.text(x,y,s,fontsize=size,fontproperties=font,color=color,va="center",ha="left",linespacing=1.45)

def card(x,y,w,h,title,detail,fill="#eaf3f5",line="#9ab7c3"):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.14",
                                facecolor=fill,edgecolor=line,linewidth=1.2))
    words(x+.18,y+h-.30,title,13)
    words(x+.18,y+h-.83,detail,10.4,muted)

def arrow(a,b,dashed=False):
    ax.annotate("", xy=b,xytext=a,arrowprops=dict(arrowstyle="->",color="#467383",
                lw=1.5,linestyle="--" if dashed else "-",shrinkA=0,shrinkB=0))

words(.45,6.87,"从一台激光切割设备看柏楚怎样赚钱",24)
words(.48,6.38,"设备、合同和财务流转  ·  2019–2025 年发行人年报",11,muted)

card(.48,4.63,3.82,1.28,"柏楚供货与服务","控制系统、软件、切割头及配件\n组装测试、售后维修、现场支持")
card(4.61,4.63,3.58,1.28,"设备制造商采购","签收及合同约定的验收\n整机集成由具体项目决定")
card(8.50,4.63,3.82,1.28,"加工企业使用","机床运行平面、管材或三维工艺\n具体终端合同责任待证")
arrow((4.31,5.24),(4.59,5.24))
arrow((8.20,5.24),(8.48,5.24),True)
ax.annotate("",xy=(6.7,4.58),xytext=(10.4,4.56),arrowprops=dict(arrowstyle="->",color="#467383",lw=1.3,
             linestyle="--",connectionstyle="arc3,rad=-0.17"))
words(6.82,4.10,"工艺与接口复用可能影响后续采购",10,muted)
ax.plot([5.40,5.40,1.96],[4.58,3.72,3.72],color="#467383",lw=1.5)
arrow((1.96,3.72),(1.96,3.40))

words(.48,3.75,"经营四环",14)
xpos=(.48,3.48,6.48,9.48)
items=[
    ("① 收入","按控制权转移确认\n其他软件交付或激活\n年度折扣调整实现收入"),
    ("② 成本与利润",f"材料、人工、制造\n保证类质保与经营费用\n2025 主营毛利率 {margin}%"),
    ("③ 资本投入",f"应收与存货占用资源\n设备投入支撑交付\n2025 购建付现 {capex} 亿元"),
    ("④ 现金回流",f"2025 年 CFO {cfo} 亿元\n减购建付现后\n简化现金余量 {cash} 亿元"),
]
for x,(title,detail) in zip(xpos,items):
    card(x,1.97,2.82,1.40,title,detail,fill="#edf4ed",line="#9eb8a1")
for x,x2 in zip(xpos,xpos[1:]):
    arrow((x+2.84,2.56),(x2-.02,2.56))

words(.48,1.42,"虚线表示设备使用链或待验证的复用机制。直销口径覆盖的是柏楚与合同客户的交易。",10.4,muted)
words(.48,1.02,"原页：2025 年报 p6、p12–18、p27–29、p119、p121–131、p160–162；2024 年报 p153。",10,muted)
words(.48,.64,"第二轮证据定位：P01–P12、P16–P17；底表与复算：B01、B02、B04、B08–B11。",10,muted)
fig.savefig(HERE/"商业模式图.png",facecolor=fig.get_facecolor())
