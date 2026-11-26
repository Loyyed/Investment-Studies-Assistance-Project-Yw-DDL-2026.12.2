"""One entry from chapter sources through approved valuation and offline package."""
from pathlib import Path
import subprocess,sys,shutil
H=Path(__file__).resolve().parent;ST=H.parents[1]
def run(p):subprocess.run([sys.executable,'-X','utf8','-B',str(p)],check=True)
run(H/'adoption.py');run(ST/'第三轮/build.py')
shutil.copy2(ST.parent/'柏楚电子证券投资分析报告11.26新版.md',ST/'第四轮/第三轮报告留存.md')
shutil.copy2(ST/'index.html',ST/'第四轮/第三轮图册留存.html')
run(ST/'第四轮/build.py');run(H/'finalize.py')
if '--package' in sys.argv:run(ST/'第四轮/package.py')
