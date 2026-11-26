"""Publish round-four Markdown, local HTML and charts from model outputs."""
from pathlib import Path
import csv,json,re,html,shutil,zipfile,subprocess,sys
import mistune
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;STAGE=HERE.parent
subprocess.run([sys.executable,"-X","utf8","-B",str(HERE/"reconcile.py"),str(STAGE/"第一轮"),str(HERE)],check=True)
subprocess.run([sys.executable,"-X","utf8","-B",str(HERE/"register_assumptions.py"),str(HERE)],check=True)
M=json.loads((HERE/"模型.json").read_text(encoding="utf-8"));B=M["base"];cases=M["results"]
plt.rcParams.update({"font.family":["Microsoft YaHei","sans-serif"],"font.size":11,"figure.facecolor":"#f3faf7","axes.facecolor":"#f3faf7","axes.spines.top":False,"axes.spines.right":False,"axes.unicode_minus":False})
CH=HERE/"charts";CH.mkdir(exist_ok=True)
def save(fig,key):
 fig.tight_layout();fig.savefig(CH/(key+".png"),dpi=155,bbox_inches="tight");plt.close(fig)
colors=["#bc895a","#378b73","#679ad1"]
fig,axs=plt.subplots(1,3,figsize=(14,4))
for s,c in zip(cases,colors):
 for ax,k,t in zip(axs,["revenue","core_ebit","fcff"],["收入","核心EBIT","FCFF"]):
  ax.plot([r["year"] for r in s["years"]],[r[k] for r in s["years"]],label=s["scenario"],color=c);ax.set_title(t);ax.set_xlabel("年");ax.set_ylabel("人民币百万元");ax.grid(alpha=.2)
axs[0].legend();save(fig,"forecast")
s=cases[1];f=s["years"][0]
fig,ax=plt.subplots(figsize=(9,4.5))
keys=["nopat","da","delta_nwc","capex","fcff"];v=[f["nopat"],f["da"],-f["delta_nwc"],-f["capex"],f["fcff"]]
ax.bar(["NOPAT","折旧摊销","营运占款","资本开支","FCFF"],v,color=[colors[1],colors[2],colors[0],colors[0],colors[1]])
for i,x in enumerate(v):ax.text(i,x+(20 if x>=0 else -20),f"{x:,.1f}",ha="center",va="bottom" if x>=0 else "top")
ax.set_ylim(min(v)-140,max(v)+180);ax.set_ylabel("人民币百万元");ax.set_title("2026 基准经营现金构成");save(fig,"fcff")
fig,ax=plt.subplots(figsize=(10,4.5))
labels=["经营价值","现金及金融资产","经营现金保留","融资与租赁","少数权益","归母权益"]
vals=[s["ev"],B["cash"]+B["financial"],-B["cashReserve"],-B["debt"],-B["minority"],s["equity"]]
ax.barh(labels,vals,color=[colors[1],colors[2],colors[0],colors[0],colors[0],colors[1]]);ax.invert_yaxis();ax.set_xlabel("人民币百万元");ax.set_title("2025年末条件股权桥")
save(fig,"equity")
sens=list(csv.DictReader((HERE/"折现与增长敏感性.csv").open(encoding="utf-8-sig")));ws=sorted({float(r["wacc"]) for r in sens});gs=sorted({float(r["g"]) for r in sens})
z=[[next(float(r["price"]) for r in sens if float(r["wacc"])==w and float(r["g"])==g) for g in gs] for w in ws]
fig,ax=plt.subplots(figsize=(7,5));im=ax.imshow(z,cmap="YlGnBu");ax.set_xticks(range(len(gs)),[f"{g:.1%}" for g in gs]);ax.set_yticks(range(len(ws)),[f"{w:.1%}" for w in ws])
for i,row in enumerate(z):
 for j,x in enumerate(row):ax.text(j,i,f"{x:.2f}",ha="center",va="center",color="black" if x<110 else "white")
ax.set_xlabel("稳定增长假设");ax.set_ylabel("WACC假设");ax.set_title("基准场景条件每股值（元）");save(fig,"sensitivity")
fig,ax=plt.subplots(figsize=(9,4.5))
mult=list(csv.DictReader((HERE/"倍数条件价格.csv").open(encoding="utf-8-sig")))
labs=[x["scenario"]+" DCF" for x in cases]+["前瞻PE "+r["PE2026"]+"倍" for r in mult]
vals=[x["price"] for x in cases]+[float(r["price"]) for r in mult]
ax.barh(labs,vals,color=colors+[colors[2]]*len(mult));ax.invert_yaxis()
for i,x in enumerate(vals):ax.text(x+1,i,f"{x:.2f}",va="center")
ax.set_xlim(0,max(vals)*1.2);ax.set_xlabel("2025年末口径条件元／股");ax.set_title("DCF与研究倍数条件并列");save(fig,"relative")
def table(headers,rows):
 return "| "+" | ".join(headers)+" |\n| "+" | ".join("---" for _ in headers)+" |\n"+"\n".join("| "+" | ".join(str(x) for x in r)+" |" for r in rows)
def img(key,caption):return f"![{caption}](charts/{key}.png)\n\n*{caption}*"
def money(n):return f"{n:,.2f}"
assumptions=table(["参数","压力","基准","改善","锚点、推导及反证"],[
["2026场景收入增长","−8/2/8/3/0%","10/16/25/20/6%","16/23/35/30/8%","依次平面、管材、三维、其他主营、其他业务。2024–25分类表p25及p27–28。基准比2025增速回落；订单、同规格净价及回款走弱则下修。"],
["第五年起场景毛利率","77/78/78/45/45%","80/83/82/51/50%","83/86/85/55/55%","从2025原值五年线性过渡。硬件搭配、折扣和材料成本改变则修订。"],
["销售／管理／研发费率","7.5/7.5/18%","6.3/6.8/15.5%","6.0/6.3/14.5%","2025利润表p126，原费率约6.23/7.09/15.55%。规模摊薄是条件，现场服务费用超支则上调。"],
["现金经营税率","17%","13%","11%","p167母公司10%及不同子公司税率，仅为综合现金税代理；优惠到期或结构变化需重算。"],
["应收／库存／应付天数","65/220/50","48/185/60","40/150/65","2025约45.48/186.07/59.29天，含应收账款、票据及融资，按收入、成本分别匹配；逾期和库龄恶化则上调。"],
["折扣／货款余额率","4.5/0.6%","2025余额率不变","5.2/1.0%","p213折扣114.11、货款18.28百万元。已净额预测收入，余额变动只进营运资本一次。"],
["增长净固定资本","Δ正收入÷2","Δ正收入÷3","Δ正收入÷4","多年购建及固定资产为锚，比例为研究假设；项目付现高于预算则下调销售资本效率。"],
["终期ROIC／g／WACC","12/1/10%","20/2/8.5%","28/2.5/7.5%","全部为条件参数。ROIC超过WACC需持续优势支持；反方为标准化替代、净价或客户份额下滑。"]])
valtable=table(["情景","显性期现值","终值现值","终值占经营价值","股权桥","每股条件值"],[
 [s["scenario"],money(s["explicit_pv"]),money(s["terminal_pv"]),f'{s["terminal_weight"]:.1%}',money(s["bridge"]),f'{s["price"]:.2f}'] for s in cases])
annual=table(["情景／年","收入","成本","销管研","核心EBIT","税","NOPAT","折旧","ΔNWC","购建","FCFF"],[
 [s["scenario"]+"/"+str(r["year"]),*[money(r[k]) for k in ["revenue","cost"]],money(r["sales"]+r["admin"]+r["rd"]),*[money(r[k]) for k in ["core_ebit","cash_tax","nopat","da","delta_nwc","capex","fcff"]]] for s in cases for r in s["years"]])
mults=list(csv.DictReader((HERE/"条件倍数.csv").open(encoding="utf-8-sig")))
mt=table(["假设元／股","FY2025 PE","2026E PE","PB","PS","PEG","EV/核心EBIT"],[
 [f'{float(r["price"]):.2f}',*[f'{float(r[k]):.2f}' for k in ["PE_FY2025_TTM_at_20251231","forwardPE2026","PB","PS","PEG_PE2026_EPS2025to28","EV_coreEBIT"]]] for r in mults])
bridge=table(["项目","2025年末百万元","口径与来源"],[
["现金等价物",money(B["cash"]),"p230–231，剔除冻结保证金0.0046"],
["交易性及其他非流动金融资产、长期股权投资",money(B["financial"]),"p121–122，账面值作为条件加回；处置税、折价和非上市投资估值缺项"],
["经营现金保留",money(-B["cashReserve"]),"收入的8%，假设；不进入非现金营运资本"],
["短借、租赁和票据融资",money(-B["debt"]),"p122–123、216–218，票据14.35百万元按融资负担处理"],
["少数股东权益",money(-B["minority"]),"p123账面值代理，公允价值未知"],
["年末股份（百万股）",money(B["shares"]),"p219股份总数288,729,927；本轮不混用期后股数"]])
coretable=table(["项目","2025百万元","采用方式"],[
["核心EBIT",money(B["core"]),"收入−成本−销管研−税金及附加＋信用减值原符号"],
["其他收益","124.19","政府补助121.90及其他税费项目；核心基准剥离，软件税返在敏感性讨论"],
["财务费用","−32.82","融资及现金利息、汇兑与手续费混合；整体从核心移出，手续费成本用信用及运营费率覆盖的条件需核"],
["投资收益／公允价值","22.16／44.64","从核心剥离，金融资产与长期股权按账面另加；不在FCFF重复预测收益"],
["资产减值及处置","按原表","长期股权减值17.26不重复外推；其他处置差额见输入原格"],
["合并净利润／归母","1130.63／1112.55","p126；完整利润与经营口径不同，预测另加条件金融收益并扣利息和2%少数损益"]])
ch9=f"""# 预测怎样从历史走向现金

**未来十年的增长需要哪些盈利与投入条件？** 本轮以2025年末财务状态为条件起点，显性期2026–2035年，2036年起稳定期。2025年报于2026年4月10日可得，报告版本为2026年11月26日。因此数值是使用后来可获完整年报的回顾性条件测算。它不提供2025年末当时可交易的信息集。所有预测与市场价格网格均为研究假设。

先界定利润。核心EBIT保留产品收入、成本、税金及附加、销管研和信用损失。其他收益和金融收益从核心移出。2025年报p167说明软件增值税即征即退政策，p224列出政府补助和其他收益。现金流中税费返还99.29百万元与当期其他收益有确认和时点差异，不能相互替换。核心基准剥离全部其他收益，政策延续另提供可量化敏感性。

{coretable}

历史桥在2025年将核心EBIT1038.81百万元接到报表营业利润1245.12百万元，再扣非经营净支出和所得税，得到合并净利润1130.63百万元。减少数损益18.08百万元后，归母为1112.55百万元。逐项原格及符号见历史利润桥.csv。

{assumptions}

税金及附加取净收入1.3%，信用损失取0.2%，按2025税附及信用减值附近规模设置。预付按2025成本比例2.754%保持，D&A按2025收入比例约1.787%保持。其他应付及税费的完整经营属性留缺。

宏石和嘉泰使采购条件成为更明确的预测观察点。工艺适配可能帮助留下订单，客户仍会比较候选、规格和折扣。本版分别把同规格净价、实际配套、现场服务、研发、回款和备货接到原有情景变量。只有增量毛利覆盖工程服务与资本占用，才有依据向改善路径移动。若留用更多依赖返利、延保或长账期，应向压力路径移动。新增案例尚未给出直接改变已审参数的定量证据，三情景模型保持原指纹。

各组收入按净实现收入预测，缺少可比分组量价时直接假设增长率。首年不同场景增长分别体现平面基座、管材与三维扩展、其他主营组合及其他业务。十年增长逐步向稳定增长收敛，避免把2025年的高增长无限延长。毛利率五年过渡，费用按收入计提。2023年新方案金额与实物同比缺口沿用已审处理。

{img("forecast","2026–2035三情景收入、核心EBIT和FCFF；人民币百万元；同版逐年模型")}

应看收入与FCFF之间的距离。改善情景依赖较好的组内毛利、回款及资本效率。压力情景首年收入下降，仍按更长回款和更高存货天数准备营运资金。集团控制与硬件量只验证规模及结构，未用于虚构配套率或分组净价。

非现金经营资本定义为应收账款、票据及融资、预付款和存货，减应付账款、折扣与货款余额。预付按成本比例，应收按收入天数，存货和应付按成本天数。2025初始选定NWC为{B["nwc"]:.2f}百万元。税费及其他应收应付的经营归属仍不完整，经营现金保留与应收延迟敏感性用于检验遗漏影响，不能当完整历史实体资本核准。

收入已扣年度折扣，模型不再次从收入扣折扣。折扣负债按净收入目标比例变化并进入ΔNWC，模拟净确认与后续结算的时差；这要求折扣计量、净发票应收和结算口径一致。货款余额单列，两项均不是额外确认收入。实际结算与政策变化会改变这条代理路径。

现金税按正核心EBIT乘情景税率。D&A按2025合并折旧摊销占收入比例。前段资本开支等于D&A加正收入增量除销售资本效率，下降期仍保留维护投入。2033–2035逐步过渡到按ΔNOPAT/新增ROIC确定总再投资，再扣ΔNWC反推出净资本开支。租赁按资本化处理，D&A含使用权摊销，未来购建代理包含替换租赁资源所需投入，股权桥扣存量租赁义务。未来股份支付继续包含费用，股数假设固定，新增激励稀释需重算。

{img("fcff","2026基准FCFF构成；人民币百万元；NOPAT＋D&A−资本开支−ΔNWC")}

基准首年收入{f["revenue"]:.2f}百万元，完整归母利润{f["parent"]:.2f}百万元，低于2025年的1112.55百万元。剥离其他收益的保守路径与收入增长可以同时成立。完整归母预测的金融收益率1.5%、债务成本3.5%、少数损益占比2%均为研究假设。NOPAT{f["nopat"]:.2f}百万元，FCFF{f["fcff"]:.2f}百万元。新增占款和购建消耗现金。2025购建35.20百万元没有机械延续到首年，首年基准购建为{f["capex"]:.2f}百万元。购建翻倍与回款延迟检验另附表。

焊接和微加工沿2025年报p15–16、41的方向设独立投入条件。单独试算从其他主营既有收入中重分0、0、2至16百万元，使用25%毛利率替换该部分原组毛利，并额外承担前三年每年8百万元运营费、5百万元资本开支，其后每年3百万元运营费。总收入不追加，避免把新业务在其他主营和独立场景中重复计价。这组规模和成本是试探假设，尚无分业务披露原值。

历史留出使用“只延续上年收入增速”的简单规则，结果见历史留出.csv。它在2022压力期与随后恢复期明显偏离，说明高增速外推会漏掉周期和分类变化。这是原列的描述性检验，未用其误差为三种未来情景分配概率。

{annual}

逐年现金明确后，下一章才能把经营价值、非经营资产和股东归属放在同一个2025年末口径内。
"""
ch10=f"""# 条件现金流能支撑怎样的价值

**这套盈利和再投资路径，在怎样的必要回报下成立？** 以下DCF均为2025年末条件价值，使用2026年4月10日可获年报。年末折现，十年FCFF形成显性价值，2036年现金流形成终值。估值单位为人民币百万元，每股值以2025年末288.73百万股计算。

{valtable}

WACC采用E/(D+E)×(Rf＋β×ERP)＋D/(D+E)×Kd×(1−税率)。缺少年报范围内可核的市场风险溢价、无风险利率、β和市场权重，本轮WACC为研究条件。可供研究的Rf区间2%–3%、β0.9–1.3、ERP5%–7%、Kd3%–5%及债务权重0%–5%均是假设，不是行情观察。三情景7.5%–10%与7%–11%敏感性展示所需回报变化。

终值FCFF=2036 NOPAT×(1−g/新增ROIC)，终值=FCFF/(WACC−g)。g低于WACC，新增ROIC高于g。2035各组增速收敛到g，毛利和费率已稳定，末段再投资与ΔNOPAT/ROIC相接。稳定期不再依赖低购建的现金释放。资本回报敏感性只改变终值新增回报，显性路径保持，其用途是识别终值的独立依赖。

{bridge}

{img("equity","2025年末基准经营价值到归母权益的条件桥；人民币百万元；原页见输入原格和补充来源")}

应看经营资产与金融资产的分开计量。金融资产加回对应核心现金流剥离利息、投资和公允价值收益。长期股权按减值后账面加回，未来估值或处置税可能使其偏离账面。少数权益也用账面代理，公允价值待证。这些条件会影响每股数，仍须在进入买入评估时补证。

{img("sensitivity","基准DCF的WACC与g敏感性；假设元／股；折现与增长敏感性.csv")}

终值在基准经营价值中占{s["terminal_weight"]:.1%}，因此长期现金假设有很大影响。利润率与回款延迟联合网格另见利润现金联合阈值.csv；购建和经营现金保留网格检验维护投入及现金储备。图册可同时调整WACC、g、组内毛利偏移、应收天数与前段购建倍率，表中会重算FCFF和每股值。最后三年的资本开支仍遵循新增回报约束，倍率用于前段并逐渐退坡。

{img("relative","同一财务起点下DCF与前瞻PE研究条件；元／股；倍数条件不是历史市场带")}

{mt}

PE的TTM仅指2025年末向前十二个月，即FY2025归母利润；它不代表2026年11月的最新TTM。前瞻PE用2026同版完整归母利润，包含按年末可投金融资产1.5%收益率、3.5%债务成本和2%少数损益比例的条件。DCF核心利润不含这些金融收益，金融资产已在权益桥加回。PB用年末归母权益，FY2025归母利润除年末权益约18.33%，平均权益ROE另需前期权益口径。PS以合并收入为分母，不能忽略其他主营毛利低于平面的结构。EV/核心EBIT用市值减现金、减金融资产、加经营现金保留和债务及少数权益，匹配剥离金融收益的核心利润。

PEG=2026前瞻PE÷2025–2028固定股数EPS复合增速的百分数。增速非正时留缺，不能给负PEG排序。基准EPS的2025–2028复合增速约4.74%，因此基准DCF隐含2026PE约23.13倍时，PEG约4.88。这个结果提示远期增长与现金回报对估值的重要性，也暴露短窗口盈利增速较慢的反方。研究条件15、20、25、30倍前瞻PE仅是比较网格。20倍在约5%盈利收益率下仍要留出增长投入，持续性和ROIC能否支撑该回报需经营证据。没有可核价格、同行财报和倍数时，不能称它为市场合理区间。

方法分歧先查盈利分母，再查净现金和金融资产、增长、再投资、折现与终值。PE资本化完整利润，可能把暂时金融收益和补助当持续盈利。DCF核心基准剥离全部其他收益，又要求增长投入。它的优势是显式约束现金，弱点是远期参数依赖。两者并列用于检验假设，缺少市场输入时没有形成实际高估低估判断。

旧81.81元属于2026年11月12日信息窗口的冻结模型，原资料含2026三季报、期后权益桥及405,984,426股。旧96.20元是该窗口行情，旧WACC6.9274%来自原研究估计，平台倍数来自旧行情资料，均不进入本轮。新版以2025年末资产、288,729,927股及分场景增长建立十年路径。若只固定新权益总值、把分母换为旧股数，得到{s["equity"]/405.984426:.2f}元，这只是分母算术隔离，不能当窗口可比价格。实际窗口桥还缺截至旧估值日的分红、资本变动、期中现金流与原市场输入复核。

缺少年末市场收盘、当日经济股数及权利、日度或月度历史价格、同日同行报表与公司行为调整，历史市场估值带及同日价格比较留缺。假设价格网格的倍数可复算，公司长期价值判断仍要回到经营兑现。
"""
ch11=f"""# 综合判断与进入买入评估的条件

**柏楚靠什么长期赚钱，当前研究应该采取怎样的立场？** 柏楚把图形处理、工艺、数控和传感执行连接起来，为设备制造商提供控制与配套。标准产品的安装较简单，持续关系仍取决于产品效果、接口适配、整机配置和现场服务。2025年平面是最大的主营毛利来源，其他场景扩大增长来源。长期价值需要增长毛利扣除费用、税、营运占款和资本投入后，仍留下现金。

11.25基线第四轮经刘翔宇独立审核通过。本版结合第七章护城河的工艺、采购、利润和现金检验，实施方维持“**有投资前景，值得持续跟踪**”的长期判断。依据是已审历史中的主营毛利贡献、压力后的恢复，以及能够持续产生现金的经营条件。宏石与嘉泰说明持续采购、规格和重新比价并存。工艺复用能否降低重复验证，仍需与同机型的净价、服务和回款共同检验。实际续购率、同规格净价、切换成本仍待证。基准条件每股{s["price"]:.2f}元，压力{cases[0]["price"]:.2f}元，改善{cases[2]["price"]:.2f}元，区间反映假设差异，未赋予概率，也未接入当前行情。

进入买入评估需要同时满足经营、现金和价格条件。首先，同场景毛利、研发及服务投入需与基准路径相容。其次，回款、库存与维护资本不能持续向压力假设恶化，硬件滚动差额要取得解释。最后，在核对同日价格与股东权利后，再比较条件价值。若研究者要求基准值25%的价格缓冲，条件价格门槛约{s["price"]*.75:.2f}元；这项缓冲为研究假设，并非实际买入指令。压力值较低，仍需判断压力情形的证据和可承受损失。

如果平面和管材同规格净价走弱、客户换用其他方案、场景毛利下降，同时回款天数升到65天以上和库存约220天，增长可能更多消耗现金。若维护及扩张资本显著高于本模型，或稳定期新增ROIC接近必要回报，则应收窄长期前景判断。相反，同一批OEM延续采购、净价和回款保持、软硬增量覆盖售后并提高现金，可增强改善路径的依据。

软件税返持续是上行条件之一。基准已剥离全部其他收益。以净收入4%作为新增经营支持、按13%条件税率纳税，仅作为现金补助代理，条件4%支持对应每股约91.37元，2%对应约88.23元，额外营运占款及政策资格差异仍待核。其显性期及终值都可量化重算。年报收到税费返还与确认其他收益存在差异，政策、资格或退税周期变化可能使该代理失效。新增业务则必须用不重复的收入分配和独立投入核查，其条件试算见压力一致性检查.csv。

正式行情判断需补足当日价格与权利、市场参数和可比公司同口径数据。11.25基线的原格、首年预测及DCF已经刘翔宇独立抽核并裁定通过。11.26新增整合由成员四Codex实施Agent完成，三名核对Agent分别回案例、财务与模型，真实范围见本版整合验收记录。本版没有代填刘翔宇新增人工审核或最终签署。
"""
for num,text in [(9,ch9),(10,ch10),(11,ch11)]:
 (HERE/f"chapter{num}.md").write_text(text,encoding="utf-8")
# Preserve approved history while adopting the reviewer wording.
oldmd=(HERE/"第三轮报告留存.md").read_text(encoding="utf-8")
oldmd=oldmd.replace("柏楚最有价值的业务仍是平面解决方案。","平面解决方案是柏楚2025年最大的主营毛利来源。").replace("第三轮历史经营与商业模式审阅稿","第四轮预测与估值完整定稿")
oldmd=oldmd.replace("第三轮独立审核待刘翔宇裁定","第四轮经刘翔宇独立审核通过，四轮研究交付完成")
extra="\n\n".join(t.replace("# ","## ",1).replace("](charts/","](柏楚电子证券投资图册11.26新版/第四轮/charts/") for t in [ch9,ch10,ch11])
report=STAGE.parent/"柏楚电子证券投资分析报告11.26新版.md"
report.write_text(oldmd.split("## 依据与来源")[0]+extra+"\n\n## 依据与来源"+oldmd.split("## 依据与来源",1)[1]+"\n\n第四轮输入原格、补充来源及逐年模型均见图册第四轮目录。",encoding="utf-8")
renderer=mistune.create_markdown(escape=False,plugins=["table"])
extrahtml=""
for num,text in [(9,ch9),(10,ch10),(11,ch11)]:
 content=renderer(text.replace("](charts/","](第四轮/charts/"))
 content=re.sub(r"<img([^>]+)>",r'<div class="plot"><img\1></div>',content)
 extrahtml+=f'<section class="chapter" id="ch{num:02}">'+content+'</section>'
htmlpage=(HERE/"第三轮图册留存.html").read_text(encoding="utf-8")
htmlpage=htmlpage.replace("柏楚最有价值的业务仍是平面解决方案。","平面解决方案是柏楚2025年最大的主营毛利来源。")
htmlpage=htmlpage.replace("11.26 新版 · 第三轮审阅","11.26 新版 · 四轮交付完成").replace("历史经营与商业模式 · 2019–2025 年报","2025年末条件估值 · 2025年报2026-04-10可得 · 报告2026-11-26").replace("第三轮独立审核待裁定","第四轮已独立审核通过，四轮研究交付完成")
htmlpage=htmlpage.replace('<a href="#sources">来源与原格</a>','<a href="#ch09">预测与现金</a><a href="#ch10">估值与敏感性</a><a href="#ch11">综合判断</a><a href="#sources">来源与原格</a>')
# Interactive assumptions are embedded. No runtime fetch needed.
widget="""<section class="chapter" id="calculator"><h1>条件估值试算</h1><p>2025年末条件价值，使用2026-04-10可获年报。所有控件为假设。默认基准，不含其他收益，金融资产按账面条件加回。价格网格与估值均非行情。</p><div class="controls"><label>情景<select id="case"><option>压力</option><option selected>基准</option><option>改善</option></select></label><label>WACC %<input id="wacc" type="number" min="4" max="20" step=".1" value="8.5"></label><label>稳定g %<input id="growth" type="number" min="0" max="4" step=".1" value="2"></label><label>组内毛利偏移 pp<input id="margin" type="number" min="-10" max="10" step=".5" value="0"></label><label>应收延迟天<input id="days" type="number" min="0" max="120" value="0"></label><label>前段购建倍率<input id="cap" type="number" min="1" max="3" step=".1" value="1"></label><button id="reset" type="button">恢复基准</button></div><p id="calcResult" aria-live="polite"></p><div class="table-scroll"><table><thead><tr><th>年</th><th>收入</th><th>EBIT</th><th>FCFF</th></tr></thead><tbody id="calctable"></tbody></table></div></section>"""
jscode=(HERE/"calculator.js").read_text(encoding="utf-8")+"""
const MODEL=JSON.parse(document.getElementById('model-data').textContent);
const el=id=>document.getElementById(id);
function refresh(){let n=el('case').value,w=+el('wacc').value/100,g=+el('growth').value/100;
 if(w<=g||g>=MODEL.cases[n].roic){el('calcResult').textContent='请保持WACC大于g，且新增ROIC大于g。';return}
 let r=calculate(MODEL,n,w,g,+el('margin').value/100,+el('days').value,+el('cap').value);
 el('calcResult').textContent='条件每股 '+r.price.toFixed(2)+' 元，显性期现值 '+r.explicit_pv.toFixed(2)+' 百万元，终值现值 '+r.terminal_pv.toFixed(2)+' 百万元。';
 el('calctable').innerHTML=r.years.map(x=>'<tr><td>'+x.year+'</td><td>'+x.revenue.toFixed(2)+'</td><td>'+x.core_ebit.toFixed(2)+'</td><td>'+x.fcff.toFixed(2)+'</td></tr>').join('');
}
['wacc','growth','margin','days','cap'].forEach(k=>el(k).addEventListener('input',refresh));
el('case').addEventListener('change',()=>{const s=MODEL.cases[el('case').value];el('wacc').value=s.wacc*100;el('growth').value=s.g*100;refresh()});
el('reset').addEventListener('click',()=>{el('case').value='基准';el('wacc').value=8.5;el('growth').value=2;el('margin').value=0;el('days').value=0;el('cap').value=1;refresh()});refresh();
"""
downloads='<section class="chapter"><h1>第四轮模型与证据</h1><p>'+ ' · '.join(f'<a href="第四轮/{name}">{name}</a>' for name in ["逐年模型.csv","历史利润桥.csv","关键假设来源.csv","输入原格.csv","补充来源.csv","股权桥来源.csv","模型.json","条件倍数.csv","折现与增长敏感性.csv","资本回报敏感性.csv","利润现金联合阈值.csv","购建与经营现金保留.csv","税返延续敏感性.csv","历史留出.csv","压力一致性检查.csv","README.md","验收记录.md"] )+'</p></section>'
htmlpage=htmlpage.replace('<section id="sources"',extrahtml+widget+downloads+'<section id="sources"',1)
htmlpage=htmlpage.replace('</body>','<script type="application/json" id="model-data">'+json.dumps(M,ensure_ascii=False)+'</script><script>'+jscode+'</script></body>')
htmlpage=htmlpage.replace('</style>',".plot{max-width:100%;overflow:auto}.plot img{display:block;width:100%;height:auto}@media(max-width:850px){.plot img{min-width:650px}}select{font:inherit;padding:9px;border-radius:12px;border:1px solid #a9c8ba;background:white}.controls label{font-size:15px;max-width:180px}.controls input{max-width:150px}#calcResult{font-weight:bold;padding:16px;border-radius:16px;background:#e0efe7}</style>")
# Bundle complete issuer originals locally so the offline package preserves physical-page links.
rawdir=HERE/"年报原件";rawdir.mkdir(exist_ok=True)
for r in csv.DictReader((STAGE/"第一轮/年报索引.csv").open(encoding="utf-8-sig")):
 f=Path(r["本地原件"]);dest=rawdir/f.name
 if not dest.exists():shutil.copy2(f,dest)
 old="../../../" # Regex below replaces all existing annual-report relative links.
htmlpage=re.sub(r'href="[^"]*/sources/raw/01_年报/([^"#]+)(#[^"]*)?"',
 lambda m:'href="第四轮/年报原件/'+m[1]+(m[2] or '')+'"',htmlpage)
(STAGE/"index.html").write_text(htmlpage,encoding="utf-8")
# Standalone chapter references resolve charts relative to HERE.
print("Fourth-round report and HTML built")
