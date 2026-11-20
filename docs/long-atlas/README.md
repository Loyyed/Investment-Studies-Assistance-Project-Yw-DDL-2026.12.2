# 五家公司证券投资超级图册 V2.2

[五公司工作台](http://127.0.0.1:8780/desk/) · [图册总封面](http://127.0.0.1:8780/long-atlas/) · [同日比较](http://127.0.0.1:8780/long-atlas/compare.html) · [离线 ZIP](offline.zip)

从仓库根运行 **python -X utf8 五公司工作台/start.py**。离线将 ZIP 解压至一个目录，再用浏览器打开其中的 **index.html**。离线包含封面、公司正文、图、底表、模型、可编辑 JSON 和关键历史快照。外链原件保持发行人、交易所或监管机关路径，打开外链时需联网。当前 Fact 需要工作台读取真实绑定，离线显示冻结快照与本版历史核验回执。

| 公司 | 在线 | 正文 Markdown | 可编辑 JSON | 估值复算 |
| --- | --- | --- | --- | --- |
| 涪陵榨菜 | [阅读](http://127.0.0.1:8780/long-atlas/002507/) | [MD](002507/case.md) | [JSON](002507/document.json) | [回执](002507/valuation-receipt.json) |
| 安琪酵母 | [阅读](http://127.0.0.1:8780/long-atlas/600298/) | [MD](600298/case.md) | [JSON](600298/document.json) | [回执](600298/valuation-receipt.json) |
| 柏楚电子 | [阅读](http://127.0.0.1:8780/long-atlas/688188/) | [MD](688188/case.md) | [JSON](688188/document.json) | [回执](688188/valuation-receipt.json) |
| 泡泡玛特 | [阅读](http://127.0.0.1:8780/long-atlas/09992/) | [MD](09992/case.md) | [JSON](09992/document.json) | [回执](09992/valuation-receipt.json) |
| Intuitive Surgical | [阅读](http://127.0.0.1:8780/long-atlas/US/) | [MD](US/case.md) | [JSON](US/document.json) | [回执](US/valuation-receipt.json) |

[字数表](word-count.csv) · [数据字段覆盖](coverage.csv) · [图表清单](figures.csv) · [主张与来源](claims.csv) · [58 条审核事件](historical-reviewstore-receipt.csv) · [折现参数](wacc.csv) · [动效与预览](motion.md) · [待审与分工](review.md) · [复算验收](acceptance.json) · [浏览器回执](browser-receipt.json)

## 生成与接续

公司目录中的 `chapters/01.md` 至 `07.md` 是唯一正文源。工作台可保存本机草稿、重开和导出 JSON。提交定稿时在审阅后把草稿对应段落更新到章节 Markdown，再运行生成程序。各版正文 SHA-256 与草稿关联，旧页面和旧图册编辑保存在各自原位置。

```text
python -X utf8 scripts/build_atlas_history.py
python -X utf8 scripts/build_atlas_valuation_notes.py
python -X utf8 scripts/build_cases.py --check
python -X utf8 scripts/build_long_atlas.py
python -X utf8 scripts/check_long_atlas.py --url http://127.0.0.1:8780
```

原件恢复以后，可加 `--verify-originals <源研究或已恢复协作库根目录>` 到历史表生成命令核对原件版本、PDF 坐标与数值。原件核验需要 `pypdfium2`。当前账本确认需要恢复原件。各公司新确认来源绑定读取 [当前 Fact](http://127.0.0.1:8780/research/facts.html)，新历史回执保留实际 agent 事件。

字数统计仅取独立论述段中的汉字。去除标题、表格、图注等非正文，去除 Markdown 引用标签后，以规范化汉字序列在五家公司全局判重。发布构建拒绝缺章、少于 20,000 字及不足 12 张数据图和 4 张机制图的版本。每张数据图的线图、柱图、底表属于同一张图。覆盖各阶段及经营约束的正文可在章内直接查阅。

浏览器验收使用 Playwright。将离线包解压后，执行 `node scripts/check_long_atlas_browser.cjs <工作台 URL> <解压目录> <截图目录> [Chromium 可执行文件]`。只有本机验证时才需要 Playwright。工厂项目、期后权益及来源权限沿用阶段 17 和现有工作台记录。
