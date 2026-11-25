"""Rebuild round-two quantitative bridges from the nine approved round-one files."""
from argparse import ArgumentParser
from collections import defaultdict
import csv
from dataclasses import dataclass
from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
FIRST = HERE.parent / "第一轮"
IS, BS, CF = "合并利润表", "合并资产负债表", "合并现金流量表"
NOTE = "营业收入和营业成本附注"
SUP = "现金流量表补充资料"
MDA = "管理层讨论与分析·"
PRODUCT, REGION, GROUP = (MDA + "主营业务分" + k + "情况" for k in ("产品","地区","销售模式"))
VOLUME = MDA + "产销量情况分析表"
COST = MDA + "成本分析表·分行业情况"
IS_MATCH = {
    "收入":r"^一、营业总收入$", "成本":r"^其中：营业成本$",
    "税金及附加":r"^税金及附加$", "销售":r"^销售费用$", "管理":r"^管理费用$",
    "研发":r"^研发费用$", "财务":r"^财务费用$", "营业利润":r"^三、营业利润",
    "利润总额":r"^四、利润总额", "所得税":r"^减：所得税费用$", "少数股东损益":r"^2[.．]少数股东损益",
    "净利润":r"^五、净利润", "归母净利润":r"归属[于与]?母公司(?:股东|所有者)的?净利润",
}
CF_MATCH = {
    "销售收现":"销售商品、提供劳务收到的现金", "税费返还":"收到的税费返还",
    "采购付现":"购买商品、接受劳务支付的现金", "职工付现":"支付给职工及为职工支付的现金",
    "税费付现":"支付的各项税费", "CFO":"经营活动产生的现金流量净额",
    "购建付现":"购建固定资产、无形资产和其他长期资产支付的现金",
}
ADJUST = {"存货":"^存货的减少", "应收":"^经营性应收项目的减少", "应付":"^经营性应付项目的增加"}
PRODUCTS = ("平面解决方案","管材解决方案","三维解决方案","其他")
COSTS = ("原材料","人工成本","制造费用","运费","实施成本")

def read_csv(f):
    with f.open(encoding="utf-8-sig",newline="") as fh:
        return list(csv.DictReader(fh))

def write_csv(f,rows):
    with f.open("w",encoding="utf-8-sig",newline="") as fh:
        writer=csv.DictWriter(fh,rows[0].keys(),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

@dataclass(frozen=True)
class Val:
    n: D
    ids: tuple[str,...]
    def result(self,n,other):
        return Val(n,tuple(dict.fromkeys(self.ids+other.ids)))
    def __add__(self,other):
        return self.result(self.n+other.n,other)
    def __sub__(self,other):
        return self.result(self.n-other.n,other)
    def __mul__(self,other):
        return self.result(self.n*other.n,other)
    def __truediv__(self,other):
        return self.result(self.n/other.n,other)
    def __neg__(self):
        return Val(-self.n,self.ids)

def const(n):
    return Val(D(n),())

def total(values):
    return sum(values,const(0))

def rate(n,d):
    assert d.n>0
    return n/d*const(100)

def yoy(n,d):
    return rate(n-d,d)

def same(x,y):
    assert abs(x.n-y.n)<D("1e-16"),(x,y)

class Data:
    def __init__(self,first):
        pin=json.loads((HERE/"第一轮输入指纹.json").read_text(encoding="utf-8"))
        for f,expected in pin.items():
            assert sha256((first/f).read_bytes()).hexdigest()==expected,f
        self.rows=read_csv(first/"清洗底表.csv")
        self.by_id={r["单元ID"]:r for r in self.rows}
        self.sources={int(r["报告年度"]):r for r in read_csv(first/"年报索引.csv")}
        self.group=defaultdict(list)
        for r in self.rows:
            key=(int(r["报告年度"]),r["表名"],r["列角色"])
            self.group[key].append(r)
        self.checks=read_csv(first/"勾稽差额.csv")

    def raw(self,y,t,name,role="本期",col=None,pattern=False):
        rows=[r for r in self.group[y,t,role] if (bool(re.search(name,r["原行"])) if pattern else r["原行"]==name)
              and (col is None or r["原列"]==col)]
        numeric=[r for r in rows if r["标准值"]!=""]
        assert len(numeric)<=1,(y,t,name,role,col,len(numeric))
        if numeric:
            return numeric[0]
        assert len(rows)<=1,(y,t,name,role,col,len(rows))
        return rows[0] if rows else None

    def get(self,y,t,name,role="本期",col=None,pattern=False):
        r=self.raw(y,t,name,role,col,pattern)
        assert r and r["标准值"]!="",(y,t,name,role,col,r)
        return Val(D(r["标准值"]),(r["单元ID"],))

    def is_(self,y,k,pr=False):
        return self.get(y,IS,IS_MATCH[k],"比较" if pr else "本期",pattern=True)

    def cf(self,y,k,pr=False):
        return self.get(y,CF,CF_MATCH[k],"比较" if pr else "本期")

    def bs(self,y,k):
        return self.get(y,BS,k)

    def adj(self,y,k,pr=False):
        return self.get(y,SUP,ADJUST[k],"比较" if pr else "本期",pattern=True)

    def m(self,y,k,pr=False):
        return self.get(y,NOTE,"主营业务","比较" if pr else "本期",
                        ("上期" if pr else "本期")+"发生额·"+k)

    def cost(self,y,k,pr=False):
        return self.get(y,COST,"工业自动化控制｜"+k,"比较" if pr else "本期",
                        "上年同期金额" if pr else "本期金额")

    def labels(self,y,t,col):
        rows=[r for r in self.group[y,t,"本期"] if r["原列"]==col]
        return list(dict.fromkeys(r["原行"] for r in rows if r["原行"] not in ("合计","总计")))

    def vol(self,y,k,c):
        return self.get(y,VOLUME,k,col=c)

class Output:
    def __init__(self,data):
        self.data=data
        self.rows=[]
        self.body=["# 收入、成本、费用与现金桥",
                   "金额单位为人民币百万元，比例为 %，变动贡献为百分点。2022 年的跨年数字是列报合并变化。精确结果、公式、适用窗口和第一轮单元 ID 在[计算明细](经营桥明细.csv)。各数据段的编号可用于检索。"]
    def add(self,code,period,key,value,formula,unit="人民币元",scope=""):
        self.rows.append(dict(计算段=code,数据期=period,项目=key,精确结果=str(value.n),单位=unit,公式=formula,
          第一轮底表单元="；".join(value.ids),口径说明=scope))
        return value.n
    def section(self,title,codes,note,headers,rows):
        table = ["| "+" | ".join(headers)+" |", "| "+" | ".join("---" for h in headers)+" |"]
        table.extend("| "+" | ".join(map(str,r))+" |" for r in rows)
        self.body.extend([f"## {title} · {codes}",note,"\n".join(table)])

def fm(x):
    return f"{x/1_000_000:,.2f}"

def fp(x):
    return f"{x:.2f}"

def build(first,out):
    d=Data(first)
    o=Output(d)
    e=o.add
    ys=range(2019,2026)
    overview=[]
    for y in ys:
        f=lambda k:d.is_(y,k)
        c=lambda k:d.cf(y,k)
        # Use each report's own current-year disclosures in the historical view.
        values=[f("收入"),f("成本"),rate(f("收入")-f("成本"),f("收入")),f("营业利润"),f("净利润"),
                f("归母净利润"),c("CFO"),rate(c("CFO"),f("净利润")),c("购建付现"),
                c("CFO")-c("购建付现"),rate(c("CFO")-c("购建付现"),f("收入"))]
        specs=[
          ("营业收入","原值"),("营业成本","原值"),("毛利率","100×（收入−成本）÷收入","%"),
          ("营业利润","原值"),("合并净利润","原值"),("归母净利润","原值"),("经营现金流净额","原值"),
          ("现金转换率","100×CFO÷合并净利润","%"),("购建长期资产付现","原值"),
          ("简化现金余量","CFO−购建长期资产付现"),("简化现金余量占营收","100×简化现金余量÷合并收入","%")]
        nums=[e("B01",str(y),k,v,fm0,q[0] if q else "人民币元","各年度原列；2023为当年报告原列")
              for (k,fm0,*q),v in zip(specs,values)]
        overview.append([y,*[fp(n) if i in (2,7,10) else fm(n) for i,n in enumerate(nums)]])
    o.section("跨年度经营画像","B01","按每年原报告合并口径。2023 原毛利率用于本表历史查阅。下一表采用 2024 年报重列基数。购建是购建固定资产、无形资产和其他长期资产的现金支出。",
              ["年","收入","成本","毛利率","营业利润","合并净利润","归母净利润","CFO","现金转换率","购建","简化现金余量","余量／收入"],overview)

    windows=(2022,2024,2025)
    labels=[f"{y-1}→{y}" for y in windows]
    amount={}
    for y,period in zip(windows,labels):
        scope={2022:"2022年报同页列报比较，合并范围有变",2024:"2024年报比较列含2023年质保费用重列",2025:"2025年报比较列"}[y]
        beg=lambda k:d.is_(y,k,pr=True)
        end=lambda k:d.is_(y,k)
        delta=lambda k:end(k)-beg(k)
        gp0=beg("收入")-beg("成本")
        gp1=end("收入")-end("成本")
        parts=("税金及附加","销售","管理","研发","财务")
        fees=total(delta(k) for k in parts)
        residue=delta("营业利润")-(gp1-gp0-fees)
        calculations=[
          ("收入变化",delta("收入"),"本年收入−比较收入"),
          ("收入同比",yoy(end("收入"),beg("收入")),"100×Δ收入÷比较收入","%"),
          ("营业成本变化",delta("成本"),"本年营业成本−比较营业成本"),
          ("营业成本同比",yoy(end("成本"),beg("成本")),"100×Δ成本÷比较成本","%"),
          ("毛利额变化",gp1-gp0,"Δ收入−Δ成本"),
          ("比较毛利率",rate(gp0,beg("收入")),"100×比较毛利÷比较收入","%"),
          ("本期毛利率",rate(gp1,end("收入")),"100×本期毛利÷本期收入","%"),
          ("毛利率变化",rate(gp1,end("收入"))-rate(gp0,beg("收入")),"本期毛利率−比较毛利率","百分点"),
          *((k+"变化",delta(k),"本年列报原值−比较列原值") for k in parts),
          ("其他营业利润项目净变动",residue,"Δ营业利润−Δ毛利额＋Δ税金及四项费用"),
          ("营业利润变化",delta("营业利润"),"本年营业利润−比较营业利润"),
          ("营业外收支净变动",delta("利润总额")-delta("营业利润"),"Δ利润总额−Δ营业利润"),
          ("所得税费用变化",delta("所得税"),"本年所得税费用−比较所得税费用"),
          ("合并净利润变化",delta("净利润"),"本年合并净利润−比较合并净利润"),
          ("少数股东损益变化",delta("少数股东损益"),"本年少数股东损益−比较少数股东损益"),
          ("归母净利润变化",delta("归母净利润"),"本年归母净利润−比较归母净利润"),
        ]
        for k,v,f,*q in calculations:
            unit=q[0] if q else "人民币元"
            amount.setdefault(k,[]).append(fp(e("B02",period,k,v,f,unit,scope)) if q else fm(e("B02",period,k,v,f,unit,scope)))
        for k in parts[1:]:
            v=rate(end(k),end("收入"))-rate(beg(k),beg("收入"))
            amount.setdefault(k+"费率变化",[]).append(fp(e("B02",period,k+"费率变化",v,
              "本期费用／收入−比较费用／收入，按百分数","百分点",scope)))
        same(gp1-gp0-fees+residue,delta("营业利润"))
        same(delta("利润总额")-delta("所得税"),delta("净利润"))
        same(delta("净利润")-delta("少数股东损益"),delta("归母净利润"))
    o.section("列报扩张与压力的利润桥","B02",
              "费用行使用费用原符号。毛利变动减税金及各项费用变动，加其他营业项目净变动等于营业利润变动。其他项是差额，含其他收益、投资收益、减值等。",
              ["项目",*labels],[[k,*v] for k,v in amount.items()])

    main_rows=[]
    for y,period in zip(windows,labels):
        a,b=d.m(y,"收入",True),d.m(y,"成本",True)
        r,c=d.m(y,"收入"),d.m(y,"成本")
        disp=lambda k,v,f,u="人民币元":e("B03",period,k,v,f,u,"当年报告附注主营两列")
        main_rows.append([period,fm(disp("主营收入变化",r-a,"本期－上期")),
          fm(disp("主营成本变化",c-b,"本期－上期")),fm(disp("主营毛利变化",(r-c)-(a-b),"Δ主营收入−Δ主营成本")),
          fp(disp("主营毛利率变化",rate(r-c,r)-rate(a-b,a),"本期主营毛利率−比较主营毛利率","百分点"))])
        for k,v in (("比较主营收入",a),("比较主营成本",b),("本期主营收入",r),("本期主营成本",c)):
            disp(k,v,"年报附注原值")
    o.section("适用主营分母","B03",
              "主营附注金额可跨期对读。2022 年比较列位于 2022 年报 p174。2024 年比较列位于 2024 年报 p205，已重列 2023 年保证类质保。2023 分方案比较收入绝对值留缺。",
              ["窗口","主营收入变化","主营成本变化","主营毛利变化","主营毛利率变化（百分点）"],main_rows)

    pr_rows=[]
    mix_parts=[]; internal_parts=[]; growth=[]; profit=[]
    total_r={y:d.m(y,"收入") for y in (2024,2025)}
    total_c={y:d.m(y,"成本") for y in (2024,2025)}
    for label in PRODUCTS:
        v={}
        for y in (2024,2025):
            r=d.get(y,PRODUCT,label,col="营业收入")
            c=d.get(y,PRODUCT,label,col="营业成本")
            gp=r-c
            w=r/total_r[y]
            g=gp/r
            for k,x,f,u in [("收入",r,"原值","人民币元"),("成本",c,"原值","人民币元"),("毛利额",gp,"收入−成本","人民币元"),
                ("主营收入占比",w*const(100),"100×分组收入÷主营收入","%"),
                ("主营毛利占比",rate(gp,total_r[y]-total_c[y]),"100×分组毛利÷主营毛利","%"),
                ("分组毛利率",g*const(100),"100×分组毛利÷分组收入","%")]:
                e("B04",str(y),label+"·"+k,x,f,u,"管理层分场景，附注主营分母")
            v[y]=(r,c,gp,w,g)
        r0,c0,gp0,w0,g0=v[2024]; r1,c1,gp1,w1,g1=v[2025]
        dr,dc,dg=r1-r0,c1-c0,gp1-gp0
        mix=(w1-w0)*(g1+g0)*const(50)
        inside=(g1-g0)*(w1+w0)*const(50)
        mix_parts.append(mix); internal_parts.append(inside); growth.append(dr); profit.append(dg)
        spec=[("收入变化",dr,"本期−上期","人民币元"),("成本变化",dc,"本期−上期","人民币元"),
              ("毛利变化",dg,"Δ分组收入−Δ分组成本","人民币元"),("收入同比",yoy(r1,r0),"100×Δ分组收入÷比较收入","%"),
              ("收入增量占比",rate(dr,total_r[2025]-total_r[2024]),"100×Δ分组收入÷Δ主营收入","%"),
              ("毛利增量占比",rate(dg,(total_r[2025]-total_c[2025])-(total_r[2024]-total_c[2024])),"100×Δ分组毛利÷Δ主营毛利","%"),
              ("组合权重贡献",mix,"100×Δ分组权重×两年平均分组毛利率","百分点"),
              ("组内毛利率贡献",inside,"100×Δ分组毛利率×两年平均分组权重","百分点")]
        for k,x,f,u in spec:e("B04","2024→2025",label+"·"+k,x,f,u,"平面、管材、三维、其他为互斥场景组合")
        pr_rows.append([label,fm(r1.n),fp(w1.n*100),fm(gp1.n),fp(gp1.n/(total_r[2025]-total_c[2025]).n*100),
                        fp(yoy(r1,r0).n),fm(dr.n),fm(dc.n),fm(dg.n),fp(g0.n*100),fp(g1.n*100),fp(mix.n),fp(inside.n)])
    mix=total(mix_parts); inside=total(internal_parts)
    ma0=rate(total_r[2024]-total_c[2024],total_r[2024])
    ma1=rate(total_r[2025]-total_c[2025],total_r[2025])
    same(total(growth),total_r[2025]-total_r[2024])
    same(total(profit),(total_r[2025]-total_c[2025])-(total_r[2024]-total_c[2024]))
    same(mix+inside,ma1-ma0)
    e("B04","2024→2025","主营毛利率组合权重贡献",mix,"Σ组合权重贡献","百分点")
    e("B04","2024→2025","主营毛利率组内贡献",inside,"Σ组内毛利率贡献","百分点")
    e("B04","2024→2025","主营毛利率变化",mix+inside,"组合权重贡献＋组内贡献","百分点")
    o.section("场景利润来源和毛利率桥","B04",
              f"主营毛利率由 {fp(ma0.n)}% 变为 {fp(ma1.n)}%。权重变化贡献 {fp(mix.n)} 个百分点，组内毛利率变化贡献 {fp(inside.n)} 个百分点。中点分解将交互项均摊。各组权重贡献相加后判断组合方向。组内可以同时包含价格、规格、搭配和成本变化。",
              ["分组","25收入","收入占比","25毛利额","毛利额占比","收入同比","Δ收入","Δ成本","Δ毛利","24毛利率","25毛利率","组合权重贡献","组内贡献"],pr_rows)

    pressure=[]
    for label in d.labels(2022,PRODUCT,"营业收入"):
        r=d.get(2022,PRODUCT,label,col="营业收入"); c=d.get(2022,PRODUCT,label,col="营业成本")
        yr=d.get(2022,PRODUCT,label,col="营业收入同比")
        g=rate(r-c,r)
        for k,v,f,u in (("收入",r,"原值","人民币元"),("成本",c,"原值","人民币元"),
                         ("收入同比",yr,"原表披露同比","%"),("毛利率",g,"100×分组毛利÷分组收入","%")):
            e("B05","2022",label+"·"+k,v,f,u,"2022旧产品组；同比直接引用披露值")
        pressure.append([label,fm(r.n),fm(c.n),fp(g.n),fp(yr.n)])
    o.section("2022 旧产品压力分布","B05",
              "2022 年报 p25–26。分项同比是管理层表原披露。同年各旧产品可以比较，2021 管理层表覆盖营业总额，2021/2022 分项收入绝对可比基数按第一轮处理。",
              ["旧产品","收入","成本","毛利率","披露的收入同比"],pressure)

    cost_rows=[]
    for k in COSTS:
        nums=[]
        for y in windows:
            pr=d.cost(y,k,True)
            current=d.raw(y,COST,"工业自动化控制｜"+k,col="本期金额")
            if not current or current["标准值"]=="":
                nums.append("本期原格空白")
                continue
            now=d.cost(y,k)
            v=e("B06",f"{y-1}→{y}",k+"变动",now-pr,"成本分析表本期−同表上年同期","人民币元",
                "主营工业自动化控制；比较成本性质按本年报告列")
            nums.append(fm(v))
        cost_rows.append([k,*nums])
    for y in windows:
        for pr in (False,True):
            used=[d.raw(y,COST,"工业自动化控制｜"+k,"比较" if pr else "本期",
                        "上年同期金额" if pr else "本期金额") for k in COSTS]
            subtotal=total(Val(D(r["标准值"]),(r["单元ID"],)) for r in used if r and r["标准值"]!="")
            same(subtotal,d.cost(y,"合计",pr))
    o.section("同报告成本性质变动","B06",
              "原材料、人工、制造等是已结转的成本分类。2025 表比较列把 2024 年 570.16 万元从制造费用挪至原材料。2025 实施成本本期格空白，按原表保留，已列数字与合计闭合。各成本项使用本表自己的比较列。",
              ["成本构成",*labels],cost_rows)

    region_rows=[]
    region_growth=[]
    for label in d.labels(2025,REGION,"营业收入"):
        r=d.get(2025,REGION,label,col="营业收入")
        c=d.get(2025,REGION,label,col="营业成本")
        prv=d.get(2024,REGION,label,col="营业收入")
        delta=r-prv
        region_growth.append(delta)
        fields=[("25收入",r,"原值","人民币元"),("25成本",c,"原值","人民币元"),
                ("25收入占比",rate(r,d.m(2025,"收入")),"100×地区收入÷地区适用主营合计","%"),
                ("25地区毛利率",rate(r-c,r),"100×地区毛利÷该地区收入","%"),
                ("收入变化",delta,"本期地区收入−比较期同名地区收入","人民币元"),
                ("收入同比",yoy(r,prv),"100×Δ同名地区收入÷比较期收入","%")]
        nums=[e("B07","2024→2025",label+"·"+k,v,f,u,"各地区使用同一主营总额；同期地区+不同业务维度不叠加")
              for k,v,f,u in fields]
        region_rows.append([label,fm(nums[0]),fm(nums[1]),fp(nums[2]),fp(nums[3]),fm(nums[4]),fp(nums[5])])
    region_delta=d.m(2025,"收入")-d.m(2024,"收入")
    same(total(region_growth),region_delta)
    huadong=d.get(2025,REGION,"华东",col="营业收入")-d.get(2024,REGION,"华东",col="营业收入")
    e("B07","2024→2025","华东·主营收入增量占比",rate(huadong,region_delta),"100×华东收入增加÷主营收入增加","%","地区维度")
    o.section("地区收入与毛利","B07","2024 年报 p25–26、2025 年报 p28。其他使用年报原分类。地区表未拆成可复算的境内与境外收入。",
              ["地区","25收入","25成本","主营收入占比","地区毛利率","Δ收入","收入同比"],region_rows)
    channel_rows=[]
    for y in range(2021,2026):
        r=d.get(y,GROUP,"直销",col="营业收入"); c=d.get(y,GROUP,"直销",col="营业成本")
        rtot=d.is_(y,"收入") if y==2021 else d.m(y,"收入")
        ctot=d.is_(y,"成本") if y==2021 else d.m(y,"成本")
        same(r,rtot); same(c,ctot)
        cov="合并营业总额" if y==2021 else "附注主营业务合计"
        nums=[e("B08",str(y),k,x,f,u,cov) for k,x,f,u in
              (("直销收入",r,"原值","人民币元"),("直销成本",c,"原值","人民币元"),("直销收入覆盖",rate(r,rtot),"100×直销收入÷适用合计","%"),
               ("直销毛利率",rate(r-c,r),"100×直销毛利÷直销收入","%"))]
        channel_rows.append([y,cov,fm(nums[0]),fm(nums[1]),fp(nums[2]),fp(nums[3])])
    o.section("直销口径","B08","2019–2020 年报无销售模式金额列。表内覆盖率只表示发行人当年该表直销列覆盖适用合计。使用端和合同买方的拆分见[渠道与交付](渠道与交付.md)。",
              ["年","适用合计","直销收入","直销成本","收入占比","毛利率"],channel_rows)

    cash_rows=[]
    for y,period in zip(windows,labels):
        dcf=lambda k:d.cf(y,k)-d.cf(y,k,True)
        np=d.is_(y,"净利润")-d.is_(y,"净利润",True)
        cfo=dcf("CFO")
        wc=[d.adj(y,k)-d.adj(y,k,True) for k in ADJUST]
        indirect=cfo-np-total(wc)
        direct=cfo-dcf("销售收现")-dcf("税费返还")+dcf("采购付现")+dcf("职工付现")+dcf("税费付现")
        cur=[("合并净利润变化",np,"本年−比较年"),*((k+"调节变动",v,"本年现金调节行−比较行") for k,v in zip(ADJUST,wc)),
             ("其他间接调节变化",indirect,"ΔCFO−Δ合并净利−三项营运调节变动"),("经营现金流变化",cfo,"本年−比较年"),
             *((k+"变化（CFO方向）",dcf(k) if k in ("销售收现","税费返还") else -dcf(k),"流入变动原号；流出变动取反")
              for k in ("销售收现","税费返还","采购付现","职工付现","税费付现")),
             ("其他直接流量净变动",direct,"ΔCFO−五项现金流贡献"),("购建付现变化",dcf("购建付现"),"本年−比较年"),
             ("简化现金余量变化",cfo-dcf("购建付现"),"ΔCFO−Δ购建付现")]
        for k,v,f in cur:
            if y==windows[0]:cash_rows.append([k])
            next(r for r in cash_rows if r[0]==k).append(fm(e("B09",period,k,v,f,"人民币元","当年合并同报比较，两种桥各自闭合")))
        same(np+total(wc)+indirect,cfo)
        same(dcf("销售收现")+dcf("税费返还")-dcf("采购付现")-dcf("职工付现")-dcf("税费付现")+direct,cfo)
    o.section("利润到现金的两条复算路","B09",
              "前五项和经营现金流构成间接法桥。销售收现至其他直接流量为另一条直接法桥，两条桥分别解释同一 CFO 变化。负号表示对当年 CFO 变化的扣减。",
              ["变化项目",*labels],cash_rows)

    bal=[]
    for y in (2021,2022,2023,2024,2025):
        items=[("应收账款净额",d.bs(y,"应收账款")),("存货净额",d.bs(y,"存货")),("应付账款",d.bs(y,"应付账款")),
               ("合同负债",d.bs(y,"合同负债")),("固定资产",d.bs(y,"固定资产")),("在建工程",d.bs(y,"在建工程"))]
        nums=[e("B10",str(y),label,v,"合并资产负债表期末原值") for label,v in items]
        ratios=[e("B10",str(y),label+"／收入",rate(v,d.is_(y,"收入")),"100×期末余额÷年度合并收入","%","规模对照，使用期末时点")
                for label,v in items[:2]]
        bal.append([y,*map(fm,nums),*map(fp,ratios)])
    o.section("资本与营运余额","B10","期末余额用来观察资源占用。合同负债可能含年度折扣形成的余额。余额变动与 B09 现金调节仍须各用自己的口径。",
              ["年","应收","存货","应付","合同负债","固定资产","在建工程","期末应收／收入","期末存货／收入"],bal)

    volume=[]
    for y in (2024,2025):
        hard=d.vol(y,"智能硬件","销售量"); ctrl=d.vol(y,"控制系统","销售量")
        q=e("B11",str(y),"硬件销量／控制系统销量",rate(hard,ctrl),"100×两组集团销量比","%","全集团产品组；无整机逐单匹配")
        for label in ("控制系统","智能硬件"):
            for k in ("生产量","销售量","库存量"):
                e("B11",str(y),label+"·"+k,d.vol(y,label,k),"原表列","套")
        volume.append([y,fp(q)])
    opening=d.vol(2024,"智能硬件","库存量")
    made=d.vol(2025,"智能硬件","生产量")
    sold=d.vol(2025,"智能硬件","销售量")
    end=d.vol(2025,"智能硬件","库存量")
    left=opening+made-sold
    gap=left-end
    old=next(r for r in d.checks if r["年度"]=="2025" and r["勾稽项"]=="智能硬件实物库存差额")
    assert gap.n==D(old["差额"])==D(-2034)
    e("B11","2025","硬件期末机械推算",left,"上年期末＋本年生产−本年销售","套","同名原表机械滚动")
    e("B11","2025","硬件库存差额",gap,"机械推算−披露期末","套","原表期末有效，差额原因未知")
    o.section("集团实物结构与差额","B11",
              "2025 年智能硬件按 3,127＋59,626−56,824 推得 5,929 套。期末原表 7,963 套。差额为 −2,034 套，保持待核。集团两组销量比用于观察产品结构，整机匹配率待逐单数据。",
              ["年","硬件销量／控制系统销量"],volume)

    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/"经营桥明细.csv",o.rows)
    ids=sorted({s for r in o.rows for s in r["第一轮底表单元"].split("；") if s})
    write_csv(out/"底表引用索引.csv",[{**d.by_id[s],"年报文件名":d.sources[int(d.by_id[s]["报告年度"])]["文件名"]}
                 for s in ids])
    (out/"经营桥.md").write_text("\n\n".join(o.body)+"\n",encoding="utf-8")
    print(json.dumps({"第一轮锁定指纹":9,"计算记录":len(o.rows),"原表单元":len(ids),
      "分组桥":len(PRODUCTS),"财务比较窗口":len(windows),"硬件库存差额":str(gap.n)},ensure_ascii=False))

if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    p.add_argument("--first",type=Path,default=FIRST)
    p.add_argument("--output",type=Path,default=HERE)
    args=p.parse_args()
    build(args.first,args.output)
