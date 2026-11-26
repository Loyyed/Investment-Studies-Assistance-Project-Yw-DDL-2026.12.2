# 第四轮预测与估值复算

[完整图册](../index.html) · [正式Markdown](../../柏楚电子证券投资分析报告11.26新版.md) · [验收记录](验收记录.md)

本版延续11.25已审第四轮模型，以2025年末为条件起点，年报2026-04-10可得，版本2026-11-26。署名刘翔宇，实施为Codex实施Agent，第四轮经刘翔宇独立审核通过，四轮研究交付完成。

使用Python 3.12、PyMuPDF、Matplotlib、mistune、pypdf。图册计算器使用calculator.js，与model.py相同公式。模型.json存三情景参数、历史基数和结果。关键假设来源.csv、输入原格.csv与补充来源.csv供回原页核查。

    & 'D:/Anaconda/python.exe' -X utf8 -B ./model.py
    & 'D:/Anaconda/python.exe' -X utf8 -B ./supplement.py ../第一轮 .
    & 'D:/Anaconda/python.exe' -X utf8 -B ./build.py
    & 'D:/Anaconda/python.exe' -X utf8 -B ./verify.py
    & 'D:/Anaconda/python.exe' -X utf8 -B ./package.py
    & 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' ./verify_browser.cjs

从原格到首年可按2025年报p27平面收入，查输入原格.csv中的对应ID，进入模型.json的base.revenue[0]，乘基准g0[0]的1.10，再按首年毛利和费率计算。逐年模型.csv的2026基准行保留收入成本、EBIT、税、资本和现金的每一步。

从未来现金到每股可汇总2026–2035行FCFF的年末折现值，再用2036 NOPAT、g/ROIC再投资及WACC−g求终值。加股权桥来源.csv的净额，除p219股数288.729927百万股。verify.py用Fraction独立复算该路线。

旧81.81元的原窗口与参数来源说明在第十章。本轮市场倍数采用假设价格网格，历史市场带和实际同日价格仍缺输入。离线包内含完整年报原件和当前模型，PDF物理页跳转沿用原文件。

11.26整合重建请先运行[统一入口](../协作深化/11.26整合/rebuild.py)，它会同步章节与留存来源，再调用本目录build.py。19个模型文件保持已审字节。
