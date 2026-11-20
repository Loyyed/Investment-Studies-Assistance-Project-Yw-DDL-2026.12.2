"""Start the pinned project workbench, using Python 3.10+ standard library."""
from pathlib import Path
import argparse
import sys
import threading
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from generic_host import start


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8780)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    url = f'http://127.0.0.1:{args.port}/desk/'
    print(f'五公司工作台 {url}', flush=True)
    if args.open:
        threading.Timer(1.2, webbrowser.open, args=(url,)).start()
    start(ROOT, ROOT / 'shared/runtime', args.port)
