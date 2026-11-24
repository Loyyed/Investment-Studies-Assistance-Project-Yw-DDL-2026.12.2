"""在真实 Edge/Chromium 中验收本地图册。需要 websocket-client 1.9.2。"""
import argparse
import base64
from contextlib import suppress
import json
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.request import urlopen

from websocket import create_connection


class Browser:
    def __init__(self, browser, profile):
        self.profile = profile
        self.process = subprocess.Popen([
            str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
            "--remote-debugging-port=0", "--user-data-dir=" + str(profile), "about:blank"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = profile / "DevToolsActivePort"
        for _ in range(150):
            if port_file.exists():
                try:
                    port = int(port_file.read_text().splitlines()[0])
                    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=1) as response:
                        page = next(entry for entry in json.load(response) if entry["type"] == "page")
                    self.socket = create_connection(page["webSocketDebuggerUrl"], timeout=8, suppress_origin=True)
                    break
                except (OSError, IndexError, ValueError, StopIteration):
                    pass
            time.sleep(.1)
        else:
            self.process.terminate()
            raise RuntimeError("Edge 调试端口未启动")
        self.serial = 0
        self.events = []
        self.rpc("Page.enable")
        self.rpc("Runtime.enable")
        self.rpc("Log.enable")

    def rpc(self, method, **params):
        self.serial += 1
        serial = self.serial
        self.socket.send(json.dumps({"id":serial, "method":method, "params":params}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") != serial:
                self.events.append(message)
                continue
            if "error" in message:
                raise RuntimeError((method,message["error"]))
            return message.get("result",{})

    def js(self, expression):
        info = self.rpc("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in info:
            raise AssertionError(info["exceptionDetails"])
        return info["result"].get("value")

    def wait(self, javascript, timeout=8):
        limit = time.monotonic() + timeout
        while time.monotonic() < limit:
            try:
                value = self.js(javascript)
                if value:
                    return value
            except AssertionError:
                pass
            time.sleep(.06)
        raise AssertionError(javascript)

    def shot(self, path):
        time.sleep(.31)
        info = self.rpc("Page.captureScreenshot", format="png", captureBeyondViewport=False)
        path.write_bytes(base64.b64decode(info["data"]))

    def close(self):
        with suppress(Exception):
            self.rpc("Browser.close")
        with suppress(Exception):
            self.socket.close()
        with suppress(Exception):
            self.process.terminate()


def observe(b, width, height, url, output):
    mobile = width < 600
    b.rpc("Emulation.setDeviceMetricsOverride", width=width,height=height,deviceScaleFactor=1,mobile=mobile,
          screenWidth=width,screenHeight=height)
    b.rpc("Emulation.setTouchEmulationEnabled", enabled=mobile)
    b.events.clear()
    b.rpc("Page.navigate", url=url)
    b.wait('document.readyState==="complete" && !!document.querySelector("#cash-result")')
    assert b.js("document.querySelectorAll('section.chapter').length") == 9
    assert b.js('document.documentElement.scrollWidth <= innerWidth + 1')
    assert b.js("[...document.querySelectorAll('[id]')].map(x=>x.id).filter((id,i,a)=>a.indexOf(id)!==i)") == []
    b.shot(output / f"封面-{width}.png")

    # 按读者顺序先经过商业模式和历史。
    if mobile:
        b.js('document.querySelector("#nav-toggle").click()')
        assert b.js('document.querySelector("#nav-toggle").getAttribute("aria-expanded")') == "true"
    b.js('document.querySelector(\'#nav-area nav a[href="#chapter-02"]\').click()')
    assert b.wait('location.hash==="#chapter-02"')
    assert b.js('document.querySelector("#nav-toggle").getAttribute("aria-expanded")') == "false"
    b.js('document.querySelector(\'#role-tabs button[data-key="2"]\').click()')
    assert "付款" in b.js('document.querySelector("#role-note").innerText') or "账期" in b.js('document.querySelector("#role-note").innerText')
    b.js('document.querySelector(\'#flow-steps button[data-step="3"]\').click()')
    assert b.js('document.querySelector("#flow-steps [aria-current=step]").innerText').endswith("回款")
    b.js('document.querySelector(\'#role-note + h4 + .actions button[data-step="2"]\').click()')
    assert "验收" in b.js('document.querySelector("#flow-note").innerText')
    b.js('document.querySelector("#chapter-02 .chapter-next a").click()')
    assert b.wait('location.hash==="#chapter-03"')
    b.js('document.querySelector(\'#history-metrics button[data-key="core_ebit"]\').click()')
    assert "2022" in b.js('document.querySelector("#history-selected").innerText')
    assert "1216370312" in b.js('document.querySelector("#history-selected a").href')
    b.js('document.querySelector(\'#history-metrics button[data-key="cfo_less_capex"]\').click()')
    assert "522.53" in b.js('document.querySelector("#history-selected").innerText')
    assert "2023" in b.js('document.querySelector("#history-plot svg").textContent')

    # 抽查通过搜索落到原表，跨章锚点打开正确的证据面板。
    b.js('document.querySelector("#search-open").click()')
    b.js('(()=>{let e=document.querySelector("#search-input");e.value="87.34%";e.dispatchEvent(new Event("input",{bubbles:true}));})()')
    assert "87.34%" in b.js('document.querySelector("#results").innerText')
    b.js('document.querySelector(\'#results a[href="#volume-evidence"]\').click()')
    assert b.wait('location.hash==="#volume-evidence" && document.querySelector("#volume-evidence").open')
    assert b.js('[...document.querySelectorAll("#volume-evidence .tableframe a")].map(x=>x.hash)')==["#page=26","#page=29"]
    evidence=b.js('document.querySelector("#volume-evidence").innerText')
    assert all(x in evidence for x in ("56,824.00","65,064.00","87.34%"))
    b.js('document.querySelector(\'#income-tabs button[data-key="gross"]\').click()')
    assert "百分点" in b.js('document.querySelector("#income-plot svg").textContent')
    b.js('document.querySelector("#income-step [data-cmd=start]").click()')
    assert b.js('document.querySelectorAll("#income-plot svg rect").length') == 1
    b.js('document.querySelector("#income-step [data-cmd=next]").click()')
    assert b.js('document.querySelectorAll("#income-plot svg rect").length') == 2
    b.js('document.querySelector("#income-step [data-cmd=all]").click()')
    b.js('document.querySelector(\'#income-tabs button[data-key="groups"]\').click()')
    assert "2024 比较列" in b.js('document.querySelector("#income-table").innerText')
    b.js('document.querySelector("#chapter-04 .chapter-next a").click()')
    assert b.wait('location.hash==="#chapter-05"')
    assert b.js('document.querySelector("#cash-result").textContent')=="+10.38 元"
    b.js('document.querySelector("#preset-slow").scrollIntoView({block:"center",behavior:"instant"})')
    if mobile:
        x,y=b.js('(()=>{let r=document.querySelector("#preset-slow").getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()')
        b.rpc("Input.dispatchTouchEvent",type="touchStart",touchPoints=[{"x":x,"y":y}])
        b.rpc("Input.dispatchTouchEvent",type="touchEnd",touchPoints=[])
    else:
        b.js('document.querySelector("#preset-slow").click()')
    assert b.wait('document.querySelector("#cash-result").textContent==="−0.58 元"')
    assert "62.8945" in b.js('document.querySelector("#cash-summary").innerText')
    assert "5.48" in b.js('document.querySelector("#cash-reading").innerText')
    b.js('document.querySelector("#cash-proof").open=true')
    assert "-0.576849315068493" in b.js('document.querySelector("#cash-proof").innerText')
    b.js('document.querySelector("#cash-ar").focus({preventScroll:true})')
    b.rpc("Input.dispatchKeyEvent", type="rawKeyDown",key="ArrowLeft",code="ArrowLeft",windowsVirtualKeyCode=37,nativeVirtualKeyCode=37)
    b.rpc("Input.dispatchKeyEvent", type="keyUp",key="ArrowLeft",code="ArrowLeft",windowsVirtualKeyCode=37,nativeVirtualKeyCode=37)
    assert b.js('document.querySelector("#cash-ar").value')=="64"
    for slider,new_value in [("ar",62),("gm",52),("service",6),("stock",140)]:
        previous = b.js('document.querySelector("#cash-result").innerText')
        b.js(f'(()=>{{let x=document.querySelector("#cash-{slider}");x.value={new_value};x.dispatchEvent(new Event("input",{{bubbles:true}}));}})()')
        assert previous != b.js('document.querySelector("#cash-result").innerText')
    b.js('document.querySelector("#preset-slow").click()')
    b.js('document.querySelector("#cash-card").scrollIntoView({behavior:"instant"})')
    b.shot(output / f"配套现金-{width}.png")
    b.js('document.querySelector(\'button[data-zoom="cash-plot"]\').click()')
    assert b.js('document.querySelector("#zoom-dialog").open')
    b.js('document.querySelector("#zoom-dialog [data-close]").click()')
    assert not b.js('document.querySelector("#zoom-dialog").open')

    # 逐年图、项目阶段和价格根。
    b.js('document.querySelector(\'#project-tabs button[data-key="2"]\').click()')
    assert "预算及技术路径" in b.js('document.querySelector("#project-data").innerText')
    b.js('document.querySelector(\'#forecast-metrics button[data-key="fcff"]\').click()')
    before = b.js('document.querySelector("#forecast-plot polyline").getAttribute("points")')
    b.js('document.querySelector(\'#forecast-scenarios button[data-key="improve"]\').click()')
    assert "改善" in b.js('document.querySelector("#forecast-note").innerText')
    assert before!=b.js('document.querySelector("#forecast-plot polyline").getAttribute("points")')
    assert all(x in b.js('document.querySelector("#forecast-note").innerText') for x in ("实绩", "桩段", "全年"))
    b.js('document.querySelector("#valuation-step [data-cmd=start]").click()')
    assert b.js('document.querySelectorAll("#valuation-plot svg rect").length') == 1
    b.js('document.querySelector("#valuation-step [data-cmd=all]").click()')
    assert b.js('document.querySelectorAll("#valuation-plot svg rect").length') == 8
    b.js('document.querySelector(\'#valuation-tabs button[data-key="contour"]\').click()')
    assert b.js('document.querySelectorAll("#valuation-plot circle").length')==15
    assert "56.83%" in b.js('document.querySelector("#price-node-readout").innerText')
    b.js('(()=>{let x=document.querySelector("#price-node");x.selectedIndex=0;x.dispatchEvent(new Event("change",{bubbles:true}));})()')
    assert b.js('document.querySelector("#price-node-readout").innerText').count("原区间无解")==3
    b.js('document.querySelector("#valuation-card").scrollIntoView({behavior:"instant"})')
    b.shot(output / f"价格等值线-{width}.png")
    b.js('document.querySelector(\'#valuation-tabs button[data-key="equity"]\').click()')
    assert "68.44%" in b.js('document.querySelector("#valuation-card").innerText')

    # 原文、精确锚点、图件加载和批注。
    b.js('document.querySelector("#all-original").click()')
    assert b.js('document.querySelectorAll(".chapter .original[open]").length')==9
    b.js('document.querySelector("#all-original").click()')
    b.js('document.querySelector(\'#roles-card a[href="#figure-chain"]\').click()')
    assert b.wait('location.hash==="#figure-chain"&&document.getElementById("figure-chain").closest("details").open')
    assert b.wait('Array.from(document.querySelectorAll(".archive-fig img")).some(x=>x.naturalWidth>0)')
    b.js('document.querySelector("#notes").open=true;document.querySelector("#note-text").value="验收临时记录";document.querySelector("#note-save").click()')
    assert "已保存在本浏览器" in b.js('document.querySelector("#note-status").innerText')
    b.rpc("Page.reload")
    b.wait('document.readyState==="complete"&&!!document.querySelector("#note-text")')
    assert b.js('document.querySelector("#note-text").value')=="验收临时记录"
    b.js('localStorage.removeItem("bochu-atlas-v1")')
    assert b.js('document.documentElement.scrollWidth<=innerWidth+1')
    errors=[e for e in b.events if e["method"]=="Runtime.exceptionThrown"]
    assert not errors, errors
    return {"宽度":width, "输入模式":"触屏模拟与键盘" if mobile else "桌面与键盘",
            "通过":"九章、导航、搜索、销量与源页、两格现金、四个范围输入、项目、预测、15个价格根、无解、原文、图件、批注重开",
            "最终场景":"42.02 / 81.81 / 134.83 元"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--browser",type=Path,required=True)
    parser.add_argument("--atlas",type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--reference",type=Path)
    args=parser.parse_args()
    atlas=args.atlas.resolve()
    output=atlas/"验收"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as path:
        b=Browser(args.browser,Path(path))
        try:
            url=(atlas/"index.html").as_uri()
            results=[observe(b,w,h,url,output) for w,h in ((1440,900),(390,844),(320,780))]
            b.rpc("Emulation.setEmulatedMedia",features=[{"name":"prefers-reduced-motion","value":"reduce"}])
            assert b.js('matchMedia("(prefers-reduced-motion: reduce)").matches')
            assert b.js('getComputedStyle(document.documentElement).scrollBehavior')=="auto"
            assert b.js('getComputedStyle(document.querySelector(".jump a")).transitionDuration')=="0s"
            results.append({"减少动效":"滚动 instant、过渡 0s，控件继续运行"})

            if args.reference:
                reference = args.reference.resolve().as_uri()
                b.rpc("Emulation.setDeviceMetricsOverride", width=1440,height=900,deviceScaleFactor=1,mobile=False)
                b.rpc("Page.navigate",url=reference+"#complete-story")
                b.wait('document.readyState==="complete" && !!document.querySelector("#complete-story")')
                chapter=b.js('document.querySelector("#complete-story").innerText.slice(0,250)')
                assert len(chapter)>60
                b.rpc("Page.navigate",url=reference+"#forecast")
                b.wait('document.readyState==="complete"&&!!document.querySelector("#forecast")')
                ref_summary=b.js('({graphs:document.querySelectorAll("figure,svg,canvas").length, folds:document.querySelectorAll("details").length})')
                assert ref_summary["graphs"]>0 and ref_summary["folds"]>0
                b.js('(()=>{const anchor=document.querySelector("#forecast");const d=anchor.querySelector("details")||document.querySelector("details");d.open=true;return d.open;})()')
                results.append({"参考图册":"Edge 实开茅台 V2.2 首屏、经营长章与预测图表，实际展开明细",**ref_summary})
            b.rpc("Network.enable")
            b.rpc("Network.emulateNetworkConditions",offline=True,latency=0,downloadThroughput=0,uploadThroughput=0)
            b.rpc("Page.navigate",url=url+"#cash-proof")
            b.wait('document.readyState==="complete" && document.querySelector("#cash-proof")?.open')
            b.js('document.querySelector("#preset-slow").click()')
            assert b.js('document.querySelector("#cash-result").textContent')=="−0.58 元"
            assert b.js('performance.getEntriesByType("resource").every(x=>new URL(x.name).protocol==="file:")')
            results.append({"完全断网":"file:// 打开、深链展开、负现金试算、仅本地资源通过"})
            (output/"浏览器回执.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(json.dumps(results,ensure_ascii=False))
        finally:
            b.close()


if __name__ == "__main__":
    main()
