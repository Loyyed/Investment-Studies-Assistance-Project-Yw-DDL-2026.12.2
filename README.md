# 投资学协作工程

团队从这里启动工作台、阅读五家公司图册、核对披露并交付定稿。协作分支为 `codex/collaboration-workbenches`。刘翔宇和团队确认最终对象、判断和稿件后，再决定合并到 `main`。

## 首次启动

需要 Git 和 Python 3.10 或更新版本。两套服务均监听本机回环地址，启动使用 Python 标准库。共享工具在仓内锁定版本。

```text
git clone --branch codex/collaboration-workbenches git@github.com:Loyyed/Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2.git
cd Investment-Studies-Assistance-Project-Yw-DDL-2026.12.2
python -X utf8 五公司工作台/start.py --open
```

另开终端运行 `python -X utf8 预选公司详细工作台/start.py`。若系统把 Python 3 命令命名为 `python3`，替换命令名即可。

- [五公司首页](http://127.0.0.1:8780/desk/)并列显示涪陵榨菜、安琪酵母、柏楚电子、泡泡玛特和 ISRG，可从公司卡片打开图册、报告、模型和证据。
- [五家公司封面](http://127.0.0.1:8780/atlas/)可选公司、横向比较、看证据、续写或下载。
- [预选公司工作台](http://127.0.0.1:8781/)登记候选，记录真实确认，再按市场和代码创建独立研究区。
- [离线 HTML](docs/super-atlas/atlas.html)可断网读全文与图表。[可编辑 JSON](docs/super-atlas/atlas-editable.json)支持导入。本地编辑保存在忽略目录。

## 核验与交付

冻结估值日为 **2026-11-12 各市场当地收盘**。发布时原披露 Fact 快照有 188 条。实时 Fact 由 ReviewStore 按实际原件及指纹判断。冷启动能阅读报告和快照。恢复公开原件可运行 `python -X utf8 scripts/recover_public_sources.py --scope facts --plan`，查看清单后移去 `--plan`。交易所若拒绝访问，可用已获授权的原件档案加 `--from-archive` 恢复。原件下载和校验结果留在本机。

- [五公司工作台](五公司工作台/README.md) · [预选公司详细工作台](预选公司详细工作台/README.md)
- [报告留存](报告留存处/README.md) · [MD 转 PDF](MD转PDF/README.md)
- [共同技能和知识](shared/README.md) · [待刘翔宇审核](docs/collaboration/审核与下一步.md)
- [394 项迁移清单](docs/collaboration/migration.csv) · [验收与交接](docs/collaboration/README.md)

提交研究用议题分支与 PR，正文存入报告留存处。原件载荷、私人会话、凭据和本地研究状态留在各成员电脑。源研究工程的历史和核验域独立保留。
