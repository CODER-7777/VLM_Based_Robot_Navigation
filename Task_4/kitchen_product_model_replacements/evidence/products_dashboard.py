"""Private PBR home-tour wrapper; retain existing comparison/model/navigation routes."""
from pathlib import Path
from urllib.parse import unquote
import mimetypes, os, re

REFINED = Path('/data/robotics/toshith/rxr_author/refined')
TOUR = REFINED / 'toaster_home_tour'
PRODUCTS = REFINED / 'kitchen_product_replacements'
WEB = PRODUCTS / 'web'
SCENE = PRODUCTS / 'home_pbr_products.glb'
CATALOG = PRODUCTS / 'comparison/items/catalog.json'
original = REFINED / 'kitchen_all_upgrade/all_dashboard.py'
source = original.read_text()
source, count = re.subn(r'^ThreadingHTTPServer\(.*?\.serve_forever\(\)\s*$', '', source, flags=re.M)
if count != 1:
    raise RuntimeError('Cannot safely import the existing dashboard handler')
exec(compile(source, str(original), 'exec'), globals())
ExistingHandler = Handler

class HomeTourHandler(ExistingHandler):
    def file(self, path, content_type=None, encoding=None):
        stat = path.stat()
        size = stat.st_size
        etag = '"%x-%x"' % (stat.st_mtime_ns, size)
        if not self.headers.get('Range') and self.headers.get('If-None-Match') == etag:
            self.send_response(304)
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            return
        start, end = 0, size - 1
        range_header = self.headers.get('Range')
        if range_header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header)
            if not match or not any(match.groups()):
                self.send(416, 'text/plain', b'Invalid byte range')
                return
            left, right = match.groups()
            if left:
                start = int(left)
                if right: end = min(end, int(right))
            else:
                start = max(0, size - int(right))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header('Content-Range', 'bytes */%d' % size)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
        self.send_response(206 if range_header else 200)
        self.send_header('Content-Type', content_type or mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        if encoding:self.send_header('Content-Encoding', encoding)
        if content_type=='model/gltf-binary':self.send_header('Vary','Accept-Encoding')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('ETag', etag)
        if range_header: self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.end_headers()
        if self.command == 'HEAD': return
        try:
            with path.open('rb') as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining:
                    block = stream.read(min(remaining, 1024 * 1024))
                    if not block: break
                    self.wfile.write(block)
                    remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == '/':
                self.file(WEB / 'comparison-first.html', 'text/html; charset=utf-8')
            elif path in ['/home-tour', '/kitchen-room']:
                self.file(WEB / 'home-tour.html', 'text/html; charset=utf-8')
            elif path == '/home-scene.glb':
                compressed=SCENE.with_suffix('.glb.gz')
                if 'gzip' in self.headers.get('Accept-Encoding','') and not self.headers.get('Range') and compressed.is_file():self.file(compressed,'model/gltf-binary','gzip')
                else:self.file(SCENE,'model/gltf-binary')
            elif path == '/tour-info':
                data = json.loads((TOUR / 'browser_scene.json').read_text())
                data.update(current_scene=str(SCENE), items=json.loads(CATALOG.read_text())['items'], latest_mesh_refresh=json.loads((PRODUCTS/'latest_mesh_refresh.json').read_text()), revision='kitchen_product_models_pbr_v2', renderer='direct WebGL triangles and original PBR textures', navigation='Habitat/NavMesh via existing navigation service', shared_files_modified=False)
                self.send(200, 'application/json', json.dumps(data).encode())
            elif path == '/models':
                catalog=json.loads(CATALOG.read_text())['items']
                body='<a href="/">Photo comparisons</a><h1>Kitchen model inspection</h1><p>Choose an item to rotate its fitted mesh and inspect its finish.</p><ul>'
                for item in catalog:
                    if item['fit_paths']:
                        body+='<li><a href="/item-viewer?object='+quote(item['id'])+'">'+html.escape(item['label'])+'</a> · '+html.escape(item['method'])+'</li>'
                self.send(200,'text/html; charset=utf-8',page('Kitchen model inspection',body+'</ul>'))
            elif path in ['/item-model.glb','/item-viewer']:
                query=parse_qs(urlsplit(self.path).query)
                name=query.get('object',['toaster'])[0]
                item=next(item for item in json.loads(CATALOG.read_text())['items'] if item['id']==name)
                if not item['fit_paths']:raise ValueError('This item is retained scan geometry')
                if path=='/item-model.glb':
                    index=int(query.get('part',['0'])[0])
                    fit=json.loads(Path(item['fit_paths'][index]).read_text())
                    model=Path(fit['glb'])
                    if not model.is_absolute():model=REFINED/model
                    if name=='toaster':model=REFINED/'kitchen/objects/toaster_v4/product_pbr.glb'
                    self.file(model,'model/gltf-binary')
                else:
                    src='/item-model.glb?object='+quote(name)
                    body='<a href="/?object='+quote(name)+'">Photo comparison</a> · <a href="/kitchen-room?object='+quote(name)+'">See it in the kitchen</a><h1>'+html.escape(item['label'])+'</h1><p>'+html.escape(item['notes'])+'</p>'
                    if len(item['fit_paths'])>1:
                        body+='<label>Bottle <select onchange="document.querySelector(\'model-viewer\').src=\''+src+'&part=\'+this.value">'
                        for i in range(len(item['fit_paths'])):body+='<option value="'+str(i)+'">'+str(i+1)+' of '+str(len(item['fit_paths']))+'</option>'
                        body+='</select></label>'
                    body+='<model-viewer src="'+src+'" camera-controls environment-image="neutral" exposure="1" shadow-intensity="1"></model-viewer><p><a href="'+src+'" download>Download fitted model</a></p>'
                    product=item.get('product')
                    if product:body+='<p>Source: <a href="'+html.escape(product.get('url',''))+'">'+html.escape(product.get('name',''))+'</a>'+(' by '+html.escape(product['author']) if product.get('author') else '')+' · '+html.escape(product.get('license',''))+'</p>'
                    self.send(200,'text/html; charset=utf-8',page(item['label'],body,'<script type="module" src="/model-viewer.min.js"></script>'))
            elif path.startswith('/tour-assets/web/'):
                item=(WEB/unquote(path[len('/tour-assets/web/'):])).resolve()
                if not item.is_relative_to(WEB.resolve()) or not item.is_file():
                    self.send(404,'text/plain',b'Not found')
                    return
                self.file(item)
            elif path.startswith('/tour-assets/comparison/items/'):
                item=(PRODUCTS/'comparison/items'/unquote(path[len('/tour-assets/comparison/items/'):])).resolve()
                if not item.is_relative_to((PRODUCTS/'comparison/items').resolve()) or not item.is_file():
                    self.send(404,'text/plain',b'Not found');return
                self.file(item)
            elif path.startswith('/tour-assets/'):
                item = (TOUR / unquote(path[len('/tour-assets/'):])).resolve()
                if not item.is_relative_to(TOUR.resolve()) or not item.is_file():
                    self.send(404, 'text/plain', b'Not found')
                    return
                self.file(item)
            elif path == '/gaussian':
                self.path = '/'
                super().do_GET()
            else:
                super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            self.send(503, 'application/json', json.dumps({'error': str(error)}).encode())

    def do_HEAD(self):
        if urlsplit(self.path).path == '/home-scene.glb':
            self.file(SCENE, 'model/gltf-binary')
        else:
            self.send(405, 'text/plain', b'HEAD available for scene downloads')

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('KITCHEN_DASH_PORT', '8774'))), HomeTourHandler).serve_forever()
