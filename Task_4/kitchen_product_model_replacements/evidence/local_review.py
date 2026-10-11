"""Local saved-model review, independent of the ISL server connection."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import html
import json
import mimetypes

ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT.parent / 'kitchen_objects_pbr_dashboard/images/assets'
ITEMS = json.loads((ROOT / 'objects/replacement_inventory.json').read_text())
BY_ID = {item['id']: item for item in ITEMS}

class Handler(BaseHTTPRequestHandler):
    def send_file(self, file):
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(file)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(file.stat().st_size))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        with file.open('rb') as source:
            while chunk := source.read(1024 * 1024):
                self.wfile.write(chunk)

    def do_GET(self):
        route = urlsplit(self.path)
        if route.path == '/':
            slug = parse_qs(route.query).get('object', ['range_kettle'])[0]
            item = BY_ID.get(slug, ITEMS[0])
            slug = item['id']
            options = ''.join('<option value="' + row['id'] + '"' + (' selected' if row['id'] == slug else '') + '>' + html.escape(row['id'].replace('_', ' ').title()) + '</option>' for row in ITEMS)
            source = item.get('product') or {}
            credit = ('<a href="' + html.escape(source.get('url', '')) + '">' + html.escape(source.get('name', '')) + '</a> · ' + html.escape(source.get('author', '')) + ' · ' + html.escape(source.get('license', ''))) if source else 'Photo-built fitted geometry'
            page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kitchen saved models</title>
            <style>body{background:#153c2c;color:white;font:16px system-ui;line-height:1.5;margin:0}main{max-width:1400px;margin:auto;padding:24px}a{color:#bbf7d0}select{padding:10px;font:inherit}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0;background:#102e23;border-radius:8px;overflow:hidden}figcaption{padding:12px}img,model-viewer{width:100%;height:500px;object-fit:contain;display:block}.note{color:#c9e3d5;font-size:14px}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>
            <script type="module" src="/model-viewer.min.js"></script><main><h1>Kitchen objects — saved model review</h1>
            <p>These new model files are saved locally. This page provides standalone studio inspection; the full-room dashboard has a separate link below.</p>
            <label>Object <select onchange="location.href='/?object='+this.value">''' + options + '''</select></label>
            <h2>''' + html.escape(slug.replace('_', ' ').title()) + '''</h2><div class="grid">
            <figure><figcaption>Real photograph</figcaption><img src="/image/''' + slug + '''/real" alt="Original photograph"></figure>
            <figure><figcaption>Earlier repaired mesh in the kitchen</figcaption><img src="/image/''' + slug + '''/before" alt="Earlier mesh rendering at the photograph camera"></figure>
            <figure><figcaption>New 3D model — drag to rotate</figcaption><model-viewer id="model" src="/model/''' + slug + '''" camera-controls environment-image="neutral" exposure="1" shadow-intensity="1" interaction-prompt="none"></model-viewer></figure></div>
            <p class="note">The new model is shown under studio lighting. It is not a calibrated full-room after image.</p><p>''' + html.escape(item['notes']) + '''</p><p class="note">Source: ''' + credit + '''</p><p><a href="/model/''' + slug + '''" download>Download this new model</a> · <a href="http://localhost:8767/">Full-room dashboard when ISL is reachable</a></p></main></html>'''
            payload = page.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif route.path == '/model-viewer.min.js':
            self.send_file(ROOT / 'web/model-viewer.min.js')
        elif route.path.startswith('/model/') and route.path.split('/')[-1] in BY_ID:
            self.send_file(ROOT / 'objects' / BY_ID[route.path.split('/')[-1]]['folder'] / 'product_pbr.glb')
        elif route.path.startswith('/image/'):
            parts = route.path.split('/')
            if len(parts) != 4 or parts[2] not in BY_ID or parts[3] not in ['real', 'before']:
                self.send_error(404)
                return
            suffix = 'real' if parts[3] == 'real' else 'pbr'
            self.send_file(OLD / (parts[2] + '_' + suffix + '.jpg'))
        elif route.path == '/inventory.json':
            self.send_file(ROOT / 'objects/replacement_inventory.json')
        else:
            self.send_error(404)

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8768), Handler).serve_forever()
