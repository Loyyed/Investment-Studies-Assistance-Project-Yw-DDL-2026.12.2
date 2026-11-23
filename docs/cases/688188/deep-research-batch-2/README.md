# 柏楚电子证券投资分析审阅稿｜第二批

**阅读入口。** [40 页 PDF](review.pdf) · [连续 HTML](review.html) · [单文件 Markdown](review.md) · [可编辑九章](chapters/) · [独立复核](data/independent-audit.json)

研究日 2026-11-23，冻结估值仍为 2026-11-12 上交所含权未复权收盘。基线为首批 `f354d3c65baabc77e8760c3bf277ca10d7d75755`。第二批责任范围为本目录及旧报告地图入口，发行人原件、事实账本、原估值和第一批结果按原版保留。当前是团队审阅稿。

## 证据和模型地图

| 研究环节 | 底表与可复核定位 |
| --- | --- |
| 历史与会计 | [逐年报告证据](data/annual-evidence.csv)、[上市前段](../deep-research-batch-1/pre-ipo.csv)、[原件指纹](../deep-research-batch-1/originals.csv)、[原表单元格](../deep-research-batch-1/filing-cells.csv)、[个别报告原列／重述／采用值](../deep-research-batch-1/restatement-bridge.csv) |
| 收入和毛利 | [2023 原产品](data/2023-product-original.csv)、[应用组反推区间及成本重列](data/group-restatement.csv)、[地区、渠道、主营及合并勾稽](../deep-research-batch-1/classification-check.csv)、[主业毛利贡献](data/gross-contribution.csv)、[材料、人员、制造](data/cost-attribution.csv) |
| 近期利润与现金 | [核心 EBIT 和股东利润](data/recent-income-bridge.csv)、[经营现金收付](data/cfo-change.csv)、[现金历史](data/cash-history.csv)、[周转](data/trade-days.csv)、[资金占用和 ROIC](data/capital-returns.csv)、[配套转正条件](data/bundle-cash-thresholds.csv) |
| 募投和追踪 | [募集原计划、批次与结项](../deep-research-batch-1/project-stages.csv)、[项目条件规模及现金](data/project-conditional-scale.csv)、[权益实施与说明会](data/post-window.csv)、[原始入口](data/links.json) |
| 预测和留出 | [三情景输入](assumptions.json)、[逐年程序](forecast.py)、[逐年模型](data/model.json)、[明细 CSV](data/forecast.csv)、[年度留出](data/annual-holdouts.csv)、[研报留出](../deep-research-batch-1/forecast-holdout.csv)、[华创成本单位](data/analyst-unit-test.csv)、[十篇材料](../deep-research-batch-1/external-evidence.csv) |
| 估值和审阅 | [旧新价值桥](data/value-bridge.csv)、[权益与现金](data/equity-bridge.csv)、[同价阈值](data/price-contours.csv)、[逐年根回代](data/price-witnesses.json)、[终值多变量](data/terminal-sensitivity.csv)、[倍数与自身历史](data/own-relative.csv)、[倍数退出条件](data/exit-sensitivity.csv)、[章节图表映射](data/claims-and-figures.csv) |

## 复算

从仓库根运行，财务计算和 HTML 构建只用 Python 标准库。PDF 原件抽核需安装 `pypdf`，通过同一发行人清单恢复本机原件。如原件在获准使用的已有工作区，把 `<授权原件档案>` 换成该工作区根目录。七份已发布年报随仓库获取。原件路径和 SHA 见上表，未跟踪的中报及季报按对应报告的发行人 URL 与摘要恢复。原表抽核所需的中报可能超出 ReviewStore 绑定恢复范围，`audit.py --from-archive` 会按同一清单和指纹从授权档案只读补查。冷克隆先运行无 `--raw` 的审计可验证公式与账表；取得同指纹原件后再核原 PDF。

~~~text
python -X utf8 docs/cases/688188/deep-research-batch-1/verify_bindings.py --from-archive "<授权原件档案>"
python -X utf8 docs/cases/688188/deep-research-batch-1/reproduce_valuation.py
python -X utf8 docs/cases/688188/deep-research-batch-2/forecast.py
python -X utf8 docs/cases/688188/deep-research-batch-2/evidence.py
python -X utf8 docs/cases/688188/deep-research-batch-2/supplement.py
python -X utf8 docs/cases/688188/deep-research-batch-2/audit.py
python -X utf8 docs/cases/688188/deep-research-batch-2/audit.py --raw --from-archive "<授权原件档案>" --write
python -X utf8 docs/cases/688188/deep-research-batch-2/build_review.py
python -X utf8 scripts/build_cases.py --check
python -X utf8 scripts/check_super_atlas.py
~~~

只复算估值时请保留已签发的原件核验回执。冷热两种环境均可重复生成数值、图表与正文。在 Chromium 打开 `review.html`，用 A4、无页眉页脚、打印背景生成 PDF。先保存为临时 PDF，再运行 `python -X utf8 docs/cases/688188/deep-research-batch-2/link_pdf.py <临时PDF>`，将本机证据链接改为议题分支的公开入口。打印版物理页对应正文，共 40 页。HTML 在克隆目录打开后可用同一组相对链接访问本机底表。

## 审阅要点与证据身份

- 截止日前的原披露与当前 `ReviewStore(...).facts()` 核有效绑定。授权档案恢复后查得 24 条，实际使用的发行人原数据同时保留 PDF 物理页及列。相同发行人的发布接口无 `change_facts()`，本稿同比差分、重列接续和计算均标 AgentCalculated。
- 2023 组收入通过 2024 组同比的舍入区间推算并与 2023 主营合计闭合，原 2023 产品列可追溯。2024 比较成本的性质挪项不改变合计。2026Q3 两组季度差分与发行人首页对照，成本、费用、收款和税费按实际符号。
- 第一批旧估值、两根和金额原样保留。新版改为可服务新机、技术适配和份额、可替换存量、验收及价格，并扣周转和购建。新增扣除 4,600 元货币资金与现金等价物差，具体性质用中报 ETC 保证金旁证。审阅状态及模型因素见正文 p34–40。
- 同 OEM 的订单、复购、毛利、安装、保修、回款和库存仍是最能改变价值的缺项。样品、合作及规划 IRR 是可用的进度线索。取得单批现金与可证资本回报才测试新业务入模。11 月 20 日原路演页访问未成功，已有含原入口的可读转录。其管理层答复、相互冲突的口径和取证字段单独记录于期后表。
- 费率、获单规模、调机和项目现金为分析条件，不记入事实账本。本稿的独立原表抽核与单独估值公式由本次实施 Agent 完成。团队签署、研究判断采纳、合并与投资决定留待各自真实程序。
