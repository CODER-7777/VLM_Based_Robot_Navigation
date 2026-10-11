"""Photographic Matterport panoramas and matched repaired-room captures.

All generated server artifacts live beside this script under vivekananda.
Skybox conventions follow Matterport3DSimulator/scripts/depth_to_skybox.py.
"""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
import hashlib
import json
import mimetypes
import struct
import time
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REF = Path('/data/robotics/toshith/rxr_author/refined')
PHOTOS = Path('/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ')
REPAIRS = Path('/data/robotics/toshith/vivekananda/kitchen_repair_20261011')
SCENE = REPAIRS / 'home_pbr_products.glb'
SIZE = 1024
WIDTH, HEIGHT = 4096, 2048
TRANSFORMS = np.asarray([
    [[1,0,0],[0,0,-1],[0,1,0]],
    [[1,0,0],[0,1,0],[0,0,1]],
    [[0,0,-1],[0,1,0],[1,0,0]],
    [[-1,0,0],[0,1,0],[0,0,-1]],
    [[0,0,1],[0,1,0],[-1,0,0]],
    [[1,0,0],[0,0,1],[0,-1,0]],
], dtype=float)
VIEWS = [
    ('sink', 'Sink and toaster', '58348305b0f84dd8b161aaf2d5b945ef'),
    ('corner', 'Corner, bottles and knife blocks', 'f7a060bfa1164b5e9c5cca04284f6d6b'),
    ('range', 'Range, telephone and grinder', '1eae5d4a0c0146c2b884d6b96d9b0e16'),
    ('tea', 'Tea setting and glass kettle', 'd70e05c20c15468eb93117d496285f82'),
    ('coffee', 'Coffee machine', '1113418419f84a5c80586634f7611f14'),
]


def calibrations():
    result = {}
    for line in (PHOTOS / 'undistorted_camera_parameters/2azQ1b91cZZ.conf').read_text().splitlines():
        words = line.split()
        if words and words[0] == 'scan':
            result[words[2]] = np.asarray(words[3:19], dtype=float).reshape(4, 4)
    return result


def equirectangular(faces, rotations):
    """World-Z-up panorama: centre faces -Y; right quarter faces +X."""
    result = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    lon = ((np.arange(WIDTH) + .5) / WIDTH * 2 - 1) * np.pi
    for start in range(0, HEIGHT, 64):
        stop = min(start + 64, HEIGHT)
        lat = (.5 - (np.arange(start, stop) + .5) / HEIGHT) * np.pi
        x = np.cos(lat)[:, None] * np.sin(lon)[None, :]
        y = -np.cos(lat)[:, None] * np.cos(lon)[None, :]
        z = np.broadcast_to(np.sin(lat)[:, None], x.shape)
        rays = np.stack((x, y, z), axis=-1)
        local = np.einsum('hwj,ijk->ihwk', rays, rotations)
        winner = np.argmax(-local[..., 2], axis=0)
        for index, face in enumerate(faces):
            d = -local[index, ..., 2]
            safe = np.where(d > 1e-8, d, 1)
            u = ((local[index, ..., 0] / safe + 1) * .5 * face.shape[1] - .5).astype(np.float32)
            v = ((1 - local[index, ..., 1] / safe) * .5 * face.shape[0] - .5).astype(np.float32)
            sample = cv2.remap(face, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            mask = winner == index
            result[start:stop][mask] = sample[mask]
    return result


def save_image(array, path):
    Image.fromarray(array).save(path, quality=95, subsampling=0)


def paired_image(view):
    before = Image.open(ROOT / 'images' / (view + '_before.jpg')).convert('RGB')
    after = Image.open(ROOT / 'images' / (view + '_after.jpg')).convert('RGB')
    result = Image.new('RGB', (WIDTH, HEIGHT * 2 + 120), '#153c2c')
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(result)
    draw.text((24, 12), 'BEFORE: original dataset panorama (real photograph)', fill='white', font=font)
    result.paste(before, (0, 60))
    draw.text((24, HEIGHT + 72), 'AFTER: published repaired kitchen (PBR room render)', fill='white', font=font)
    result.paste(after, (0, HEIGHT + 120))
    result.save(ROOT / 'images' / (view + '_comparison.jpg'), quality=94, subsampling=0)


def prepare():
    for name in ('images', 'faces', 'evidence', 'logs'):
        (ROOT / name).mkdir(exist_ok=True)
    cams = calibrations()
    catalog = json.loads((REPAIRS / 'comparison/items/catalog.json').read_text())['items']
    verification = json.loads((REPAIRS / 'evidence/artifact_verification.json').read_text())
    scene_hash = hashlib.sha256(SCENE.read_bytes()).hexdigest()
    assert scene_hash == verification['scene_sha256'], 'Scene changed since verification'
    config = {'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'before': 'Original Matterport dataset photographs; six supplied skybox faces',
              'after': 'Published repaired mesh with direct PBR materials',
              'after_source': str(SCENE), 'source_bytes': SCENE.stat().st_size,
              'source_sha256': scene_hash, 'revision': verification['revision'],
              'source_mtime_ns': SCENE.stat().st_mtime_ns,
              'coordinate_frame': 'raw Matterport Z-up metres',
              'panorama_size': [WIDTH, HEIGHT], 'face_size': SIZE,
              'camera_basis_reference': 'https://github.com/peteanderson80/Matterport3DSimulator/blob/master/scripts/depth_to_skybox.py',
              'calibration_note': 'Skybox rotation follows the supplied i1_5 camera and published skybox transforms. Capture centre uses that camera translation; original stitching can retain small rig/parallax differences.',
              'limitations': ['A viewpoint cannot reveal occluded objects. Five positions cover the photographed kitchen areas.',
                             'Before is an original photographic panorama, not the missing untouched GLB.',
                             'After retains existing scan reconstruction defects and approximate object models.'],
              'views': []}
    for key, label, pano in VIEWS:
        basis = cams[pano + '_i1_5.jpg']
        rotations = np.einsum('ij,kjl->kil', basis[:3, :3], TRANSFORMS)
        assert np.max(np.abs(rotations @ rotations.transpose(0, 2, 1) - np.eye(3))) < 1e-4
        assert np.min(np.linalg.det(rotations)) > .9999
        packets = []
        for rotation in rotations:
            matrix = basis.copy()
            matrix[:3, :3] = rotation
            packets.append({'width': SIZE, 'height': SIZE,
                            'K': [[SIZE/2,0,SIZE/2],[0,SIZE/2,SIZE/2],[0,0,1]],
                            'c2w_raw_gl': matrix.tolist()})
        files = [PHOTOS / 'matterport_skybox_images' / (pano + '_skybox%d_sami.jpg' % i) for i in range(6)]
        item = {'id': key, 'label': label, 'pano_id': pano, 'position_raw': basis[:3, 3].tolist(),
                'calibration_camera': pano + '_i1_5.jpg', 'rotations': rotations.tolist(),
                'capture_packets': packets, 'original_faces': [str(p) for p in files],
                'original_sha256': [hashlib.sha256(p.read_bytes()).hexdigest() for p in files],
                'objects': [entry['id'] for entry in catalog if entry['photo'].startswith(pano)]}
        config['views'].append(item)
        target = ROOT / 'images' / (key + '_before.jpg')
        if not target.exists():
            faces = [np.asarray(Image.open(p).convert('RGB')) for p in files]
            save_image(equirectangular(faces, rotations), target)
        print('ORIGINAL_PANORAMA_READY', key, flush=True)
    (ROOT / 'config.json').write_text(json.dumps(config, indent=2))
    return config


CONFIG = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        with (ROOT / 'logs/http.log').open('a') as log:
            log.write('%s %s\n' % (self.log_date_time_string(), fmt % args))

    def reply(self, status, data, kind='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def file(self, path):
        if not path.is_file():
            return self.reply(404, b'Not found', 'text/plain')
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(path.stat().st_size))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        try:
            with path.open('rb') as stream:
                while block := stream.read(1024 * 1024):
                    self.wfile.write(block)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/', '/panoramas'):
            return self.file(ROOT / 'index.html')
        if path == '/config.json':
            public = dict(CONFIG)
            public['ready'] = all((ROOT / 'images' / (v['id'] + '_after.jpg')).exists() for v in CONFIG['views'])
            return self.reply(200, json.dumps(public).encode())
        if path.startswith('/images/'):
            p = (ROOT / path.lstrip('/')).resolve()
            if p.is_relative_to(ROOT / 'images'):
                return self.file(p)
        if path.startswith('/vendor/'):
            p = (REF / 'toaster_home_tour/vendor' / path[len('/vendor/'):]).resolve()
            if p.is_relative_to(REF / 'toaster_home_tour/vendor'):
                return self.file(p)
        if path == '/panorama.js':
            return self.file(ROOT / 'panorama.js')
        return self.reply(404, b'Not found', 'text/plain')

    def do_POST(self):
        path = urlsplit(self.path).path
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length < 20000000:
            return self.reply(400, b'Invalid upload size', 'text/plain')
        data = self.rfile.read(length)
        try:
            parts = path.strip('/').split('/')
            view = next(v for v in CONFIG['views'] if v['id'] == parts[1])
            if parts[0] == 'capture' and len(parts) == 3 and parts[2] in map(str, range(6)):
                import io
                image = Image.open(io.BytesIO(data)).convert('RGB')
                assert image.size == (SIZE, SIZE), image.size
                image.save(ROOT / 'faces' / ('%s_%s.png' % (view['id'], parts[2])))
                return self.reply(200, b'{"saved":true}')
            if parts[0] == 'assemble' and len(parts) == 2:
                faces = [np.asarray(Image.open(ROOT / 'faces' / ('%s_%d.png' % (view['id'], i)))) for i in range(6)]
                save_image(equirectangular(faces, np.asarray(view['rotations'])), ROOT / 'images' / (view['id'] + '_after.jpg'))
                paired_image(view['id'])
                return self.reply(200, b'{"assembled":true}')
        except Exception as error:
            return self.reply(400, json.dumps({'error': str(error)}).encode())
        return self.reply(404, b'Not found', 'text/plain')


if __name__ == '__main__':
    CONFIG = prepare()
    print('PANORAMA_SERVER_READY 8786', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8786), Handler).serve_forever()
