"""Render the same Mermaid used by GitHub to static, offline PNGs for the HTML edition."""
import argparse
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

from review_assets import DEFAULT_CACHE, FONT, MERMAID, ensure_asset

HERE = Path(__file__).resolve().parent
FIGURES = HERE / "figures"


def render(cache, executable):
    font = ensure_asset(FONT, cache)
    renderer = ensure_asset(MERMAID, cache)
    with TemporaryDirectory(prefix="bochu-diagrams-") as tmp, sync_playwright() as pw:
        temp = Path(tmp)
        shutil.copyfile(font, temp / font.name)
        template = temp / "diagram.html"
        template.write_text("""<!doctype html><meta charset="utf-8">
<style>
@font-face{font-family:ReviewCN;src:url('NotoSansCJKsc-Regular.otf')}
html{background:#faf9f5}body{margin:0;color:#183a42;font:16px ReviewCN}
#graph{display:table;padding:18px;margin:0 auto;box-sizing:border-box;min-width:300px}
#graph svg{display:block;height:auto}
</style><div id="graph"></div>""", encoding="utf-8")
        with pw.chromium.launch(executable_path=executable, args=["--disable-gpu","--disable-lcd-text","--force-color-profile=srgb"]) as browser:
            page = browser.new_page(viewport={"width": 1100, "height": 1130}, device_scale_factor=2)
            page.goto(template.as_uri())
            page.add_script_tag(path=str(renderer))
            page.evaluate("""async () => {
                await document.fonts.load('16px ReviewCN');
                mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',
                  fontFamily:'ReviewCN',htmlLabels:false,deterministicIds:true,deterministicIDSeed:'688188',
                  themeVariables:{fontFamily:'ReviewCN',primaryColor:'#e6efea',
                     primaryTextColor:'#193b41',primaryBorderColor:'#669182',lineColor:'#546e73',
                     secondaryColor:'#f2eadc',tertiaryColor:'#e6edf2'},
                  flowchart:{useMaxWidth:false,htmlLabels:false,nodeSpacing:25,rankSpacing:26,diagramPadding:10}});
            }""")
            for source in sorted(FIGURES.glob("*.mmd")):
                page.evaluate("""async text => {
                    const result = await mermaid.render('rendered-review', text);
                    document.querySelector('#graph').innerHTML = result.svg;
                    await document.fonts.ready;
                }""", source.read_text(encoding="utf-8"))
                destination = source.with_suffix(".png")
                page.locator("#graph").screenshot(path=str(destination), animations="disabled")
                print(destination.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--browser", help="Chromium、Edge 或 Chrome 的可执行文件")
    options = parser.parse_args()
    render(options.cache, options.browser)
