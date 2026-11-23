"""Pinned, checksum-verified assets used for report rendering."""
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_CACHE = Path.home() / ".cache" / "bochu-review-render"
FONT = ("NotoSansCJKsc-Regular.otf",
        "https://raw.githubusercontent.com/notofonts/noto-cjk/Sans2.004/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
        "2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b")
MERMAID = ("mermaid.min.js", "https://cdn.jsdelivr.net/npm/mermaid@10.9.5/dist/mermaid.min.js",
           "616a109f19cd186842e11d45b35ac07456b3a75513310f6ea075351aa430b1e2")


def ensure_asset(spec, cache):
    name, url, expected = spec
    path = cache / name
    if not path.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        with urlopen(Request(url, headers={"User-Agent": "Bochu research chart renderer"}), timeout=30) as response:
            content = response.read()
        if sha256(content).hexdigest() != expected:
            raise ValueError(f"下载文件指纹不符 {name}")
        path.write_bytes(content)
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"缓存文件指纹不符 {path}")
    return path.resolve()
