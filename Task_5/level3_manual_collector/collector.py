#!/usr/bin/env python3
"""Manual Habitat collector. No navigation policy or VLM is loaded."""
import argparse
import base64
import datetime as dt
import io
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse, urlencode
import zipfile

ROOT = Path(__file__).resolve().parent
BENCH = Path('/home/guest-isl/rishabh/bench')
SOURCE = BENCH / 'experiments/awarevln_levels_1_2_3_presentation/presentation.html'
SCENES = Path('/data/robotics/toshith/vln_baselines/data/scene_datasets/mp3d')


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def media_download_url(session, file):
    return '/api/media?' + urlencode({'session': session, 'file': file})


def session_directory(relative):
    directory = (ROOT / relative).resolve()
    if not directory.is_relative_to((ROOT / 'sessions').resolve()) or not (directory / 'inputs.json').is_file():
        raise ValueError('Unknown recording session.')
    return directory


def session_videos(directory):
    session = str(directory.relative_to(ROOT))
    files = []
    if (directory / 'manifest.json').is_file() and (directory / 'navigation.mp4').is_file():
        files.append({'label': 'Download navigation MP4', 'filename': 'navigation.mp4',
                      'url': media_download_url(session, 'navigation.mp4')})
    for file in sorted((directory / 'screen').glob('screen_*')):
        if file.is_file() and file.suffix in ['.webm', '.mp4']:
            relative = str(file.relative_to(directory))
            files.append({'label': 'Download screen recording · ' + file.name, 'filename': file.name,
                          'url': media_download_url(session, relative)})
    return files


def prepare():
    """Copy selected source inputs; preserve benchmark inputs unchanged."""
    html = SOURCE.read_text()
    match = re.search(r'<script id="presentation-data" type="application/json">(.*?)</script>', html, re.S)
    data = json.loads(match.group(1))
    case = next(c for c in data['cases'] if c['episode_key'] == 'QUCTc6BB5sX_8247')
    level = case['levels']['3']
    selected = level['inputs']['multiple_memories']['primary']
    memories = []
    for mid in selected['memory_ids']:
        m = dict(data['memories'][mid]); m['id'] = mid
        m['image_urls'] = [data['images'][p]['data_url'] for p in m['images']]
        memories.append(m)
    payload = {
        'episode_key': case['episode_key'], 'scene': 'QUCTc6BB5sX',
        'original_request': selected['assigned_task'],
        'default_request': selected['assigned_task'],
        'default_current_state': 'It is Thursday 07:30. I am carrying dirty school clothes. I need to take them to the remembered laundry area.',
        'scenario': 'User-authored dirty-clothes delivery demonstration; clothing is assumed, not rendered. This changes the original clean-clothes pickup scenario.',
        'memories': memories, 'route': case['route'],
        'source': str(SOURCE), 'source_goal_memory_id': selected['evaluator_rules']['goal_memory_id'],
        'reasoning_template': 'The request concerns [need]. Memory [ID] is relevant because [speech and visual evidence]. In my current view I see [visible evidence]. My next navigation decision is [action and reason].',
    }
    write_json(ROOT / 'sample_case.json', payload)
    print('Prepared laundry memories without running VILA or Habitat.')


class Collector:
    def __init__(self):
        import habitat_sim
        import numpy as np
        import quaternion
        from PIL import Image
        self.hs, self.np, self.q, self.Image = habitat_sim, np, quaternion, Image
        self.case = json.loads((ROOT / 'sample_case.json').read_text())
        cfg = habitat_sim.SimulatorConfiguration()
        cfg.scene_id = str(SCENES / self.case['scene'] / (self.case['scene'] + '.glb'))
        cfg.gpu_device_id = 0
        sensor = habitat_sim.SensorSpec()
        sensor.uuid = 'rgb'; sensor.sensor_type = habitat_sim.SensorType.COLOR
        sensor.resolution = [512, 512]; sensor.position = [0, 1.25, 0]
        sensor.parameters['hfov'] = '90'
        agent = habitat_sim.agent.AgentConfiguration()
        agent.sensor_specifications = [sensor]
        agent.action_space = {
            'forward': habitat_sim.agent.ActionSpec('move_forward', habitat_sim.agent.ActuationSpec(amount=0.25)),
            'left': habitat_sim.agent.ActionSpec('turn_left', habitat_sim.agent.ActuationSpec(amount=15)),
            'right': habitat_sim.agent.ActionSpec('turn_right', habitat_sim.agent.ActuationSpec(amount=15)),
        }
        self.sim = habitat_sim.Simulator(habitat_sim.Configuration(cfg, [agent]))
        self.agent = self.sim.initialize_agent(0)
        self.session = None; self.finished = False; self.frame_index = 0
        self.frames = []; self.path_length = 0.; self.actions = 0
        self.reset()

    def reset(self):
        if self.session and not self.finished:
            raise ValueError('Finish the current sample before resetting.')
        state = self.hs.AgentState()
        state.position = self.np.asarray(self.case['route']['start_position'], dtype=self.np.float32)
        x, y, z, w = self.case['route']['start_rotation_xyzw']
        state.rotation = self.q.quaternion(w, x, y, z)
        self.agent.set_state(state, reset_sensors=True)
        self.session = None; self.finished = False; self.path_length = 0.; self.actions = 0
        self.render()

    def render(self):
        self.rgb = self.sim.get_sensor_observations()['rgb'][..., :3].copy()
        buffer = io.BytesIO(); self.Image.fromarray(self.rgb).save(buffer, format='JPEG', quality=88)
        self.jpeg = buffer.getvalue()

    def pose(self):
        state = self.agent.get_state(); quat = state.rotation
        return {'position': state.position.tolist(), 'rotation_xyzw': [quat.x, quat.y, quat.z, quat.w]}

    def elapsed(self):
        return round(time.monotonic() - self.started, 6)

    def event(self, value):
        value = {'elapsed_seconds': self.elapsed(), 'frame_index': max(0, self.frame_index - 1), **value}
        with (self.session / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(value, ensure_ascii=False) + '\n')

    def capture(self, action, client_ms=None, collided=False):
        file = f'frames/{self.frame_index:06d}.png'
        self.Image.fromarray(self.rgb).save(self.session / file)
        row = {'frame_index': self.frame_index, 'elapsed_seconds': self.elapsed(), 'client_elapsed_ms': client_ms,
               'action': action, 'collided': bool(collided), 'frame_path': file, 'pose': self.pose()}
        with (self.session / 'trajectory.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        self.frames.append(row); self.frame_index += 1
        self.event({'type': 'action', 'action': action, 'collided': bool(collided)})

    def start(self, data):
        if self.session and not self.finished:
            raise ValueError('A recording is already active.')
        self.reset()
        user = str(data.get('annotator', '')).strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', user):
            raise ValueError('Use a 1–48 character annotator ID containing letters, digits, _ or -.')
        selected = data.get('relevant_memory_ids', [])
        known = {m['id'] for m in self.case['memories']}
        if not isinstance(selected, list) or not set(selected).issubset(known):
            raise ValueError('Unknown memory IDs.')
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        self.session = ROOT / 'sessions' / user / stamp
        (self.session / 'frames').mkdir(parents=True, exist_ok=False)
        (self.session / 'audio').mkdir(); (self.session / 'screen').mkdir()
        self.started = time.monotonic(); self.finished = False; self.frames = []; self.frame_index = 0
        self.actions = 0; self.path_length = 0.; self.recording_source = data.get('recording_source', 'human_manual')
        bundled_memories = []
        (self.session / 'memory_images').mkdir()
        for memory in self.case['memories']:
            copied = {k:v for k,v in memory.items() if k != 'image_urls'}
            copied['source_image_paths'] = copied['images']
            copied['images'] = []
            for index, url in enumerate(memory['image_urls']):
                relative = f"memory_images/{memory['id']}_{index:02d}.png"
                (self.session / relative).write_bytes(base64.b64decode(url.split(',',1)[1]))
                copied['images'].append(relative)
            bundled_memories.append(copied)
        write_json(self.session / 'inputs.json', {
            'annotator_id': user, 'scene': self.case['scene'], 'episode_key': self.case['episode_key'],
            'request': str(data.get('request', self.case['default_request'])),
            'current_state': str(data.get('current_state', self.case['default_current_state'])),
            'supplied_memories': bundled_memories,
            'human_selected_memory_ids': selected, 'original_benchmark_request': self.case['original_request'],
            'scenario': self.case['scenario'], 'source': self.case['source'],
        })
        # Evaluation coordinates are kept separate from robot inputs.
        write_json(self.session / 'evaluation_only.json', self.case['route'])
        self.capture('START', data.get('client_elapsed_ms'))
        self.event({'type': 'session_start', 'recording_source': self.recording_source})
        return self.status()

    def action(self, data):
        if not self.session or self.finished:
            raise ValueError('Start a recording before moving.')
        action = data.get('action')
        if action not in ['forward', 'left', 'right', 'stop']:
            raise ValueError('Only forward, left, right and stop are allowed. Backward is disabled.')
        if self.actions >= 500 and action != 'stop':
            raise ValueError('500 actions reached. Press STOP to finish.')
        if action == 'stop':
            return self.finish(data.get('client_elapsed_ms'))
        before = self.agent.get_state().position.copy()
        collided = self.sim.step(action).get('collided', False)
        self.path_length += float(self.np.linalg.norm(self.agent.get_state().position - before))
        self.actions += 1; self.render()
        self.capture(action.upper(), data.get('client_elapsed_ms'), collided)
        return self.status()

    def guidance(self):
        path = self.hs.ShortestPath(); state = self.agent.get_state()
        path.requested_start = state.position
        path.requested_end = self.np.asarray(self.case['route']['goals'][0]['position'], dtype=self.np.float32)
        if not self.sim.pathfinder.find_path(path):
            return {'text': 'No navmesh route found.', 'next_action': None, 'distance_m': None}
        distance = float(path.geodesic_distance)
        if distance <= 0.65:
            return {'text': 'At the authored destination. Inspect the view, then press STOP.', 'next_action': 'stop', 'distance_m': distance}
        remaining = .65; target = path.points[-1]
        for a,b in zip(path.points, path.points[1:]):
            segment = float(self.np.linalg.norm(b-a))
            if segment >= remaining:
                target = a + (b-a) * remaining / segment; break
            remaining -= segment
        forward = self.q.rotate_vectors(state.rotation, self.np.array([0.,0.,-1.]))
        delta = target - state.position
        current = math.atan2(-forward[0], -forward[2])
        desired = math.atan2(-delta[0], -delta[2])
        turn = math.degrees((desired-current+math.pi)%(2*math.pi)-math.pi)
        action = 'left' if turn > 7.6 else 'right' if turn < -7.6 else 'forward'
        hint = {'left': 'A: turn left 15°', 'right': 'D: turn right 15°', 'forward': 'W: move forward 25 cm'}[action]
        return {'text': hint, 'next_action': action, 'distance_m': round(distance,3)}

    def status(self):
        return {'active': bool(self.session and not self.finished), 'finished': self.finished,
                'session_id': str(self.session.relative_to(ROOT)) if self.session else None,
                'actions': self.actions, 'frames': self.frame_index if self.session else 0,
                'path_length_m': round(self.path_length,3), 'elapsed_seconds': self.elapsed() if self.session else 0,
                'download_url': '/api/download?session=' + str(self.session.relative_to(ROOT)) if self.session and self.finished else None,
                'videos': session_videos(self.session) if self.session else []}

    def annotate(self, data):
        if not self.session:
            raise ValueError('Start a session first.')
        if data.get('memory_ids') is not None and not set(data['memory_ids']).issubset({m['id'] for m in self.case['memories']}):
            raise ValueError('Unknown memory IDs.')
        self.event({'type': 'reasoning_annotation', 'text': str(data.get('text', '')),
                    'memory_ids': data.get('memory_ids', []), 'annotation_kind': data.get('kind','human_reasoning'),
                    'client_start_ms': data.get('client_start_ms'), 'client_end_ms': data.get('client_end_ms')})
        return self.status()

    def delete_sample(self, data):
        relative = data.get('session_id', '')
        parts = Path(relative).parts
        if len(parts) != 3 or parts[0] != 'sessions' or not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', parts[1]):
            raise ValueError('Select a saved sample to delete.')
        if data.get('confirm_session') != relative:
            raise ValueError('Confirm the exact sample before deleting it.')
        directory = session_directory(relative)
        if not (directory / 'manifest.json').is_file():
            raise ValueError('Finish saving the sample before deleting it.')
        if self.session == directory and not self.finished:
            raise ValueError('Stop and save the active recording before deleting it.')
        inputs = json.loads((directory / 'inputs.json').read_text())
        if inputs['annotator_id'] != parts[1]:
            raise ValueError('The selected sample does not match its annotator.')
        destination = ROOT / 'deleted_sessions' / parts[1] / directory.name
        if destination.exists():
            raise ValueError('A deleted copy already exists; it will not be overwritten.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if self.session == directory:
            self.reset()
        directory.rename(destination)
        write_json(destination / 'deletion.json', {
            'original_session_id': relative,
            'deleted_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'recoverable': True,
        })
        return {'deleted_session': relative, 'recoverable': True, 'state': self.status()}

    def upload(self, content, params):
        if not self.session:
            raise ValueError('Start a session before saving media.')
        kind = params.get('kind',['voice'])[0]
        if kind not in ['voice','screen']:
            raise ValueError('Unknown media type.')
        mime = params.get('mime',['video/webm' if kind=='screen' else 'audio/webm'])[0]
        extension = 'mp4' if 'mp4' in mime else 'ogg' if 'ogg' in mime else 'webm'
        folder = 'screen' if kind=='screen' else 'audio'
        index = len(list((self.session / folder).iterdir()))
        relative = f'{folder}/{kind}_{index:03d}.{extension}'
        (self.session / relative).write_bytes(content)
        self.event({'type': 'media', 'kind': kind, 'path': relative, 'mime_type': mime,
                    'client_start_ms': params.get('start_ms',[None])[0], 'client_end_ms': params.get('end_ms',[None])[0],
                    'size_bytes': len(content)})
        return {'path': relative, 'download_url': media_download_url(str(self.session.relative_to(ROOT)), relative)}

    def finish(self, client_ms=None):
        if self.finished:
            return self.status()
        self.capture('STOP', client_ms); self.finished = True
        info = self.guidance()
        self.event({'type': 'session_finished'})
        write_json(self.session / 'manifest.json', {
            'recording_source': self.recording_source, 'completed_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'frame_count': self.frame_index, 'movement_actions': self.actions, 'wall_duration_seconds': self.elapsed(),
            'path_length_m': self.path_length, 'forward_step_m': .25, 'turn_degrees': 15,
            'allowed_actions': ['FORWARD','LEFT','RIGHT','STOP'], 'backward_enabled': False,
            'native_goal_distance_m': info['distance_m'],
            'stop_within_original_3m': info['distance_m'] is not None and info['distance_m'] < 3,
            'scenario_matches_original_benchmark': False, 'assumed_item_is_rendered': False,
            'navigation_policy_loaded': False, 'vila_inference_run': False,
            'raw_video': 'navigation.mp4', 'video_fps': 5,
            'video_timing': 'Action frames held to their wall-clock durations; PNG ledger is the authoritative unsampled action record.',
            'model_input_warning': 'Keep evaluation_only.json and trajectory poses out of model input.',
        })
        self.export_video()
        return self.status()

    def export_video(self):
        import imageio_ffmpeg
        fps = 5; duration = min(self.elapsed(), 3600.)
        writer = imageio_ffmpeg.write_frames(str(self.session / 'navigation.mp4'), (512,512), fps=fps,
                    codec='libx264', macro_block_size=1, output_params=['-crf','20','-preset','fast','-movflags','+faststart'])
        writer.send(None); idx = 0; cached = None; old = -1
        try:
            for frame in range(max(1, math.ceil(duration * fps))):
                t = frame / fps
                while idx+1 < len(self.frames) and self.frames[idx+1]['elapsed_seconds'] <= t: idx += 1
                if idx != old:
                    with self.Image.open(self.session / self.frames[idx]['frame_path']) as image:
                        cached = self.np.asarray(image.convert('RGB')).copy()
                    old = idx
                writer.send(cached)
            # Preserve the final observation even when several actions arrived inside one video frame.
            writer.send(self.rgb)
        finally:
            writer.close()


class Handler(BaseHTTPRequestHandler):
    def response(self, data, mime='application/json', code=200, headers=None):
        if not isinstance(data, bytes): data = json.dumps(data).encode()
        self.send_response(code); self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data))); self.send_header('Cache-Control','no-store')
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        try:
            parsed = urlparse(self.path); path = parsed.path; app = self.server.app
            if path == '/api/case':
                return self.response({k:v for k,v in app.case.items() if k not in ['route','source_goal_memory_id']})
            if path == '/api/state': return self.response(app.status())
            if path == '/api/guidance':
                if app.session: app.event({'type':'oracle_guidance_viewed','usage':'Human annotation aid, never model input'})
                return self.response(app.guidance())
            if path == '/api/frame': return self.response(app.jpeg,'image/jpeg')
            if path == '/api/sessions':
                user = parse_qs(parsed.query).get('annotator',[''])[0]
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',user): return self.response([])
                result = []
                for p in sorted((ROOT/'sessions'/user).glob('*/manifest.json'),reverse=True):
                    result.append({'id':str(p.parent.relative_to(ROOT)), 'download':'/api/download?session='+str(p.parent.relative_to(ROOT)),
                                   'videos': session_videos(p.parent)})
                return self.response(result)
            if path == '/api/videos':
                relative = parse_qs(parsed.query)['session'][0]
                return self.response(session_videos(session_directory(relative)))
            if path == '/api/media':
                params = parse_qs(parsed.query)
                directory = session_directory(params['session'][0])
                relative = params['file'][0]
                if relative != 'navigation.mp4' and not re.fullmatch(r'(screen/screen_\d+\.(webm|mp4)|audio/voice_\d+\.(webm|ogg|mp4))', relative):
                    raise ValueError('Unknown recording media.')
                file = (directory / relative).resolve()
                if not file.is_relative_to(directory) or not file.is_file():
                    raise ValueError('Recording file is not available yet.')
                if relative == 'navigation.mp4' and not (directory / 'manifest.json').is_file():
                    raise ValueError('Finish navigation before downloading its MP4.')
                mime = {'.mp4':'video/mp4', '.webm':'video/webm' if relative.startswith('screen/') else 'audio/webm', '.ogg':'audio/ogg'}[file.suffix]
                # Stream the original media file without creating a ZIP or reading
                # a large screen recording into memory all at once.
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(file.stat().st_size))
                self.send_header('Content-Disposition', f'attachment; filename="{directory.name}_{file.name}"')
                self.end_headers()
                with file.open('rb') as source:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block: break
                        self.wfile.write(block)
                return
            if path == '/api/download':
                rel = parse_qs(parsed.query)['session'][0]; directory = (ROOT/rel).resolve()
                if not directory.is_relative_to((ROOT/'sessions').resolve()) or not (directory/'manifest.json').is_file():
                    raise ValueError('Unknown finished session.')
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
                    for file in sorted(directory.rglob('*')):
                        if file.is_file(): archive.write(file,str(file.relative_to(directory)))
                return self.response(buffer.getvalue(),'application/zip',headers={'Content-Disposition':f'attachment; filename="{directory.name}.zip"'})
            names = {'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if path not in names: return self.response({'error':'Not found'},code=404)
            file = ROOT/'web'/names[path]
            return self.response(file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'text/plain')
        except Exception as err:
            self.response({'error':str(err)},code=400)

    def do_POST(self):
        try:
            # This collector is served over a private localhost SSH tunnel only.
            origin = self.headers.get('Origin')
            if origin and urlparse(origin).netloc != self.headers.get('Host'):
                raise ValueError('Cross-origin requests are disabled.')
            length = int(self.headers.get('Content-Length','0'))
            if length > 300 * 1024 * 1024: raise ValueError('Upload exceeds 300 MB.')
            content = self.rfile.read(length); parsed = urlparse(self.path); app = self.server.app
            if parsed.path == '/api/upload': return self.response(app.upload(content,parse_qs(parsed.query)))
            data = json.loads(content or b'{}')
            routes = {'/api/start':app.start,'/api/action':app.action,'/api/annotate':app.annotate,
                      '/api/delete':app.delete_sample}
            if parsed.path == '/api/reset': app.reset(); return self.response(app.status())
            if parsed.path not in routes: return self.response({'error':'Not found'},code=404)
            return self.response(routes[parsed.path](data))
        except Exception as err:
            self.response({'error':str(err)},code=400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--port',type=int,default=8876)
    args = parser.parse_args()
    if args.prepare: prepare(); return
    # GL context and all simulator calls stay on this single server thread.
    app = Collector(); server = HTTPServer(('127.0.0.1',args.port),Handler); server.app = app
    print(f'READY http://127.0.0.1:{args.port} (one renderer; no model inference)',flush=True)
    try: server.serve_forever()
    finally: server.server_close(); app.sim.close()


if __name__ == '__main__': main()
