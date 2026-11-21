"""Figures and numerical sources for the company long-form atlas."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'docs/cases'
OUT = ROOT / 'docs/long-atlas'
NAMES = {'002507': '涪陵榨菜', '600298': '安琪酵母', '688188': '柏楚电子',
         '09992': '泡泡玛特', 'US': 'Intuitive Surgical'}
BRANDS = {
    '002507': ('榨菜、出货和渠道现金', '椒红', '#a04c36', '已有基准高于现价，现金增量要经过动销、回款和旧线替代检验。'),
    '600298': ('从吨毛利到工厂现金', '麦金', '#926729', '基准高于现价。新厂可售吨数与回款决定回报，较低折现率放大这项条件。'),
    '688188': ('从工艺控制到配套回报', '钢蓝', '#476d89', '基准略低于现价。系统续购与配套扣除服务和占款后的贡献决定能否跨价。'),
    '09992': ('从角色热度到库存现金', '藕紫', '#845779', '基准高于现价。IP 接力必须与成熟店动销、库存去化及现金租金同时兑现。'),
    'US': ('从医院装机到每例现金', '海青', '#22726e', '基准低于现价。只有装机、利用率和变现共同上升，平台的现金价值才接近现价。'),
}

MECHANISMS = {
    '002507': [
        ('出货和消费的距离','终端购买|经销补货|工厂确认收入','订单、出库与终端售出之间存在渠道库存；用实收和再订货验证销量。'),
        ('直销毛利变成现金的顺序','直销新增毛利|履约与促销|回款与库存|归属自由现金','同一履约费只扣一次；账期变化占用现金而非当期利润。'),
        ('新旧生产线如何交替','设计能力|实际利用|替代旧线|对外净增吨数','产出中替换旧线的部分按节约现金估计，净新增才按对外增量估计。'),
        ('两种渠道的成本边界','品牌获客|经销买断或直接履约|退换与收款|价格条件','把可归属增量从集团营销总额分开，现金费用上限与整股估值分别检验。'),
    ],
    '600298': [
        ('谁决定采购酵母','食品客户验证|配方或工艺适配|采购下单|验收后收款','跨配方转换需要验证批次稳定性；工业客户与零售小包装的成交条件不同。'),
        ('新厂产能怎样可售','工程投入|试运行与转固|客户认证|可售吨数与现金','转固触发折旧；可售吨数要在质量验证后才能开始贡献回款。'),
        ('从糖源到吨毛利','糖蜜与替代原料|发酵和能源|干燥运输|售价扣吨成本','同一产品族销售金额除以吨数带有组合效应，不能直接识别单品定价。'),
        ('资本回报如何穿越账期','项目资金|存货与应收|达产税后利润|回款抵资本成本','低折现率和高边际投入回报给出不同价格条件，应同时看厂级兑现。'),
    ],
    '688188': [
        ('谁把设备选型传给终端','设备厂选型|软件控制工艺|终端加工验证|下一批采购','同名套数能反映出货，按客户代际续购还需要同客户证据。'),
        ('控制加切割头如何形成增量','控制系统|软硬配套|硬件生产与保修|净毛利','硬件附加件抬高单套收入的同时，也改变综合毛利与备货要求。'),
        ('从备货到回款','订单预测|采购备货|发货验收|售后与收款','期末件数的周转代理应和应收期限对照，避免把交货积压当合理备货。'),
        ('核心经营与投资现金的分界','工业经营利润|剔除金融损益|经营资本与现金|非经营权益桥','经营税后利润折现；金融资产根据证券权利在权益桥处理。'),
    ],
    '09992': [
        ('角色如何变为销售','设计与授权|发行商品|渠道成交|回款与分成','新角色销售与既有角色接续同时观察，集团余额不能代替角色生命周期。'),
        ('如何区分开店和成熟经营','门店开业|进入完整经营期|成熟店流量与客单|净销售','期末店均营收混有开业时间、门店面积与渠道组合，需要批次资料识别。'),
        ('存货、折扣和租赁谁先占现金','采购备货|售罄或降价|回现金|支付固定与浮动租金','售罄率会同时影响折扣毛利和资金周转；租赁分类变化影响现金桥。'),
        ('季度区间如何走到证券价值','Q3同比区间|基期权重|Q4绝对额条件|每股现金估值','公告只有同比区间；先给权重假设再反推剩余收入。期后回购进入跟踪。'),
    ],
    'US': [
        ('医院从采购到日常使用','医院预算|装机与培训|使用科室排台|器械与服务采购','设备可用与手术排程是不同节点；耗材收入取决于术量和每例组合。'),
        ('两平台的术量分母','da Vinci外科机器人|Ion肺活检平台|合并器械耗材|合并每例代理','分别保留两类术量；合并每例是报表收入配合并术量的代理。'),
        ('租赁怎样拿回制造现金','制造与部署|固定／按量合同|回款与维护|合同回收阈值','固定租赁依赖合约；按量租赁依赖活跃设备使用，年度收入不等于合同累计回收。'),
        ('设备资产和现金的对应','存货制造现金|非现金转入设备|现金购建|租赁设备与股权价值','资产转入为非现金；诉讼计提与外部付款单列，以免重复扣减。'),
    ],
}

def readj(file):
    return json.loads(file.read_text(encoding='utf-8'))

def readcsv(file):
    with file.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def number(value):
    return float(value) if value not in (None, '') else None

def ratio(row, num, den, multiple=100):
    a,b=number(row.get(num)),number(row.get(den))
    return a/b*multiple if a is not None and b else None

def fields(rows, mapping):
    return [(name,[number(row.get(field)) for row in rows]) for field,name in mapping]

SPEC = {
 '002507': [
    ('渠道中哪些品类贡献增量毛利','channel-attribution.csv','dimension',[('gross_change_m','新增毛利')],'百万元人民币','直销与经销的品类贡献分别观察。收入贡献和毛利贡献的差额只在可归属费用清楚后才能称为净贡献。'),
    ('新基地实际产出与对外净增量','plant-utilization.csv','utilization',[('production_tonnes','基地生产'),('market_incremental_tonnes','对外净新增')],'吨','固定旧线替代为50%、每吨旧线节约为0的情景。净增销量取决于利用率及真实终端需求。'),
 ],
 '600298': [
    ('酵母及深加工吨成本与吨毛利','unit-economics.csv','period',[('unit_cost','吨成本'),('unit_gross','吨毛利')],'元／吨','同产品族金额除以销量，价格与结构混合。吨毛利继而影响新厂资本回报。'),
    ('重点项目的工程余额与转固','project-bridge.csv','name',[('h1_eop_cip_m','期末在建'),('h1_transfer_m','本期转固')],'百万元人民币','只显示 2026H1 工程已列报范围。转固以后能否达到可售吨数，须接认证和回款。'),
 ],
 '688188': [
    ('产品组新增收入与毛利留存','product-bridge.csv','group',[('sales_delta','收入变化'),('gross_delta','毛利变化')],'百万元人民币','用同产品组收入和毛利增量定位配套利润，跨组收入变化不等于客户续购。'),
    ('两类交付的期末库存天数代理','volume-and-stock.csv','period',[('control_finished_stock_days','控制系统'),('hardware_finished_stock_days','硬件')],'天','期末件数除以全年出货量。两类天数都增加时，需要新增订单与售后现金验证。'),
 ],
 '09992': [
    ('头部 IP 及其余 IP 的收入变化','ip-contribution.csv','group',[('delta_m','H1 同比收入变化')],'百万元人民币','跨期同名 IP 显示接续，保留合计和主要单项的层级关系。IP 组合变动不提供门店开业时点。'),
    ('门店数与店效代理的收入变化桥','store-cohort-proxy.csv','scope',[('change_count_m','门店数贡献'),('change_revenue_yield_and_cohort_m','销售强度与批次混合')],'百万元人民币','图中地理口径可能有包含关系。销售强度使用期末店数作分母，不能视为同店。'),
 ],
 'US': [
    ('两平台术量的增长来源','annual-unit-history.csv','period',[('da_vinci_proc','da Vinci'),('ion_proc','Ion')],'例','平台术量分别呈列，合并时用于耗材分母。折旧、维护按现金口径另桥。'),
    ('租赁合同的每台年化收入','lease-revenue-proxy.csv','period',[('yearized_revenue_per_end_unit_m','每期每台租赁收入代理')],'百万美元／台','用期末租赁台数，固定和按量不等于同一合同内现金。分母跨 da Vinci 和 Ion。'),
 ],
}

def figure(ident, title, unit, labels, series, source, reading, kind='line'):
    assert len(labels) > 0 and all(len(s[1]) == len(labels) for s in series), ident
    assert any(v is not None for _,values in series for v in values), ident
    return dict(id=ident,title=title,unit=unit,labels=labels,
                series=[dict(name=name,values=values) for name,values in series],
                source=source,reading=reading,kind=kind)

def available_url(code, file):
    return f'/cases/{code}/{file}'

def figures(code):
    raw=CASES/code
    history=readcsv(raw/'history.csv')
    timely=readcsv(raw/'interim.csv')
    model=readj(raw/'model.json')
    future=readcsv(raw/'forecast.csv')
    money=history[0]['unit']
    years=[r['period'][:4] for r in history]
    cases=(('stress','压力'),('base','基准'),('improve','改善'))
    def fig(ident,title,unit,labels,series,file,note,kind='line'):
        return figure(ident,title,unit,labels,series,available_url(code,file),note,kind)
    early=[
        fig('revenue','扩张、压力与转折的收入轨迹',money,years,fields(history,[('revenue','营业收入')]),'history.csv',
            '连续收入定位规模变化。断点及各期来源位于下表和原历史文件，金额跨准则时照原口径。'),
        fig('margins','报告毛利率与核心经营利润率','%',years,[('合并毛利率',[ratio(r,'gross_profit','revenue') for r in history]),('分析经营利润率',[ratio(r,'analysis_ebit','revenue') for r in history])],'history.csv',
            '由同年合并收入计算。两条线差额对应销售管理等费用与核心口径调整，空点保留原表缺项。'),
        fig('cash','经营现金、现金购建和余额',money,years,fields(history,[('cfo_reported','报告经营现金流'),('cash_capex','现金购建付出'),('cfo_minus_capex','CFO减现金购建')]),'history.csv',
            '经营净现金与现金购建的差值仍含经营资本和其他项目变化。泡泡玛特融资租赁在单独桥处理；ISRG非现金转入与现金购建分列。'),
        fig('wc','经营性营运资本占收入','%',years,[('可见营运资本／收入',[ratio(r,'wc_trade_subset','revenue') for r in history])],'history.csv',
            '可见余额使用各公司定义的应收、存货、预收和应付子集。分子是期末存量，现金影响取同口径变动。'),
        fig('capital','经营资本回报与新增投入差额','%',years,[('代理ROIC',[None if r['roic_subset']=='' else float(r['roic_subset'])*100 for r in history]),('新增投入回报代理',[None if r['incremental_return_paired']=='' else float(r['incremental_return_paired'])*100 for r in history])],'history.csv',
            'ROIC 是税后核心利润除以同范围资本。新增投入代理是可用期间利润变动相对于资本增加，受项目投产时滞影响。'),
    ]
    recent=[r for r in timely if r['metric']=='revenue']
    early.append(fig('interim','从历年同期识别最近收入信号',money,[r['period'] for r in recent],
                  fields(recent,[('cumulative','累计收入'),('single_period','单期收入')]),
                  'interim.csv','拆分累计与单期。累计覆盖期不同，判断变化时用同季度或同半年度比较。','bar'))
    for i,(title,file,key,mapping,unit,note) in enumerate(SPEC[code],1):
        rows=readcsv(raw/file)
        if file=='plant-utilization.csv':
            rows=[r for r in rows if number(r['replacement'])==0.5 and number(r['assumed_old_line_savings_per_tonne'])==0]
        elif file=='project-bridge.csv':
            rows=[r for r in rows if r['available'] and r['available'][:10]<=model['cutoff']]
        elif file=='unit-economics.csv':
            rows=[r for r in rows if r['product']=='酵母及深加工']
        elif file=='ip-contribution.csv':
            rows=[r for r in rows if r['group'] in ('THE MONSTERS','星星人','CRYBABY','SKULLPANDA','MOLLY') or '剔除' in r['group']]
        name=lambda r: r[key]+(' '+r['contract'] if 'contract' in r else '')
        early.append(fig('special-'+str(i),title,unit,[name(r) for r in rows],fields(rows,mapping),file,note,'bar'))
    path_years=list(range(2027,2032))
    for ident,title,column,note in (
        ('forecast-revenue','经营驱动形成三条收入路径','revenue','2026实际和剩余期分栏另见专项表。图中各情景由业务驱动形成，远期以稳定期为目标。'),
        ('forecast-cash','三条路径每年的截点后自由现金','model_cash_after_date','逐年经营税、折旧、资本支出和营运资本相扣。终值及估值日前已实现现金均未画入本图。')):
        lookup={(r['scenario'],int(r['year'])):r for r in future}
        early.append(fig(ident,title,money,path_years,
                    [(label,[number(lookup[case,y][column]) for y in path_years]) for case,label in cases],
                    'forecast.csv',note))
    munit=model['security']['quote']+'/股'
    early.append(fig('price','同日价格和三条每股路径',munit,[*[name for _,name in cases],'同日收盘'],
                [('每股',[*[model['cases'][case]['per_share'] for case,_ in cases],model['close']])],
                'model.json','三情景只用估值截点前可得披露。每股报价保留原市场币种，比较页同时显示相对收盘。','bar'))
    bridge=readcsv(raw/'value-bridge.csv')
    early.append(fig('value-bridge','阶段17冻结值到本版的逐项差额',munit,
                [r['step'] for r in bridge[1:]],fields(bridge[1:],[('delta','每步对每股影响')]),
                'value-bridge.csv','每项差额按现金流、折现、终值与权益的公开顺序计算。阶段15原值和阶段17冻结值在底表并列可追溯。','bar'))
    tests=model['tests']
    matrix=tests['matrix']
    xs=list(dict.fromkeys(r['x'] for r in matrix))
    ys=list(dict.fromkeys(r['y'] for r in matrix))
    lookup={(r['x'],r['y']):r['value'] for r in matrix}
    early.append(fig('reverse','不同经营条件下如何穿越现价',munit,[f'{x:.5g}' for x in xs],
                [(f'{tests["y"]} {y:.5g}',[lookup[x,y] for x in xs]) for y in (ys[0],ys[len(ys)//2],ys[-1])] +
                [('同日收盘',[model['close']]*len(xs))],
                'sensitivity.csv',f'横轴为{tests["x"]}。{tests["condition"]}同源反解表保留无根条件与可回代边界。'))
    if code=='600298':
        file=OUT/code/'early-capital.csv'
        e=readcsv(file)
        early.append(figure('historical-addon','旧准则扩产期的税前经营回报','%', [r['period'] for r in e],
                [('税前经营资本回报代理',[100*float(r['pretax_roic_proxy']) for r in e]),
                 ('分析经营利润率',[100*float(r['analysis_ebit_margin']) for r in e])],
                '/long-atlas/'+code+'/'+file.name,
                '主营成本、财务费用及旧准则固定资产与净营运资本逐行对回原件。早期项目时滞验证不进入现代参数校准。'))
    if code=='09992':
        file=OUT/code/'historical-lease-cash.csv'
        e=readcsv(file)
        early.append(figure('historical-addon','两类租赁现金与租后资本开支余额','百万元人民币',[r['period'] for r in e],
                [(n,[float(r[f])/1000 for r in e]) for f,n in (('operating_lease_cash','经营租赁现金'),
                    ('financing_lease_cash','融资租赁现金'),('after_rent_cfo_and_capex','租金和现金资本开支后余额'))],
                '/long-atlas/'+code+'/'+file.name,
                'CFO已过经营分类租赁，只追加扣融资分类与现金购建。各年度使用权折旧和可变租赁保留原版与比较。'))
    if code=='002507':
        file=OUT/code/'channel-current-price.csv'
        e=readcsv(file)
        joint=[r for r in e if r['root']]
        early.append(figure('historical-addon','伴随直销费用与资金占用的销量阈值','集团销量增速的附加百分点',
                [r['halfyear_fee_m']+'／'+r['incremental_capital_m'] for r in joint],
                [('回到11.42元的销量偏移',[100*float(r['root']) for r in joint])],
                '/long-atlas/'+code+'/'+file.name,
                '横轴为半年度附加费用／资本附加占用（百万元）。−13至+3百分点检验有九根；仅费用和资本域无根。','bar'))
    return early

COVER_FIELDS = [
    ('收入及增速', ('revenue','revenue_growth'),'history.csv'), ('成本及毛利',('cost','gross_profit'),'history.csv'),
    ('核心经营利润',('report_operating_profit','analysis_ebit'),'history.csv'),
    ('经营现金与资本支出',('cfo_reported','cash_capex'),'history.csv'),
    ('营运资本',('wc_trade_subset','delta_wc_trade_subset'),'history.csv'),
    ('资本与回报',('capital_subset','roic_subset'),'history.csv'),
]
def field_coverage(code):
    records=readcsv(CASES/code/'history.csv')
    rows=[]
    for label,metrics,file in COVER_FIELDS:
        for metric in metrics:
            observed=[r for r in records if r.get(metric) not in ('',None)]
            windows=list(dict.fromkeys(r['stage'] for r in records[:]))
            periods=[r['period'] for r in observed]
            # Each source disclosure keeps its version, PDF locator, source ID and table header in locators.
            rows.append(dict(company=code,group=label,field=metric,first=next(iter(periods),''),
                        last=next(reversed(periods),''),comparable_count=len(observed),
                        missing='、'.join(r['period'] for r in records if r not in observed),
                        stages='／'.join(windows),entry=available_url(code,file),
                        locations='history.csv 的 source_id、filed、sha256、locators；核心及资本派生字段使用原组件定位'))
    for name,file,key,mapping,unit,_ in SPEC[code]:
        rec=readcsv(CASES/code/file)
        for metric,label in mapping:
            observed=[r for r in rec if r.get(metric) not in ('',None)]
            windows=[r.get('period') or r.get('period_label') or r.get('published') or r.get('scope') or r.get('source') or r.get(key,'') for r in observed]
            rows.append(dict(company=code,group=name,field=label,first=next(iter(windows),''),
                             last=next(reversed(windows),''),comparable_count=len(observed),
                             missing='、'.join(str(r.get(key,'')) for r in rec if r not in observed),
                             stages=unit,entry=available_url(code,file),locations='原专题表 source、口径及有条件代理列'))
    additions = {
        '600298': ('early-capital.csv', ('cost','analysis_ebit_m','wc_narrow_m','capital_narrow_m','pretax_roic_proxy')),
        '09992': ('historical-lease-cash.csv', ('operating_lease_cash','financing_lease_cash','rou_da','after_rent_cfo_and_capex')),
    }
    if code in additions:
        file,metrics=additions[code]
        additional=readcsv(OUT/code/file)
        for field in metrics:
            filled=[r for r in additional if r.get(field) not in ('',None)]
            rows.append(dict(company=code,group='本版逐页核对补充',field=field,first=filled[0]['period'],
                             last=filled[-1]['period'],comparable_count=len(filled),
                             missing='、'.join(r['period'] for r in additional if r not in filled),
                             stages='旧会计制度；2007起分段' if code=='600298' else 'IFRS使用权及租赁现金流分类',
                             entry='/long-atlas/'+code+'/'+file,
                             locations='/long-atlas/'+code+'/historical-original-locators.csv'))
    index={
      '002507': [('unit-economics.csv','销量及实现均价')],
      '600298': [('dimension-panel.csv','产品与地区收入和成本')],
      '688188': [('volume-and-stock.csv','控制与配套销量／库存')],
      '09992': [('region-channel-bridge.csv','地区渠道收入')],
      'US': [('annual-unit-history.csv','双系统术量与收入')],
    }
    for file,label in index[code]:
        observed=readcsv(CASES/code/file)
        periods=sorted({r['period'] for r in observed}) if 'period' in observed[0] else ['2025-H1','2026-H1']
        rows.append(dict(company=code,group='经营数据覆盖',field=label,first=periods[0],last=periods[-1],
                         comparable_count=len(observed),missing='覆盖表仅计原表观察行，拆分缺项见源表说明',
                         stages='产品、地区或公司专项口径',entry=available_url(code,file),
                         locations='源表期间列、行组说明与来源定位'))
    return rows
