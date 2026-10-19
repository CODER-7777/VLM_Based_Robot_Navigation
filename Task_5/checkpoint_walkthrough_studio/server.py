"""Local checkpoint review and recording server; independent of collector V2."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, parse_qs, unquote, urlencode
from urllib.request import Request, urlopen
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
SESSIONS = ROOT / 'sessions'
LOCK = threading.RLock()
POOL = ThreadPoolExecutor(max_workers=2)
UPSTREAM = 'http://127.0.0.1:8912'
JOBS = {}


def utc():
    return datetime.now(timezone.utc).isoformat()


def slug(value):
    return re.sub(r'[^A-Za-z0-9_-]+', '_', str(value)).strip('_')[:60] or 'anonymous'


def session_path(sid):
    parts = sid.split('/')
    if len(parts) != 2 or any(not re.fullmatch(r'[A-Za-z0-9_-]+', p) for p in parts):
        raise ValueError('Invalid sample ID')
    p = SESSIONS.joinpath(*parts)
    if not (p / 'manifest.json').is_file():
        raise ValueError('Sample not found')
    return p


def manifest(path):
    return json.loads((path / 'manifest.json').read_text())


def save_manifest(path, data):
    tmp = path / 'manifest.tmp'
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path / 'manifest.json')


def append(path, filename, data):
    with LOCK, (path / filename).open('a') as out:
        out.write(json.dumps(data, ensure_ascii=False) + '\n')


def convert_media(sid, token, source, kind):
    path = session_path(sid)
    dest = path / ('voice' if kind == 'voice' else kind) / (token + '.mp4')
    dest.parent.mkdir(exist_ok=True)
    with LOCK:
        JOBS[token]['status'] = 'converting'
    try:
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise RuntimeError('ffmpeg is required to convert recordings')
        args = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source)]
        if kind == 'voice':
            args += ['-vn', '-c:a', 'aac', '-b:a', '128k']
        else:
            args += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                     '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-pix_fmt', 'yuv420p', '-c:a', 'aac']
        args += ['-movflags', '+faststart', str(dest)]
        proc = subprocess.run(args, capture_output=True, timeout=1800)
        if proc.returncode:
            raise RuntimeError(proc.stderr.decode(errors='replace')[-2000:])
        with LOCK:
            m = manifest(path)
            m['media'].append({'kind': kind, 'path': str(dest.relative_to(path)),
                               'bytes': dest.stat().st_size, 'job': token})
            save_manifest(path, m)
            JOBS[token].update(status='ready', path=str(dest.relative_to(path)))
        source.unlink()
    except Exception as error:
        with LOCK:
            JOBS[token].update(status='error', error=str(error))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def json_response(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def proxy(self, command, data=None):
        allowed = {'health', 'select', 'state', 'step', 'look', 'action', 'props', 'jump'}
        if command not in allowed:
            raise ValueError('Unknown renderer operation')
        try:
            req = Request(UPSTREAM + '/' + command,
                          data=json.dumps(data).encode() if data is not None else None,
                          headers={'Content-Type': 'application/json'})
            with urlopen(req, timeout=190) as res:
                return self.json_response(200, json.load(res))
        except HTTPError as error:
            return self.json_response(error.code, json.loads(error.read()))
        except (URLError, OSError) as error:
            return self.json_response(503, {'error': 'Live simulator unavailable. Recorded video and panoramas are available.', 'detail': str(error)})

    def file(self, path, download=None):
        if not path.is_file():
            return self.send_error(404)
        size = path.stat().st_size
        start, end, partial = 0, size - 1, False
        header = self.headers.get('Range')
        if header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', header)
            if not match or not any(match.groups()):
                return self.send_error(416)
            a, b = match.groups()
            if a:
                start, end = int(a), min(int(b) if b else end, end)
            else:
                start = max(0, size - int(b))
            if start >= size or end < start:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            partial = True
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        if download:
            self.send_header('Content-Disposition', 'attachment; filename="' + download + '"')
        self.end_headers()
        if self.command == 'HEAD':
            return
        try:
            with path.open('rb') as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    block = stream.read(min(262144, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_HEAD(self):
        return self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == '/api/health':
                return self.json_response(200, {'app': 'checkpoint-walkthrough-studio', 'local_storage': str(SESSIONS)})
            if u.path.startswith('/api/live/'):
                return self.proxy(u.path.rsplit('/', 1)[-1])
            if u.path == '/api/sessions':
                user = slug(q.get('user', ['anonymous'])[0])
                entries = []
                for f in sorted((SESSIONS / user).glob('*/manifest.json'), reverse=True):
                    try:
                        entries.append(manifest(f.parent))
                    except (ValueError, OSError):
                        continue
                return self.json_response(200, entries)
            if u.path == '/api/sample':
                sid = q['id'][0]
                with LOCK:
                    m = manifest(session_path(sid))
                    m['jobs'] = [dict(id=k, **v) for k, v in JOBS.items() if v['sample'] == sid]
                return self.json_response(200, m)
            if u.path == '/api/download':
                sid = q['id'][0]
                p = session_path(sid)
                with LOCK:
                    if any(v['sample'] == sid and v['status'] != 'ready' for v in JOBS.values()):
                        return self.json_response(409, {'error': 'Wait for media conversion, or inspect a failed upload.'})
                # Streaming a disk ZIP avoids loading long recordings into RAM.
                target = p / 'sample.zip'
                with LOCK, zipfile.ZipFile(target.with_suffix('.tmp'), 'w', zipfile.ZIP_STORED) as z:
                    for f in sorted(p.rglob('*')):
                        rel = f.relative_to(p)
                        if f.is_file() and not any(s.startswith('.') for s in rel.parts) and f.name not in ('sample.zip', 'sample.tmp', 'manifest.tmp'):
                            z.write(f, str(rel))
                target.with_suffix('.tmp').replace(target)
                return self.file(target, p.name + '.zip')
            if u.path == '/':
                return self.file(ROOT / 'web/index.html')
            if u.path.startswith(('/assets/', '/web/')):
                p = (ROOT / unquote(u.path).lstrip('/')).resolve()
                if not p.is_relative_to(ROOT / u.path.split('/')[1]):
                    raise ValueError('Invalid asset path')
                return self.file(p)
            return self.send_error(404)
        except (ValueError, KeyError, OSError) as error:
            return self.json_response(400, {'error': str(error)})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if u.path == '/api/upload':
                q = parse_qs(u.query)
                sid, kind = q['id'][0], q['kind'][0]
                if kind not in ('voice', 'scene', 'screen'):
                    raise ValueError('Unknown recording kind')
                if not 0 < length <= 2 * 1024**3:
                    raise ValueError('Empty upload or upload over 2 GB')
                path = session_path(sid)
                token = datetime.now(timezone.utc).strftime('%H%M%S_') + uuid.uuid4().hex[:10]
                directory = path / '.uploads'
                directory.mkdir(exist_ok=True)
                source = directory / (token + '.webm')
                remaining = length
                with source.open('xb') as out:
                    while remaining:
                        block = self.rfile.read(min(262144, remaining))
                        if not block:
                            raise ValueError('Incomplete upload')
                        out.write(block)
                        remaining -= len(block)
                with LOCK:
                    JOBS[token] = dict(sample=sid, kind=kind, status='queued', created=utc())
                source.with_suffix('.json').write_text(json.dumps({'kind': kind}))
                POOL.submit(convert_media, sid, token, source, kind)
                return self.json_response(202, {'job': token})
            if length > 2_000_000:
                raise ValueError('Request too large')
            data = json.loads(self.rfile.read(length) or b'{}')
            if u.path.startswith('/api/live/'):
                return self.proxy(u.path.rsplit('/', 1)[-1], data)
            if u.path == '/api/new':
                tours = json.loads((ROOT / 'assets/tours.json').read_text())['tours']
                tour_id = data.get('tour_id', 'pilot04')
                tour = next((t for t in tours if t['id'] == tour_id), None)
                if tour is None:
                    raise ValueError('Unknown tour')
                plan_path = (ROOT / tour['assets'].lstrip('/') / 'plan.json').resolve()
                if not plan_path.is_relative_to(ROOT / 'assets'):
                    raise ValueError('Invalid tour asset path')
                selected_plan = json.loads(plan_path.read_text())
                user = slug(data.get('user', 'anonymous'))
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_') + uuid.uuid4().hex[:6]
                sid = user + '/' + stamp
                path = SESSIONS / sid
                path.mkdir(parents=True)
                m = dict(id=sid, user=user, created=utc(), status='collecting', media=[],
                         task=data.get('task', ''), context=data.get('context', ''), transcript='',
                         scene=selected_plan['scene'], pilot=tour_id, tour_id=tour_id, authored=True)
                save_manifest(path, m)
                (path / 'events.jsonl').touch()
                (path / 'trajectory.jsonl').touch()
                shutil.copy(plan_path, path / 'pilot_plan.json')
                return self.json_response(201, m)
            path = session_path(data['id'])
            if u.path == '/api/event':
                event = dict(data.get('event', {}), server_time=utc())
                append(path, 'events.jsonl', event)
                if event.get('pose'):
                    append(path, 'trajectory.jsonl', event)
                return self.json_response(200, {'saved': True})
            if u.path in ('/api/save', '/api/note'):
                with LOCK:
                    m = manifest(path)
                    for key in ('task', 'context', 'transcript'):
                        if key in data:
                            m[key] = str(data[key])
                    if u.path == '/api/save':
                        m.update(status='saved', saved=utc())
                    save_manifest(path, m)
                    (path / 'transcript.txt').write_text(m['transcript'])
                return self.json_response(200, m)
            return self.send_error(404)
        except (ValueError, KeyError, OSError) as error:
            return self.json_response(400, {'error': str(error)})


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8900)
    ap.add_argument('--upstream', default=UPSTREAM)
    args = ap.parse_args()
    UPSTREAM = args.upstream
    # Recover interrupted uploads after a restart; preserve failed originals.
    for source in SESSIONS.glob('*/*/.uploads/*.webm'):
        path = source.parent.parent
        sid = str(path.relative_to(SESSIONS))
        # Kind is persisted through a sidecar by newer clients; older incomplete uploads remain available on disk.
        if source.with_suffix('.json').exists():
            kind = json.loads(source.with_suffix('.json').read_text())['kind']
            JOBS[source.stem] = dict(sample=sid, kind=kind, status='queued', created=utc())
            POOL.submit(convert_media, sid, source.stem, source, kind)
    print(f'Checkpoint Walkthrough Studio: http://127.0.0.1:{args.port}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
