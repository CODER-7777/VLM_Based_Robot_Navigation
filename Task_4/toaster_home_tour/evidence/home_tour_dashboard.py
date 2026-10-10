"""Private PBR home-tour wrapper; retain existing comparison/model/navigation routes."""
from pathlib import Path
from urllib.parse import unquote
import mimetypes, os, re

REFINED = Path('/data/robotics/toshith/rxr_author/refined')
TOUR = REFINED / 'toaster_home_tour'
original = REFINED / 'kitchen_all_upgrade/all_dashboard.py'
source = original.read_text()
source, count = re.subn(r'^ThreadingHTTPServer\(.*?\.serve_forever\(\)\s*$', '', source, flags=re.M)
if count != 1:
    raise RuntimeError('Cannot safely import the existing dashboard handler')
exec(compile(source, str(original), 'exec'), globals())
ExistingHandler = Handler

class HomeTourHandler(ExistingHandler):
    def file(self, path, content_type=None):
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
                self.file(TOUR / 'web/comparison-first.html', 'text/html; charset=utf-8')
            elif path in ['/home-tour', '/kitchen-room']:
                self.file(TOUR / 'web/home-tour.html', 'text/html; charset=utf-8')
            elif path == '/home-scene.glb':
                self.file(TOUR / 'home_pbr.glb', 'model/gltf-binary')
            elif path == '/tour-info':
                data = json.loads((TOUR / 'browser_scene.json').read_text())
                data.update(revision='home_tour_pbr_v2', renderer='direct WebGL triangles and original PBR textures', navigation='Habitat/NavMesh via existing navigation service', shared_files_modified=False)
                self.send(200, 'application/json', json.dumps(data).encode())
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
            self.file(TOUR / 'home_pbr.glb', 'model/gltf-binary')
        else:
            self.send(405, 'text/plain', b'HEAD available for scene downloads')

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('KITCHEN_DASH_PORT', '8774'))), HomeTourHandler).serve_forever()
