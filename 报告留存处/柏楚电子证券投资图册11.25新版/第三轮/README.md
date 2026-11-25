# 第三轮重建与审阅入口

[交互图册](../index.html) · [Markdown报告](../../柏楚电子证券投资分析报告11.25新版.md) · [验收记录](验收记录.md)

署名刘翔宇，执行为Codex实施Agent，第三轮独立审核待裁定。

## 重建

使用本机Python 3.12，依赖PyMuPDF、Matplotlib、mistune和pypdf。字体使用Microsoft YaHei。build.py验证输入指纹及七份原件SHA，从章节源和已审数据生成图表、报告、HTML及来源映射。verify.py独立核对新增原格与关键图表计算。

    & 'D:/Anaconda/python.exe' -X utf8 -B ./build.py
    & 'D:/Anaconda/python.exe' -X utf8 -B ./verify.py
    & 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' ./verify_browser.cjs

章节源保留图表插入标记，以章节清单.json确定顺序。图表映射.json指明图名、期间、单位、证据和计算段。图表取数.csv保留第二轮精确公式及依赖，原格索引.csv连接第一轮原表位置。合同负债新增原格与计算分别留存。来源文件仍从第一轮年报索引中的本地路径读取。

HTML离线打开即可使用。它把脚本与样式内嵌，图片使用相邻charts目录。窄屏图表采用内部横向滚动。正式阅读入口为新版目录的index.html，第三轮审阅版.html提供同一入口。

## 版本

第三轮重组前入口.md保存本次重组前的入口字节。第一二轮审核与材料继续保留各自路径。当前第三轮阅读稿按八章重组，合同负债新增证据记录为L213，不转写人工Fact。CURRENT中的接续状态为待刘翔宇审核。
