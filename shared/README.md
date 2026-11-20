# 共享技能与知识

两套工作台共用本目录。三公司工作台读取 `shared/runtime` 的原生工作台和 `shared/knowledge.json`。预选工作台引用同一运行时、知识和模板目录。

[知识索引](knowledge/README.md)列出任务入口。六套项目与通用技能在 [skills/](skills/)，经验和模板在技能 references 及 [templates/](templates/)。材料增补使用 `updates.json` 的版本、方法和引用记录。课程材料原始载荷和本机写作扩展仍按实际访问许可取得。

[固定依赖](external-dependency.json)给出上游标识与文件 SHA-256，原生工作台随仓提交。版本变更先保留旧绑定，再运行两套工作台与现有研究回归。
