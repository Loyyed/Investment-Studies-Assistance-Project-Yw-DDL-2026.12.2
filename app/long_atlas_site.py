"""Serve the approved long-form publication and its generated downloads."""
from urllib.parse import unquote
from json import loads
from pathlib import PurePosixPath

MIME={
    '.html':'text/html; charset=utf-8','.csv':'text/csv; charset=utf-8',
    '.json':'application/json; charset=utf-8','.md':'text/markdown; charset=utf-8',
    '.zip':'application/zip','.png':'image/png',
}


def serve_long(host, root, route, query, nonce):
    relative=unquote(route.removeprefix('/long-atlas/'))
    rel=PurePosixPath(relative)
    if not relative or relative.endswith('/'):
        rel=rel/'index.html'
    directory=(root/'docs/long-atlas').resolve()
    target=(directory/rel).resolve()
    allowed=loads((directory/'package.json').read_text(encoding='utf-8'))['files']
    if (not target.is_relative_to(directory) or rel.as_posix() not in allowed
            or target.suffix not in MIME or not target.is_file()):
        return host.send({'error':'该图册文件没有在本版发布'},404)
    if target.suffix=='.html' and query.get('download')!=['1']:
        # Files are generated only from escaped plain research text and trusted local JS.
        # Same-origin localStorage holds only this edition's draft.
        html=target.read_text(encoding='utf-8').replace('<script>',f'<script nonce="{nonce}">')
        return host.send_edition_cover(html,allow_images=True)
    suffix=target.suffix
    disposition=None if suffix=='.png' and query.get('download')!=['1'] else f'attachment; filename="{target.name}"'
    return host.send(target.read_bytes(),content=MIME[suffix],disposition=disposition,downloadable=True)
