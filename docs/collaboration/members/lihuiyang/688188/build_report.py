"""Build the personal Version2 report without changing the team archive or model."""
from pathlib import Path
import csv, hashlib, html, json, re, shutil
from decimal import Decimal as D

ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
REPORTS=ROOT/'报告留存处'
ARCHIVE=REPORTS/'柏楚电子证券投资图册'
BASE=ARCHIVE/'original/report.md'
TARGET=REPORTS/'2026-11-24_SSE-688188_柏楚电子证券投资分析报告Version2.md'
ASSETS=REPORTS/'assets/688188Version2'
ASSETS.mkdir(parents=True,exist_ok=True)

def readcsv(name):
 with (ARCHIVE/'data'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

financial=next(x for x in readcsv('financial-bridge.csv') if x['period']=='2025-FY' and x['column']=='本期')
cash=next(x for x in readcsv('cash-history.csv') if x['year']=='2025')
revenue=D(financial['revenue']);parent=D(financial['parent_profit']);net=D(financial['net_profit'])
cfo=D(financial['cfo']);capex=D(financial['capex']);da=D(cash['da_m'])*D(1000000)
simple=cfo-capex
f=lambda x,n=2:f'{x:,.{n}f}'

market='''### 市场叙事怎样变成可检验的投资命题

本轮补充的八篇雪球文章，集中讨论软件能力、工艺积累、客户粘性和新业务。其中两篇来自方心景，六篇来自都不是的同一连载。本文把它们视为两位作者提出的研究线索，不据篇数推定市场共识。它们共同提示一个值得研究的机制：设备厂买到熟悉且兼容的加工控制，可能减少调机、培训与联调成本；柏楚若将这部分节省留在净价与复购中，就能持续取得收益。[补充材料清单](../docs/collaboration/members/lihuiyang/688188/材料核验.md)

这一机制有三道检验。第一，设备厂在同一机型上的重复选择是否来自使用效率，还是竞争方案、需求景气和报价暂时变化？第二，配套切割头是否增加同订单净毛利，还是以控制器折让、延长保修或账期换来收入？第三，研发平台的共用能否缩短新场景验收，而不是只扩大项目数量？前两道决定已有业务的价格与现金，第三道决定后续新增业务何时进入预测。

<div align="center">表 N1　市场叙事、检验变量与估值入口</div>

| 待检验解释 | 应看到的经营证据 | 不能由现有标签直接推出的内容 | 对应模型 |
| --- | --- | --- | --- |
| 工艺及软件复用降低客户成本 | 同OEM同机型的调试、一次验收、重选净价与后续订单 | 技术功能齐全不等于永远不可替代 | 新机取得、续购、控制组净价 |
| 配套提高交付效果 | 同订单附着、材料成本、返修、到账 | 硬件销量与控制量的比值不等于真实附着率 | 硬件收入、售后、存货和应收 |
| 大厂自研与第三方控制分工 | 具体机型的采购与自研边界、兼容合同及竞价 | 某厂当前自用不等于永远不会外售或替代 | 取得份额、净价、销售与研发支出 |
| 通用运动底座打开新应用 | 样机、认证、可销售订单、验收及收款 | 整机市场空间不等于控制及配套可获收入 | 新业务增量与相应研发、资本 |

文章中的份额、客户切换所需月数和替代的时间判断，需要同口径来源才能成为模型输入。已有方案收入按应用分类，产销按产品统计，不能把应用收入叫纯软件收入，也不能把“低边际复制成本”扩展到整套硬件、现场服务和长期研发。行业竞争也可能在同一合同的几个环节同时发生：一个厂商今天供应光源、明天提供成套方案，互补与局部替代可以并存。报告据具体产品和订单划边界，不给某类厂商永久排除竞争资格。

本稿保留切割与配套的已识别经营锚。弧焊、锂电焊接和超快精密的可识别新增收入继续按零进入当前场景，待订单、验收和回款再调整；历史上已在集团确认的相关收入留在既有残余组，不能再次扣除或重复加入。这样会比单纯给新赛道安排较高增速更审慎，也使后续的上修有清楚依据。

### 控制权、研发激励与资本分配

柏楚的技术投入和资金分配，最终由实际治理结构作出选择。2025年末，唐晔、代田田、卢琳、万章和谢淼是前五位股东，年报披露五人签署一致行动协议。按年末持股数合计，其股份约占当时总股本64.59%。这一结构有助于维持较长期的研发安排，也使普通股研究必须跟踪：新项目如何批准、预算如何调整、闲置资金留存还是分配、激励最终形成多少股份。持股与一致行动并不自动证明每一项资本配置都会产生回报。

<div align="center">表 N2　2025年末主要自然人股东与披露比例</div>

| 股东 | 年末持股数（股） | 年报披露比例 |
| --- | ---: | ---: |
| 唐晔 | 53,339,003 | 18.47% |
| 代田田 | 41,718,851 | 14.45% |
| 卢琳 | 36,194,281 | 12.54% |
| 万章 | 32,384,156 | 11.22% |
| 谢淼 | 22,859,445 | 7.92% |

来源：[2025年报](https://static.cninfo.com.cn/finalpage/2026-04-10/1225091045.PDF#page=113)，PDF物理p113—114。展示比例有舍入，合计应按股数除以288,729,927股计算；这些是2025年末持股，不能替代2026年估值日股权状态。

2025年研发费用3.4133亿元，研发人员525人、占员工40.92%，且研发投入披露包含人员股份支付。工资和股份激励可以让工程团队持续投入，但费用强度并不是技术回报。研究者应把项目进度、客户验证、交付质量和实际净收益与投入对应起来。估值沿费用化研发口径，不再把同一研发支出在资本端扣一遍；如果未来进行研发资本化，需要同时调整经营利润、资本和摊销，不能只抬高利润。

股份变动还需要分清资本公积转增与激励归属。前者改变股数及每股数的尺度，不能当作经营增长；后者在满足条件并完成登记后改变实际权利，可能伴随认购款流入。2025年的归属记录可在年报物理p110—112核对，2026年估值仍采用同日登记的405,984,426股；历史EPS加权股数与现值分母不互换。新授予不等于已发行，新发股份也不能只扣稀释而忽略真正取得的现金与费用。

资本配置的另一面是股东分配。2025年报所列年度拟案加中期已分配的现金红利合计约7.4897亿元，占当年归母利润67.32%；其中年度拟派5.5667亿元，年报发布时仍属方案，实施情况须另核权益分派公告。这体现管理层提出的分配力度，未来比例取决于经营与资金安排。[2025年报p2、p55](https://static.cninfo.com.cn/finalpage/2026-04-10/1225091045.PDF#page=55) 现金池未来用于研发、项目、营运、回购还是股利，都要避免在FCFF与权益桥中重复处理。对控制股东的判断因此落到真实项目及分配决策和执行结果，不以创始团队身份直接给治理溢价。

'''

cash_note=f'''### 对“现金释放期”的交叉核验

一篇补充文章将资本支出回落视为现金释放的迹象。本报告保留这一观察线索，同时把计算拆开。2025年报的经营现金净额为{f(cfo/D(100000000),4)}亿元，合并净利润为{f(net/D(100000000),4)}亿元，归母净利润为{f(parent/D(100000000),4)}亿元。CFO与归母利润之比约{f(cfo/parent,3)}，若按集团全部净利润作分母则约{f(cfo/net,3)}。两种比率回答的对象不同。

现金购建支出仍是正的{f(capex/D(100000000),4)}亿元，CFO减该项后为{f(simple/D(100000000),4)}亿元。这个报表现金差额可以回表复算；若采用不同的自由现金口径，须另列定义和桥接，不能把文章中的其他结果直接替换它。[2025年报p126、p130](https://static.cninfo.com.cn/finalpage/2026-04-10/1225091045.PDF#page=126)

按已归档历史折旧摊销约{f(da/D(100000000),4)}亿元，现金购建减折旧摊销约为{f((capex-da)/D(1000000),4)}百万元。这个负值表示本期这两项净额为负，并不能证明以后无需增长性投资：研发已在费用中发生，库存和应收还可能增占资金，新应用也需要验证、产线和服务。把本年购建下降永久外推，同时给予新赛道高增速，会把现金需求压得过低。

已有历史经营FCFF代理另用核心利润、经营税和窄贸易资本推导，2025年约8.1982亿元，与CFO减购建相差约2.4930亿元。报告保留该差额的范围和支付时点问题。后文预测按其声明的费用、资本和税假设运行，不用净利润与CFO接近这一现象跳过经营现金预测。

'''

terminal_note='''### 对外部估值情景的复核

外部估值文章提出未来利润增长与终点P/E的组合。它为讨论增长提供了条件世界，但没有给出分业务基期、每年资本和可归股东现金的完整桥；对未来股价的推导也必须与当期现值分开。本文按文章自身的利润锚、五年复合增长率、终点倍数和固定股数作算术复核，结果见下表；这一运算没有采用其预测为本公司的事实或新增目标价。

<div align="center">表 N3　外部增长和终点倍数的条件算术</div>

| 文章情景标签 | 利润五年CAGR | 2030利润（亿元） | 终点P/E | 固定4.08亿股时2030每股金额（元） |
| --- | ---: | ---: | ---: | ---: |
'''
external=[]
for name,g,pe in [('原文保守',D('.24'),D(30)),('原文中性',D('.28'),D(37)),('原文乐观',D('.34'),D(45))]:
 profit=D('11.13')*(1+g)**5
 price=profit*pe/D('4.08')
 external.append(dict(label=name,profit_anchor_2025_yi='11.13',growth=str(g),years=5,pe=str(pe),shares_yi='4.08',profit_2030_yi=str(profit),future_price_cny=str(price),status='article-conditional-arithmetic-not-adopted'))
 terminal_note+=f'| {name} | {g:.0%} | {profit:.2f} | {pe:.0f} | {price:.2f} |\n'
terminal_note+='''
来源：[都不是，2026-07-26估值文章](https://xueqiu.com/1486099110/402142812)；本轮独立公式复算，只重现该组假设。利润锚11.13亿元和4.08亿股是文章使用的舍入数，不替代本报告精确报表与估值股数。

三种路径的最低利润增长仍为24%，不包含零增长、让价、周转恶化或新业务失败的压力世界；“保守”的名称不能证明下行风险已覆盖。终点P/E包含2030年市场愿意支付的倍数，其高低会受到届时增长、风险、竞争与资本需求影响。若把终点股权价值折回当期，应采用与股权现金权利匹配的权益成本和准确期限，并处理期间分配及稀释，不能直接拿WACC折股价。

这些条件算术与当前DCF的不同，主要是经营兑现、资本负担、终点定价和时点各自不同。AI给出相近的价格不能增加原参数的证据强度。本文继续以逐年经营现金、稳定期再投资和普通股桥构成81.81元基准，而把外部较高增长视作需要被订单和现金证明的上行情景。

'''

source=BASE.read_text(encoding='utf-8')
base_sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
source=re.sub(r'^# .+\n','# 柏楚电子证券投资分析报告 Version2\n',source,count=1)
source=re.sub(r'^\*\*撰写与整理\*\*.*$', '**撰写与整理**　团队11.23归档稿由Codex整理，接续图册11.24两处计算勘误；本版由李辉阳个人分支的主Agent续写。',source,count=1,flags=re.M)
source=re.sub(r'^\*\*稿件状态\*\*.*$', '**稿件状态**　个人续写审阅稿；待团队复核、取舍和采纳。',source,count=1,flags=re.M)
source=source.replace('**研究日**　2026-11-23','**研究日**　2026-11-24',1)
source=source.replace('**源提交**','**原团队模型源提交**',1)
source=source.replace('92.75774737785618','92.76')
source=source.replace('6.9274187472%','6.9274%').replace('7.5334057567%','7.53%').replace('49.8011297326%','49.80%')
source=source.replace('21.9563231292 亿元','21.9563 亿元').replace('5.391052%','5.39%').replace('5.208872%','5.21%').replace('2.306047%','2.31%')
source=source.replace('52.2421495225 亿元','52.2421 亿元')
source=source.replace('[HTML 浏览及打印]','[配套图册（团队11.23版）]')
source=source.replace('[02 商业模式与竞争]','[02 商业模式、市场叙事、治理与竞争]')
source=source.replace('## 九章目录','## 九章目录与新增论证',1)
source=source.replace('2. [商业模式与竞争](#chapter-02)','2. [商业模式、市场叙事、治理与竞争](#chapter-02)',1)
source=source.replace('## 第 2 章　商业模式与竞争','## 第 2 章　商业模式、市场叙事、治理与竞争',1)
source=source.replace('<a name="chapter-03"></a>',market+'<a name="chapter-03"></a>',1)
source=source.replace('### 2022 和 2026 的现金改善不走同一条路',cash_note+'### 2022 和 2026 的现金改善不走同一条路',1)
source=source.replace('<a name="chapter-09"></a>',terminal_note+'<a name="chapter-09"></a>',1)
source=source.replace('正文 40 页','正文按约40页预算组织，最终页数在排版后核定')
source=re.sub(r' · p\d+\b','',source)
source=source.replace('**资料身份与期间。** 2022、2024/2025 和 2026Q3 的原表抽核共 103 个单元，按 SHA、物理页、合并范围和期间列核对。原件绑定恢复后 ReviewStore 有效 Fact 为 24 条。','**资料身份与期间。** 团队原稿记录了2022、2024/2025和2026Q3的103个单元抽核，以及原件恢复后的24条有效Fact。本轮保留其来源身份，新增对2025年报主要财务、研发、股东、利润及现金购建的Agent回查；不将前轮核验改记为本轮学生核验。')

# Prefer available in-repository snapshots to a historical source URL.
remote='https://github.com/Loyyed/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2/blob/5f485482174392124261b1654ed102d16c19030c/docs/cases/688188/'
def localize(m):
 url=m.group(0)
 tail=url[len(remote):]
 filename=tail.rsplit('/',1)[-1]
 if (ARCHIVE/'data'/filename).is_file():return './柏楚电子证券投资图册/data/'+filename
 if tail.endswith('/review.md'):return './柏楚电子证券投资分析报告11.23一版.md'
 if tail.endswith('/review.html'):return './柏楚电子证券投资图册/index.html'
 if tail.endswith('/figures/README.md') or tail.endswith('/README.md'):return './柏楚电子证券投资图册/README.md'
 return url
source=re.sub(re.escape(remote)+r'[^)\s]+',localize,source)

# Convert the four Mermaid blocks with already-rendered PNG fallbacks into ordinary figures.
source=re.sub(r'```mermaid\n.*?```\n\n\[([^\]]+)\]\(([^)]+\.png)\)',r'![\1](\2)',source,flags=re.S)
def image_copy(m):
 alt,url=m.groups()
 original=(REPORTS/url).resolve()
 if not original.is_file():raise FileNotFoundError(original)
 target=ASSETS/(original.stem+'Version2'+original.suffix)
 if target.exists() and hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(original.read_bytes()).digest():
  raise RuntimeError('Existing figure differs; preserve it and create the next VersionN.')
 shutil.copyfile(original,target)
 return f'![{alt}](./assets/688188Version2/{target.name})'
source=re.sub(r'!\[([^\]]*)\]\((\./柏楚电子证券投资分析报告11\.23一版_图件/[^)]+)\)',image_copy,source)

# Caption placement: tables above, figures below, consistently centered.
lines=source.splitlines();result=[];caption=None
def put_caption():
 global caption
 if caption:
  result.extend(['',f'<div align="center">{html.escape(caption)}</div>',''])
  caption=None
for line in lines:
 if line.startswith('#### 图表 '):
  put_caption();caption=line[5:].strip();continue
 if caption and line.startswith('|'):
  put_caption()
 if caption and re.match(r'^#{1,3} ',line):
  put_caption()
 result.append(line)
 if caption and line.startswith('!['):
  put_caption()
put_caption()
source='\n'.join(result)+'\n'
# Keep provenance available at the end, so the first page leads with the investment argument.
provenance=[]
for pattern in (r'^\*\*原团队模型源提交\*\*.*\n', r'^\[源审阅稿\].*\n'):
 found=re.search(pattern,source,re.M)
 if found:
  provenance.append(found.group(0).strip())
  source=source[:found.start()]+source[found.end():]
source=re.sub(r'\n{4,}','\n\n\n',source)
source+='\n'+'\n\n'.join(provenance)+'\n'
source+='''
### 本版新增材料与责任记录

本版以团队2026-11-23归档稿及其图册数据为基础，接续图册2026-11-24对设备配套统计与首批现金零线的两处说明，参考基线提交6081db63f02627b0b464817bca86bf3b6b8a7abb。2026-11-24，用户明确选定柏楚电子，并选择沿用11月12日估值、保留期后跟踪。本轮续写市场叙事核验、治理和外部估值假设比较，三情景模型与归档输入不变。

八篇雪球文章的作者、链接、日期和处理见[材料核验](../docs/collaboration/members/lihuiyang/688188/材料核验.md)。两篇微信链接只取得验证页，未据其标题或正文推论。当前网页与后验说明不自动成为11月12日时点已知的事实。学生逐条核验、其他四位成员贡献、独立人类复核和团队最终采纳按实际行为补齐，本版不代签。

[原始归档报告](./柏楚电子证券投资分析报告11.23一版.md) · [本轮研究计划](../docs/collaboration/members/lihuiyang/688188/研究计划.md) · [本轮复算和交付](../docs/collaboration/members/lihuiyang/688188/复算与交付.md) · [版本生成程序](../docs/collaboration/members/lihuiyang/688188/build_report.py)
'''

# A fresh named version is intentional; rebuild is idempotent and refuses unrelated edits.
marker=HERE/'build-receipt.json'
if TARGET.exists():
 if not marker.exists() or json.loads(marker.read_text(encoding='utf-8')).get('report_sha256')!=hashlib.sha256(TARGET.read_bytes()).hexdigest():
  raise RuntimeError('Existing report changed outside the recorded build; preserve edits and create a new VersionN.')
 if TARGET.read_bytes()!=source.encode('utf-8'):
  raise RuntimeError('Inputs would change the existing report; preserve it and create the next VersionN.')
TARGET.write_text(source,encoding='utf-8',newline='\n')
receipt=dict(base_report=str(BASE.relative_to(ROOT)).replace('\\','/'),base_sha256=base_sha,
 report=str(TARGET.relative_to(ROOT)).replace('\\','/'),report_sha256=hashlib.sha256(TARGET.read_bytes()).hexdigest(),
 model_sha256=hashlib.sha256((ARCHIVE/'data/model.json').read_bytes()).hexdigest(),
 image_count=len(re.findall(r'!\[',source)),han_count=len(re.findall('[\u4e00-\u9fff]',source)),
 external_estimate=external,capex_minus_da_yuan=str(capex-da),cfo_less_capex_yuan=str(simple),
 cfo_parent_ratio=str(cfo/parent),cfo_group_ratio=str(cfo/net),weighted_controller_share=str(D(53339003+41718851+36194281+32384156+22859445)/D(288729927)),
 cutoff='2026-11-12 SSE close; user adopted 2026-11-24',status='draft-for-team-review')
marker.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='external_estimate'},ensure_ascii=False,indent=2))
