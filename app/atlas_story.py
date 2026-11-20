"""Editorial judgments linked to the released scenarios and primary-source tables."""

from math import isclose


STORIES = {
    '002507': {
        'label': '现金基准高于收盘',
        'mechanism': '榨菜复购和经销覆盖仍能留下现金',
        'trigger': '直销增量现金持续为负，且新基地净增量无法覆盖购建',
        'sections': {
            'customer': ('复购、发货和回款是一条链',
                '家庭和餐饮客户为熟悉口味、稳定规格和附近买得到付钱。经销商把货铺到终端，公司先承担采购、腌制与库存，然后发货、确认收入并收回货款。基准保留既有铺货和复购的现金贡献，直销提升能否留住毛利则取决于履约费用和信用占用。'),
            'annual': ('从全国铺货到产能先行',
                '2010–2015 年经销铺货阶段，收入由 5.45 增至 9.31 亿元。规格与量价升级后，2016–2020 年阶段中位经营现金率由前一阶段的 21.14% 提至 34.39%。2021–2022 年提价与原料时点放大盈利，2023–2025 年收入从 24.50 亿元走到 24.32 亿元，阶段中位经营现金率回到 27.02%。这组数据支持存量渠道盈利，扩建后的真实增量需要用净新增吨数和回款验证。'),
            'recent': ('直销毛利多了，款是否收回',
                '2026H1 食品四品类披露销量合计约 7.33 万吨，上年同期约 7.09 万吨。直销收入 0.74 → 1.22 亿元，毛利 0.34 → 0.55 亿元；经销收入 12.37 → 12.41 亿元，毛利 6.76 → 6.68 亿元。直销新增毛利 21.09 百万元，同口径经销毛利少 7.52 百万元。前三季集团销货收现 2,117.13 → 2,156.74 百万元，9 月应收 120.88 → 143.58 百万元，集团口径含税费及回款期差。发货和应收同步上行，基准据此保留既有经销现金，单独给直销分摊费用和占款。'),
            'cash': ('先用净新增吨数，再算渠道留下的现金',
                '公司收入由销量乘组均价和结构取得。毛利扣可归属履约和销售费用得到经营利润，扣税后再按发货到收现时序计入应收、库存和购建。新基地利用率为 35% 的条件下，替代旧产量的份额从 50% 提到 80%，净增由 2.80 万吨降至 1.12 万吨，未扣营运资本、未计旧线节约的现金由 +77.55 降到 −28.98 百万元。使用净新增吨数可把替代旧线与新增需求分开。'),
            'follow': ('费用和基地净新增量共同决定安全边际',
                '最有力的反方是新增直销依赖赊销，基地主要替代旧产量。给定贸易占用与净购建各 5 百万元，直销新增税前现金在分摊费用超过 11.09 百万元时转负。若渠道增量持续耗现、基地净增量无法覆盖购建，使用 11.00 元压力值，低于 11.42 元收盘。下一期可对读分渠道毛利、应收及销货收现、基地试产与旧线退出时间。'),
        },
    },
    '600298': {
        'label': '基准高于收盘，厂级回报待兑现',
        'mechanism': '认证复购能支撑发酵产线回报',
        'trigger': 'WACC 为 7.50% 时，稳定新增 ROIC 低于 11.75%',
        'sections': {
            'customer': ('投产之后还要过客户认证',
                '工业客户为稳定发酵效果、批次一致性和适配配方付款。安琪先投入工厂，再完成品种和客户认证，形成可重复的合格供货。基准采用可观察的集团销量和吨经济性，厂级可售量与回报用转固、客户认证和回款单独验证。'),
            'annual': ('产能扩张能带动收入，现金效率有阶段差',
                '2001–2006 年为扩产及旧准则期，2007–2012 年多基地放量，2013–2019 年叠加深加工与海外业务。2020–2021 年需求与原料变动后，2022–2025 年收入从 128.43 增至 167.29 亿元，阶段中位经营现金率为 10.29%，低于 2013–2019 年的 16.93%。扩张后收回资本需要单独验证。2025 年酵母及深加工每吨毛利约 8,226 元，是集团分部多个产品和地区的组合。'),
            'recent': ('库存天数缩短，经营现金减购建仍下降',
                '2025 年披露印尼项目建设进度。2026H1 发酵产量 25.4 万吨、同比增 11.6%，全集团发酵年产能 49 万吨，厂级已认证可售量仍需按投产批次对应。按期末余额和 273 天累计流量估算，前三季库存天数 144.7 → 131.9，应收天数 35.4 → 37.3，应付天数 55.5 → 52.1。同期经营现金减现金购建从 977.62 降到 407.19 百万元。集团库存天数下降与回款变慢可同时发生，基准将两项占用分开。'),
            'cash': ('以已认证可售吨数和营业利润推到回款',
                '产线转固后，客户认证放开的可售吨数乘吨价进入收入。吨毛利再扣折旧与相关费用得到营业利润，扣税后配对库存、应收及现金购建。按新增资本占用 300 百万元、年可售 3 万吨，11.2% 的新增回报需 33.6 百万元税后营业利润或每吨 1,427 元税前营业利润。只有实际转固、售出及收现匹配，才能把集团组合利润收敛到厂级新增回报。'),
            'follow': ('用新增回报与融资成本联判价差',
                '最有力的反方是原料周期和投产推动吨毛利改善，而账期与投资延迟让可分配现金减少。在 7.50% WACC 下，稳定新增 ROIC 11.2% 得 36.06 元，13.0% 得 37.71 元，临界 11.75% 对应 36.62 元。11 月 17 日董事会公告把预算由 215.24 调为 236.53 百万元，13.69% 是初步预计项目收益，公告在冻结估值日之后。按项目投产公告及年报追踪转固、实际投资、认证、可售吨数、吨利润、库存和客户回款。'),
        },
    },
    '688188': {
        'label': '经营基准低于收盘',
        'mechanism': '控制系统复购仍能产生现金，配套与备货提高兑现门槛',
        'trigger': '控制销量增速达到 7.53%，或稳定核心利润率达到 49.80%',
        'sections': {
            'customer': ('把接口和工艺做进设备，客户复购时才兑现',
                '设备厂为控制系统、切割工艺和现场适配付钱。工程接口、工艺参数和售后服务积累有利于复购，既有客户续单和新设备订单最终都表现为出货。基准使用可核的控制系统销量，配套件另外承担毛利、售后和库存。'),
            'annual': ('控制系统增长经过设备周期的反例',
                '2019–2021 年控制系统放量，收入由 3.76 增到 9.13 亿元。2022 年回到 8.98 亿元，显示设备订单的需求周期。2023–2025 年控制与配套共同增长，收入升至 21.96 亿元，阶段中位经营现金率 54.88%，低于 2019–2021 年的 63.50%。2024 → 2025 年控制系统销量 60,993 → 65,064 套，智能硬件 35,118 → 56,824 套，主营毛利率 80.53% → 77.92%。配套带来的收入增长已出现，配套净毛利仍须扣除售后并确认占款。'),
            'recent': ('用核心利润与库存验证硬件扩张',
                '2026 年前三季报告营业利润 1,226.03 百万元，收入扣除成本、销售、管理、研发及税附后的核心经营利润为 938.19 百万元。利息、投资和公允价值净收益分别为 91.06、17.06 和 46.97 百万元，放在经营之外单列。9 月存货从 216.23 增到 403.39 百万元，期末成本周转代理从约 166 天延长至 216 天。基准用系统销量和稳定核心利润率约束经营，把备货放进增量营运资金。'),
            'cash': ('控制量价和配套净贡献约束自由现金流',
                '控制系统销量乘每套净收入，加配套设备和服务形成销售。各类收入扣成本和可归属售后费用，再扣现金税及新增库存、应收和净购建。备货天数单独缩短 60 天的每股值为 93.14 元。现价跨线需控制系统续购或配套净毛利也改善。'),
            'follow': ('559 套相当量能否来自老客户续单',
                '最有力的反方是配套附着率、大客户续购和规模毛利同时改善。其他基准输入固定，控制销量缺口约 559 套 2025 年销量当量，或稳定核心利润率由 46.96% 提到 49.80%。若全部由占收入 25% 的软硬配套贡献，毛利率须增加 11.37 个百分点；若只靠售后，需节省年化税前约 148.58 百万元。用下期控制系统和智能硬件销量、整套方案毛利、售后费和存货追踪。11 月 16 日分派税前 0.582 元/股，固定其余因素的机械除息基数为 95.618 元，基准按同口径移至 92.176 元，保留原有价差方向。'),
        },
    },
    '09992': {
        'label': '条件基准高于收盘，门店现金最关键',
        'mechanism': '头部 IP 之外的集团销售能支持产品接续',
        'trigger': '实际 Q4 收入低于租金与库存周转对应的临界线',
        'sections': {
            'customer': ('角色吸引首购，IP 接续决定复购',
                '收藏和礼赠客户为角色设计及系列体验付款。公司组织开发、生产和发行，用门店与渠道接触客户，先承担备货、折扣和租金，再从销售收回投入。基准采用已观察的头部 IP 之外的集团销售与门店组合，将成熟店店效、折扣和租金拆开验证。'),
            'annual': ('早期门店扩张、需求放慢和海外加速',
                '2020–2021 年自主 IP 和门店增长，收入 25.13 → 44.91 亿元。2022–2023 年需求放缓后恢复，阶段中位核心利润率 14.53%。毛绒和海外扩张使 2024–2025 年收入从 130.38 升至 371.20 亿元，同期经营现金率从 38.00% 降至 29.27%。利润增长和现金吸收的区别，进入后续租赁与库存模型。'),
            'recent': ('IP 接续有证据，成熟店仍要独立衡量',
                '2026H1 剔除 THE MONSTERS 后集团收入增长 40.35%；中国区实体门店销售除以平均门店数增长 34.22%，为混合店龄代理。同期集团毛利率 70.34% → 69.68%，年化库存周转 4.33 → 1.80，H1 现金租金 12.11 亿元。之后 Q3 业务公告给出集团未经审计收入同比下降 45%–50%，把 Q4 兑现提升为价格验证条件。'),
            'cash': ('先看每批门店的收入，再扣租金及库存',
                'IP 发行和上架形成动销，店龄结构与折扣影响售价及毛利，租金进入经营利润与现金税，补货和滞销反映在库存占用。基准以门店证据替换集团收入误差回填并统一现金租金口径，调整先作用于同店与库存，租金口径贯穿显式期及终值。'),
            'follow': ('Q4 在不同租金和库存组合下有不同门槛',
                '最有力的反方是新店新区域和铺货抬高集团增长，成熟门店毛利经折扣后走弱。给定上年 Q3 占 H2 的 50%、库存周转 1.80 次、H2 现金租金 8.53 亿元，143.40 港元要求 Q4 收入 20.96–26.77 亿元；周转降至 1.35 次、H2 现金租金约 10.51 亿元，门槛升至 35.64–41.45 亿元。核全年及租赁附注的绝对销售、现金租金和周转，并核成熟店批次。六份收盘后回购的股数及现金同时变化，固定模型其余项，基准机械从 166.654720 到 166.696839 港元/股。'),
        },
    },
    'US': {
        'label': '现价高于三条发布路径',
        'mechanism': '手术使用带来耗材和服务复购，租赁还须覆盖每台制造及维护',
        'trigger': '8% WACC 下装机／每台术量达到 13%／10.62% 或 16%／6.55%，且租赁回收兑现',
        'sections': {
            'customer': ('装机是入口，医院安排手术才创造重复收入',
                '医院购买器械、维护、装机和设备使用权。术式培训、器械供给和流程稳定度有利于重复使用。设备一旦租出，公司先付制造和维护现金，之后靠固定租金、术量收费和独立耗材销售回收资本。'),
            'annual': ('手术波动说明装机和收入之间有利用率',
                '2015–2019 年装机带动耗材与服务，收入由 23.84 增到 44.79 亿美元。2020 年择期手术受冲击，收入回到 43.58 亿美元；2021–2023 年术量恢复并增加设施投资，2024–2025 年又进入新平台及租赁扩张。2023–2025 年装机年复合增 13.60%、每台平均装机术量增 2.97%、每合并病例耗材收入变动 −0.06%。采用装机增长作为供给线索，单独约束医院利用率与单例变现。'),
            'recent': ('耗材、服务、销售和租赁分列',
                '2026Q3 da Vinci 期末 12,094 台，上年同期 10,763 台；前三季 da Vinci、Ion 术量约增 15%、35%。同期耗材 5,218.7、服务 1,388.3、销售及买断 1,317.8、固定租赁代理 283、按量租赁代理 504 百万美元。按平均活跃装机推 da Vinci 术量，用 da Vinci 加 Ion 的组合病例乘每例耗材收入；租赁收入则区分按时间或按使用。固定和按量采用经营租赁的会计披露代理。'),
            'cash': ('租赁出货先花制造现金，再由利用率驱动回收',
                '单位租赁制造现金和维护回收单算。10-Q 披露库存转设备 670.5 百万美元为非现金转列；现金购建 329 百万美元，库存占用经营现金 822 百万美元，拟议和解应计 450 百万美元。模型按设备新租赁量乘单位制造现金单列再投入，和解从经营现金假设剥离后单列权益现值。后续法院批准、实际付款及单套制造现金仍取决于独立证据。'),
            'follow': ('医院利用率与单台租赁回收须一起跨线',
                '最有力的反方是新平台带动装机与手术密度长期加速。在 8% WACC、单台制造现金 0.85 百万美元下，装机增速 13%／16% 分别需每台活跃术量增速 10.62%／6.55%，每例变现增速 1.5%／2.0%，才能到 439.89 美元。若每台五年回收、年维护 0.10 百万美元、残值为零，需年租赁现金 0.313 百万美元；10-Q 年化固定、按量代理为 0.223、0.295。单位制造现金若升至 1.03 百万美元，两条同价路径降至 435.25／434.41 美元。下一期按两类装机、独立术量、租赁实际收款及现金购建比对。'),
        },
    },
}


OBSERVED_BRIDGES = {
    '002507': '2024→2025 年食品收入增加 44.91 百万元，其中量贡献 25.26、组均价与结构贡献 19.65。该年增量依靠量与组合共同兑现。2026H1 切到渠道毛利后，品类量价和渠道结构使用同一笔收入的两个切面，各自再核费用和回款。',
    '600298': '2024→2025 年酵母及深加工收入增加 1,094.69 百万元，销量贡献 +1,675.99，组均价与结构 −581.29。增量由实物量拉动，因此采用售出吨数推收入，吨价和产品结构另设，再由吨毛利扣费用检验转化。',
    '688188': '2024→2025 年合并收入增约 460.18 百万元。平面、管材、三维、其他主营及其他业务依次贡献 168.10、107.22、27.12、146.34 和 11.41 百万元。年报其他主营跨多项业务，配套件贡献用其独立销量、毛利与售后重新约束。',
    '09992': '2025H1→2026H1，THE MONSTERS 收入减少 359.66 百万元，其余集团收入增加 3,656.30 百万元。产品接续有集团销售的支持，门店批次、原价动销和现金租赁回报各自进入后续验证。',
    'US': '2024→2025 年总收入增加 1,712.6 百万美元。耗材、设备、服务依次贡献 939.9、507.7、265.0 百万美元。耗材和服务支撑采用使用量驱动；系统收入中买断、固定与按量租赁的现金时序随后逐项拆开。',
}

CASH_CHAINS = {
    '002507': ['食品发货与净价','直销与经销毛利','费用与应收、收现','基地净增与现金购建'],
    '600298': ['投用及客户认证','可售吨数与吨毛利','库存、应收与回款','新增资本回报与现金'],
    '688188': ['控制系统复购与新装','配套净毛利及售后','库存、应收和现金税','核心自由现金流'],
    '09992': ['IP接续与成熟店动销','折扣后销售及毛利','现金租金及补货','税后自由现金流'],
    'US': ['活跃装机与每台术量','每例耗材、服务和租赁','制造与维护现金','税后自由现金流'],
}

PRICE_CONTEXT = {
    '002507': '基准其他量价、折现率与权益条件固定，同日收盘反解稳定营业利润率 15.86%，对应 EBIT 511.64、FCFF 333.90 百万元。',
    '600298': '基准稳定新增 ROIC 为 11.2%，同日价的 WACC 临界线是 7.44%。新增 ROIC 为 8%／18% 时，临界 WACC 为 6.97%／7.89%。',
    '688188': '冻结其他经营与权益条件，收盘要求 2027 控制系统销量增速由 6.675% 提到 7.533%，或稳定核心营业利润率由 46.96% 升到 49.80%。',
    '09992': '收盘对应的是 Q4 收入与现金租金、周转共同满足的条件。Q3 公布的是增长区间，绝对季度收入仍用情景权重反解。',
    'US': '三条发布情景的上沿仍低于收盘。反推可用 8% WACC 的两条经营路径；基准 9.77% WACC 下，在搜寻的利用率增长 −3% 到 12% 区间无交点。',
}

CURRENCIES = {'CNY':'元','HKD':'港元','USD':'美元'}


def _thesis(story, model):
    price = model['price']
    quote = CURRENCIES[model['market']['quote']]
    cases = model['cases']
    base = cases['base']['per_share']
    if price > cases['improve']['per_share']:
        return f"{story['mechanism']}，{price:.2f} {quote}收盘已超过三条发布情景的上沿 {cases['improve']['per_share']:.2f} {quote}。"
    side = '高于' if base > price else '低于'
    return f"{story['mechanism']}，条件基准 {base:.2f} {quote}{side}同日收盘 {price:.2f} {quote}。"


def _cash_summary(base):
    row = next(row for row in base['rows'] if row['year'] == 2027)
    title = '2027 年基准现金桥（报告币种百万元）'
    if 'volume_sales_delta' in row:
        detail = f"销量和组均价或结构对收入的模型贡献依次为 {row['volume_sales_delta']:+,.2f} 与 {row['price_mix_sales_delta']:+,.2f}。"
    elif 'cash_rent_fixed' in row:
        detail = f"门店容量增长假设 {row['store_capacity_growth']:.1%}，固定及经营现金租金分别 {row['cash_rent_fixed']:,.2f} 与 {row['cash_rent_operating']:,.2f}，已进入模型。"
    else:
        detail = f"租赁装机对应的独立制造现金 {row['cash_manufacturing']:,.2f} 已在净再投入内。"
    return title+(
        f"。收入 {row['revenue']:,.2f}，税前营业利润 {row['operating_profit']:,.2f}，"
        f"现金税 {row['cash_tax']:,.2f}，税后经营利润 {row['nopat']:,.2f}。"
        f"营运资本变动 {row['delta_wc']:+,.2f}，净再投资 {row['net_reinvestment']:,.2f}，"
        f"当年自由现金流 {row['model_cash_after_date']:,.2f}。{detail}"
    )


def _equity_table(model):
    market = model['market']
    base = model['cases']['base']
    bridge = base['bridge']
    value = (base['enterprise_value']+bridge['bridge_net'])*1e6/market['fx']/market['shares']
    if not isclose(value,base['per_share'],rel_tol=1e-9):
        raise ValueError(f"{model['company']} equity bridge is inconsistent")
    return {
        'title':'基准权益桥 · 现金流现值如何成为每股价值',
        'columns':['项目','金额或口径'],
        'rows':[
            ['显式期现金现值（报告币种百万元）',base['enterprise_value']-base['terminal']['pv']],
            ['终值现值（报告币种百万元）',base['terminal']['pv']],
            ['企业价值（报告币种百万元）',base['enterprise_value']],
            ['可分配现金代理',bridge['excess_cash_proxy']],
            ['扣有息负债',-bridge['financial_debt']],
            ['扣按融资处理租赁',-bridge['finance_treated_lease']],
            ['扣少数股东权益代理',-bridge['non_controlling_deduction']],
            ['扣独立和解现值',-bridge['litigation_separate_pv']],
            ['股东价值（报告币种百万元）',base['equity']],
            ['一报价币折报告币',market['fx']],
            ['估值证券股数',market['shares']],
            ['每股价值（报价币）',base['per_share']],
        ],
    }


def _price_summary(code, model):
    base = model['cases']['base']
    bridge = model['bridge']
    price = model['price']
    wacc = base['wacc']
    ratio = base['terminal']['pv_share']
    quote = CURRENCIES[model['market']['quote']]
    steps = '、'.join(f"{row['step']} {row['change']:+.2f}" for row in bridge)
    return (
        f"{PRICE_CONTEXT[code]}\n\n"
        f"基准以 {wacc:.2%} 折现经营自由现金流。稳定期增长 {base['terminal']['growth']:.1%}、新增回报 {base['terminal']['incremental_return']:.1%} 一起决定稳定再投入，终值现值占企业价值 {ratio:.1%}。"
        f"再按报告币种加可分配现金、扣负债及其他权益请求，换为报价币后除估值股数。"
        f"基准每股 {base['per_share']:.2f} {quote}，相对 {price:.2f} {quote}收盘 {base['per_share']/price-1:+.1%}。"
        f"阶段 15 的 {bridge[0]['start']:.2f} {quote}依次经历每股变动（{steps}），"
        f"到阶段 17 发布的 {bridge[-1]['end']:.2f} {quote}。"
    )


def apply_stories(doc, models):
    """Apply a common company judgment to the reading card and its overview references."""
    by_code = {model['comparison']['code']:model for model in models}
    card_by_code = {}
    for card in doc['cards']:
        if not card['id'].startswith('company-'):
            continue
        code = card['id'].removeprefix('company-')
        if code not in STORIES:
            continue
        if card.get('judgment', {}).get('editorial_version') == 1:
            card_by_code[code] = card
            continue
        model = by_code[code]
        story = STORIES[code]
        base = model['cases']['base']
        canonical = _thesis(story,model)
        card['body'] = canonical
        card['feature']['summary'] = canonical
        quote = CURRENCIES[model['market']['quote']]
        card['judgment'] = {
            'editorial_version':1,
            'label':story['label'],
            'mechanism':story['mechanism'],
            'price':model['price'],
            'price_text':f"{model['price']:.2f} {quote}",
            'base':base['per_share'],
            'direction':'above' if base['per_share']>model['price'] else 'below',
            'valuation_date':model['valuation_date'],
            'trigger':story['trigger'],
            'summary':canonical,
        }
        sections = {section['id']:section for section in card['feature']['sections']}
        for section_id,(title,text) in story['sections'].items():
            section = sections[section_id]
            section['title'] = title
            section['body'] = text
        sections['recent']['annotation'] = ''
        sections['mechanism-bridge']['body'] = OBSERVED_BRIDGES[code]
        sections['cash']['chain'] = CASH_CHAINS[code]
        sections['cash']['body'] += '\n\n' + _cash_summary(base)
        sections['price']['title'] = '自由现金流怎样变成每股价值'
        sections['price']['body'] = _price_summary(code,model)
        sections['price']['tables'].append(_equity_table(model))
        card_by_code[code] = card

    for card in doc['cards']:
        if card['id'] not in ('overview','valuation'):
            continue
        for part in card['feature']['sections']:
            if part['id'] != 'range':
                continue
            table = part['tables'][0]
            if table['columns'][-2:] == ['同一主判断','翻转阈值']:
                continue
            table['columns'][-1:] = ['同一主判断','翻转阈值']
            for row in table['rows']:
                code = row[0]['href'].split('company-')[-1]
                ref_card = card_by_code[code]
                row[-1:] = [ref_card['feature']['summary'], ref_card['judgment']['trigger']]

    for chart_map in doc.get('maps', []):
        for node in chart_map['nodes']:
            linked = node.get('card_id') or ''
            if linked.startswith('company-') and linked.removeprefix('company-') in card_by_code:
                node['detail'] = card_by_code[linked.removeprefix('company-')]['feature']['summary']
    return doc
