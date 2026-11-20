# 五套独立证券投资案例

冻结估值日为 **2026-11-12 各市场当地收盘**。每家以原件定位、经营机制、历史财务桥、预测参数、折现和权益桥、现价反推、最强反方及未来报告素材地图组织。阶段15至17保持源发布口径。阶段17之后公开的项目、分红和回购在[期后跟踪](../super-atlas/follow-up.csv)单列。

| 公司 | 正文 | 素材地图 | 独立复核 |
| --- | --- | --- | --- |
| 涪陵榨菜 | [正文](002507/case.md) | [地图](002507/report-map.md) | [复核](002507/independent-review.md) |
| 安琪酵母 | [正文](600298/case.md) | [地图](600298/report-map.md) | [复核](600298/independent-review.md) |
| 柏楚电子 | [正文](688188/case.md) | [地图](688188/report-map.md) | [复核](688188/independent-review.md) |
| 泡泡玛特 | [正文](09992/case.md) | [地图](09992/report-map.md) | [复核](09992/independent-review.md) |
| ISRG | [正文](US/case.md) | [地图](US/report-map.md) | [复核](US/independent-review.md) |

## 运行与复核

Python 3.10 或更新版本。项目根目录下执行：

```text
python -X utf8 scripts/recalculate_research15.py --check
python -X utf8 scripts/recalculate_research16.py --check
python -X utf8 scripts/build_cases.py --check
python -X utf8 scripts/verify_case_release.py
python -X utf8 五公司工作台/start.py
```

[案例中心](http://127.0.0.1:8780/cases/)与[独立图册封面](http://127.0.0.1:8780/atlas/)共用模型输出。每家公司目录下有全时期 `forecast.csv`、`inputs.json`、`model.json`、历史桥、季报累计和单期、阈值和两变量图。2026首行区分披露期与剩余期，DCF实际以估值日后桩段现金流为首笔。币种换算与各市场股份权利以市场行固定，FCFF、DCF和价桥保持全精度。

`build_cases.py --output <目录>` 可生成另一份输出。内容完成后运行 `python -X utf8 scripts/publish_cases.py` 与 `python -X utf8 scripts/build_super_atlas.py` 更新网站与可编辑图册。相对估值采用同日滚动量纲核对和同行筛选淘汰表。历史现金桥保留范围、代理和未识别差额。经营与资本原数覆盖不足时，文件中的空值表示未取得，未代填零。

## 原件与当前核验

冷启动可逐项复算65个财年、49条近期比较、15条情景和62项旧价格回代。原件通过工作台原件页或恢复脚本按指纹获取。原件未恢复时，阶段17的188条是冻结快照，实时Fact以ReviewStore实际绑定为准。新材料保留对读者、可获日、期间、行列和证据标签，由独立原披露账本按授权流程认定。项目对读的原件证据见各家复核文件与[五家合并收入抽查](original-receipt.json)。

正式报告在团队选定主对象后按素材地图组织。 [60项验收矩阵](acceptance.csv) · [复算回执](model-acceptance.json) · [组长待审与下一步](review.md) · [动效与预览](motion.md)
