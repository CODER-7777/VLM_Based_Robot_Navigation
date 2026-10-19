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
import subprocess
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue
from urllib.parse import parse_qs, urlparse, urlencode
import zipfile
from presentation_cases import DEFAULT_EPISODE, collection_cases, environment_catalog, load_cases, load_house_cases, public_case

ROOT = Path(__file__).resolve().parent
BENCH = Path('/home/guest-isl/rishabh/bench')
SOURCE = BENCH / 'experiments/awarevln_levels_1_2_3_presentation/presentation.html'
SCENES = Path('/data/robotics/toshith/vln_baselines/data/scene_datasets/mp3d')


def write_json(path, data):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


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
        if file.is_file() and file.suffix == '.mp4':
            relative = str(file.relative_to(directory))
            files.append({'label': 'Download screen recording · ' + file.name, 'filename': file.name,
                          'url': media_download_url(session, relative)})
    return files


def session_audio(directory):
    session = str(directory.relative_to(ROOT))
    paths = sorted([*(directory / 'audio').glob('voice_*.mp4'),
                    *(directory / 'audio').glob('screen_*.m4a')])
    return [{'filename': file.name, 'url': media_download_url(session, str(file.relative_to(directory))),
             'label': 'Download ' + ('screen audio · ' if file.suffix == '.m4a' else 'voice · ') + file.name}
            for file in paths if file.is_file()]


def extract_screen_audio(directory, relative):
    """Create a separate audio-only clip; never rewrite the original screen video."""
    import imageio_ffmpeg
    directory = Path(directory).resolve()
    if not re.fullmatch(r'screen/screen_\d+\.mp4', relative):
        raise ValueError('Choose a saved screen recording for audio extraction.')
    source = directory / relative
    if source.is_symlink() or not source.resolve().is_relative_to(directory) or not source.is_file():
        raise ValueError('Screen recording is unavailable.')
    audio = directory / 'audio'
    if audio.is_symlink():
        raise ValueError('Audio directory must stay within the recording sample.')
    audio.mkdir(exist_ok=True)
    destination = audio / (source.stem + '.m4a')
    if destination.is_symlink():
        raise ValueError('Audio output must stay within the recording sample.')
    info = {'source_screen': relative, 'path': str(destination.relative_to(directory)),
            'mime_type': 'audio/mp4', 'derived_from_screen_recording': True}
    if destination.exists():
        if not destination.stat().st_size:
            raise ValueError('An empty audio output already exists; review it before replacing it.')
        return {**info, 'size_bytes': destination.stat().st_size, 'already_exists': True}
    temporary = destination.with_name('.' + destination.stem + '.' + uuid.uuid4().hex + '.partial.m4a')
    prefix = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
              '-i', str(source), '-map', '0:a:0', '-vn']
    try:
        try:
            subprocess.run(prefix + ['-c:a', 'copy', '-movflags', '+faststart', str(temporary)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            method = 'audio_stream_copy'
        except subprocess.CalledProcessError:
            subprocess.run(prefix + ['-c:a', 'aac', '-b:a', '160k', '-threads', '2',
                                     '-movflags', '+faststart', str(temporary)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            method = 'aac_transcode'
        temporary.replace(destination)
        info.update(size_bytes=destination.stat().st_size, extraction_method=method,
                    created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        write_json(destination.with_suffix('.source.json'), info)
        return {**info, 'already_exists': False}
    finally:
        temporary.unlink(missing_ok=True)


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
        default_case = json.loads((ROOT / 'sample_case.json').read_text())
        self.cases = load_cases(SOURCE, default_case)
        selection_path = ROOT / 'collection_selection.json'
        selection = json.loads(selection_path.read_text()) if selection_path.is_file() else {}
        if selection.get('authored_source_root'):
            self.cases.update(load_house_cases(selection['authored_source_root']))
        owner_file = ROOT / 'campus_owner.json'
        owner = json.loads(owner_file.read_text())['username'] if owner_file.is_file() else None
        self.collection_cases = collection_cases(self.cases, ROOT / 'collection_selection.json', owner)
        self.case = self.collection_cases.get(DEFAULT_EPISODE, next(iter(self.collection_cases.values())))
        self.frame_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='frame-save')
        self.media_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='mp4-export')
        self.frame_futures = []; self.jobs = {}; self.media_counters = {}
        self.event_lock = threading.Lock(); self.ended_elapsed = 0.; self.goal_reached = False
        self.sim = habitat_sim.Simulator(self.scene_configuration(self.case['scene']))
        self.agent = self.sim.initialize_agent(0)
        self.session = None; self.finished = False; self.frame_index = 0
        self.frames = []; self.path_length = 0.; self.actions = 0
        self.reset()

    def scene_configuration(self, scene):
        habitat_sim = self.hs
        cfg = habitat_sim.SimulatorConfiguration()
        cfg.scene_id = str(SCENES / scene / (scene + '.glb'))
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
        return habitat_sim.Configuration(cfg, [agent])

    def environments(self):
        return environment_catalog(self.collection_cases, SCENES)

    def public_case(self):
        return public_case(self.case)

    def activate_case(self, episode_key):
        if self.session and not self.finished:
            raise ValueError('STOP & save the current sample before changing environments.')
        if self.status()['processing']:
            raise ValueError('Wait for the current MP4 exports before changing environments.')
        if episode_key not in self.cases:
            raise ValueError('Choose an episode from the source presentation.')
        target = self.cases[episode_key]
        if not (SCENES / target['scene'] / (target['scene'] + '.glb')).is_file():
            raise ValueError('The selected environment scene file is unavailable.')
        previous = self.case
        if target['scene'] != previous['scene']:
            try:
                self.sim.reconfigure(self.scene_configuration(target['scene']))
                self.agent = self.sim.initialize_agent(0)
            except Exception:
                self.sim.reconfigure(self.scene_configuration(previous['scene']))
                self.agent = self.sim.initialize_agent(0)
                raise
        self.case = target
        self.reset()

    def select_case(self, data):
        if data.get('episode_key', '') not in self.collection_cases:
            raise ValueError('Choose a study episode available to your account from the collection menu.')
        self.activate_case(data.get('episode_key', ''))
        return {**self.response_state(), 'case': self.public_case()}

    def reset(self):
        if self.session and not self.finished:
            raise ValueError('Finish the current sample before resetting.')
        state = self.hs.AgentState()
        state.position = self.np.asarray(self.case['route']['start_position'], dtype=self.np.float32)
        x, y, z, w = self.case['route']['start_rotation_xyzw']
        state.rotation = self.q.quaternion(w, x, y, z)
        self.agent.set_state(state, reset_sensors=True)
        self.session = None; self.finished = False; self.path_length = 0.; self.actions = 0
        self.goal_reached = False; self.ended_elapsed = 0.; self.frame_index = 0
        self.goal_stage = 0
        self.render()

    def render(self, observations=None):
        if observations is None: observations = self.sim.get_sensor_observations()
        self.rgb = observations['rgb'][..., :3].copy()
        buffer = io.BytesIO(); self.Image.fromarray(self.rgb).save(buffer, format='JPEG', quality=82)
        self.jpeg = buffer.getvalue()

    def response_state(self):
        return {**self.status(), 'frame_data_url': 'data:image/jpeg;base64,' + base64.b64encode(self.jpeg).decode()}

    def pose(self):
        state = self.agent.get_state(); quat = state.rotation
        return {'position': state.position.tolist(), 'rotation_xyzw': [quat.x, quat.y, quat.z, quat.w]}

    def elapsed(self):
        if self.finished: return self.ended_elapsed
        return round(time.monotonic() - self.started, 6)

    def event(self, value):
        if not self.session: return
        value = {'elapsed_seconds': self.elapsed(), 'frame_index': max(0, self.frame_index - 1), **value}
        self.append_event(self.session, value)

    def append_event(self, session, value):
        with self.event_lock:
            with (session / 'events.jsonl').open('a') as stream:
                stream.write(json.dumps(value, ensure_ascii=False) + '\n')

    def save_frame(self, session, rgb, row):
        self.Image.fromarray(rgb).save(session / row['frame_path'], compress_level=1)
        with (session / 'trajectory.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')

    def capture(self, action, client_ms=None, collided=False):
        file = f'frames/{self.frame_index:06d}.png'
        row = {'frame_index': self.frame_index, 'elapsed_seconds': self.elapsed(), 'client_elapsed_ms': client_ms,
               'action': action, 'collided': bool(collided), 'frame_path': file, 'pose': self.pose()}
        self.frame_futures.append(self.frame_executor.submit(self.save_frame, self.session, self.rgb.copy(), row))
        self.frames.append(row); self.frame_index += 1
        self.event({'type': 'action', 'action': action, 'collided': bool(collided)})

    def start(self, data):
        if self.case['episode_key'] not in self.collection_cases:
            raise ValueError('Select a current study episode before creating a new sample. Older recordings remain available for review.')
        if self.session and not self.finished:
            raise ValueError('A recording is already active.')
        if data.get('episode_key', self.case['episode_key']) != self.case['episode_key']:
            raise ValueError('The environment changed in another tab. Reload its episode before starting.')
        if self.status()['processing']:
            raise ValueError('Wait for MP4 preparation before creating the next sample.')
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
        self.frame_futures = []
        bundled_memories = []
        (self.session / 'memory_images').mkdir()
        for memory in self.case['memories']:
            copied = {k:v for k,v in memory.items() if k != 'image_urls'}
            copied['source_image_paths'] = copied['images']
            copied['images'] = []
            for index, url in enumerate(memory['image_urls']):
                extension = 'jpg' if url.startswith('data:image/jpeg;') else 'png'
                relative = f"memory_images/{memory['id']}_{index:02d}.{extension}"
                (self.session / relative).write_bytes(base64.b64decode(url.split(',',1)[1]))
                copied['images'].append(relative)
            bundled_memories.append(copied)
        write_json(self.session / 'inputs.json', {
            'annotator_id': user, 'scene': self.case['scene'], 'episode_key': self.case['episode_key'],
            'request': str(data.get('request', self.case['default_request'])),
            'current_state': str(data.get('current_state', self.case['default_current_state'])),
            'supplied_memories': bundled_memories,
            'human_selected_memory_ids': selected, 'original_benchmark_request': self.case['original_request'],
            'memory_selection_source': data.get('memory_selection_source', 'episode_default'),
            'scenario': self.case['scenario'], 'source': self.case['source'],
            'source_sha256': self.case.get('source_sha256'), 'episode_title': self.case['title'],
            'scenario_matches_original_benchmark': bool(self.case.get('scenario_matches_original_benchmark', False))
                and str(data.get('request', self.case['default_request'])) == self.case['original_request']
                and str(data.get('current_state', self.case['default_current_state'])) == self.case['default_current_state'],
        })
        # Evaluation coordinates are kept separate from robot inputs.
        write_json(self.session / 'evaluation_only.json', self.case['route'])
        self.capture('START', data.get('client_elapsed_ms'))
        self.event({'type': 'session_start', 'recording_source': self.recording_source})
        self.advance_ordered_goals()
        return self.response_state()

    def action(self, data):
        if not self.session or self.finished:
            raise ValueError('This episode is complete. Create a new sample before recording another episode.')
        action = data.get('action')
        if action not in ['forward', 'left', 'right', 'stop']:
            raise ValueError('Only forward, left, right and stop are allowed. Backward is disabled.')
        if action == 'stop':
            return self.finish(data.get('client_elapsed_ms'))
        before = self.agent.get_state().position.copy()
        observations = self.sim.step(action)
        collided = observations.get('collided', False)
        self.path_length += float(self.np.linalg.norm(self.agent.get_state().position - before))
        self.actions += 1; self.render(observations)
        self.capture(action.upper(), data.get('client_elapsed_ms'), collided)
        self.advance_ordered_goals()
        self.goal_reached = self.guidance()['next_action'] == 'stop'
        return self.response_state()

    def advance_ordered_goals(self):
        """Record intermediate navigation visits, never simulated object handling."""
        goals = self.case['route']['goals']
        while self.goal_stage < len(goals) - 1:
            goal = goals[self.goal_stage]
            path = self.hs.ShortestPath()
            path.requested_start = self.agent.get_state().position
            path.requested_end = self.np.asarray(goal['position'], dtype=self.np.float32)
            if not self.sim.pathfinder.find_path(path) or path.geodesic_distance > goal.get('radius', 0.65):
                break
            self.goal_stage += 1
            self.event({'type': 'intermediate_navigation_stop', 'stop_index': self.goal_stage - 1,
                        'distance_m': float(path.geodesic_distance), 'object_handling_simulated': False})

    def guidance(self):
        path = self.hs.ShortestPath(); state = self.agent.get_state()
        path.requested_start = state.position
        goal = self.case['route']['goals'][self.goal_stage]
        path.requested_end = self.np.asarray(goal['position'], dtype=self.np.float32)
        if not self.sim.pathfinder.find_path(path):
            return {'text': 'No navmesh route found.', 'next_action': None, 'distance_m': None}
        distance = float(path.geodesic_distance)
        if distance <= goal.get('radius', 0.65):
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
        session_id = str(self.session.relative_to(ROOT)) if self.session else None
        jobs = [dict(j) for j in list(self.jobs.values()) if j['session_id'] == session_id]
        processing = any(j['status'] in ['queued','processing'] for j in jobs)
        video_ready = self.session and (self.session / 'navigation.mp4').is_file()
        audio = session_audio(self.session) if self.session else []
        return {'active': bool(self.session and not self.finished), 'finished': self.finished,
                'scene': self.case['scene'], 'episode_key': self.case['episode_key'], 'episode_title': self.case['title'],
                'session_id': session_id, 'annotator': self.session.parent.name if self.session else None,
                'actions': self.actions, 'frames': self.frame_index if self.session else 0,
                'path_length_m': round(self.path_length,3), 'elapsed_seconds': self.elapsed() if self.session else 0,
                'download_url': '/api/download?session=' + session_id if self.session and self.finished and video_ready and not processing else None,
                'videos': session_videos(self.session) if self.session else [], 'audio': audio,
                'goal_reached': self.goal_reached, 'processing': processing, 'media_jobs': jobs,
                'intermediate_stops_reached': self.goal_stage,
                'intermediate_stops_total': len(self.case['route']['goals']) - 1}

    def load_session(self, data):
        directory = session_directory(data.get('session_id',''))
        if self.session and not self.finished:
            raise ValueError('Finish the active sample before loading another session.')
        inputs = json.loads((directory / 'inputs.json').read_text())
        manifest = json.loads((directory / 'manifest.json').read_text())
        rows = [json.loads(line) for line in (directory / 'trajectory.jsonl').read_text().splitlines() if line.strip()]
        if not rows: raise ValueError('This saved sample has no observations.')
        episode_key = inputs.get('episode_key')
        if episode_key not in self.cases or self.cases[episode_key]['scene'] != inputs.get('scene'):
            raise ValueError('This saved sample is not in the presentation environment catalog.')
        self.activate_case(episode_key)
        state = self.hs.AgentState(); pose = rows[-1]['pose']
        state.position = self.np.asarray(pose['position'],dtype=self.np.float32)
        x,y,z,w = pose['rotation_xyzw']; state.rotation = self.q.quaternion(w,x,y,z)
        self.agent.set_state(state,reset_sensors=True); self.render()
        self.session=directory; self.finished=True; self.frames=rows; self.frame_futures=[]
        self.frame_index=len(rows); self.actions=manifest['movement_actions']
        self.path_length=manifest['path_length_m']; self.ended_elapsed=manifest['wall_duration_seconds']
        self.goal_stage=manifest.get('intermediate_stops_reached', 0)
        self.goal_reached=self.guidance()['next_action']=='stop'
        return {**self.response_state(), 'inputs': inputs, 'case': self.public_case()}

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
        if any(j['session_id']==relative and j['status'] in ['queued','processing'] for j in list(self.jobs.values())):
            raise ValueError('Wait for MP4 export to finish before deleting this sample.')
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
            raise ValueError('Create a new sample before recording.')
        requested = params.get('session', [str(self.session.relative_to(ROOT))])[0]
        if requested != str(self.session.relative_to(ROOT)):
            raise ValueError('This recording belongs to a different sample.')
        kind = params.get('kind', ['voice'])[0]
        if kind not in ['voice', 'screen']:
            raise ValueError('Unknown media type.')
        session = self.session; session_id = str(session.relative_to(ROOT))
        folder = 'screen' if kind == 'screen' else 'audio'
        key = (session_id, kind)
        if key not in self.media_counters:
            numbers = [int(p.stem.rsplit('_',1)[-1]) for p in (session/folder).glob(kind+'_*.mp4')]
            self.media_counters[key] = max(numbers, default=-1) + 1
        index = self.media_counters[key]; self.media_counters[key] += 1
        relative = f'{folder}/{kind}_{index:03d}.mp4'
        job_id = uuid.uuid4().hex
        staging = ROOT / '.uploads'; staging.mkdir(exist_ok=True)
        raw = staging / (job_id + '.upload'); raw.write_bytes(content)
        self.jobs[job_id] = {'id':job_id, 'session_id':session_id, 'kind':kind, 'status':'queued', 'path':relative}
        timing = {'client_start_ms':params.get('start_ms',[None])[0], 'client_end_ms':params.get('end_ms',[None])[0],
                  'elapsed_seconds':self.elapsed(), 'frame_index':max(0,self.frame_index-1)}
        self.media_executor.submit(self.convert_media, job_id, session, raw, relative, kind,
                                   params.get('mime',[''])[0], timing)
        return {'job_id':job_id, 'path':relative, 'status':'processing'}

    def convert_media(self, job_id, session, raw, relative, kind, mime, timing):
        import imageio_ffmpeg
        job = self.jobs[job_id]; job['status']='processing'
        destination = session / relative
        temporary = destination.with_name('.' + destination.stem + '.partial.mp4')
        try:
            cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw)]
            if kind == 'screen':
                cmd += ['-map','0:v:0','-map','0:a:0?']
                if 'mp4' in mime and ('avc1' in mime or 'h264' in mime):
                    cmd += ['-c','copy']
                else:
                    cmd += ['-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',
                            '-r','15','-threads','2','-c:a','aac','-b:a','160k']
            else:
                cmd += ['-map','0:a:0','-vn','-c:a','aac','-b:a','160k','-threads','2']
            cmd += ['-movflags','+faststart',str(temporary)]
            subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            temporary.replace(destination)
            if kind == 'screen':
                audio_info = extract_screen_audio(session, relative)
                self.append_event(session, {**timing, 'type':'screen_audio_extracted', **audio_info})
                job['audio_path'] = audio_info['path']
            raw.unlink()
            self.append_event(session, {**timing,'type':'media','kind':kind,'path':relative,
                'mime_type':'video/mp4' if kind=='screen' else 'audio/mp4',
                'source_mime_type':mime,'size_bytes':destination.stat().st_size,'clip_type':'reasoning' if kind=='voice' else 'screen'})
            job['status']='ready'; job['download_url']=media_download_url(str(session.relative_to(ROOT)),relative)
        except Exception as err:
            message = err.stderr.decode(errors='replace')[-700:] if isinstance(err,subprocess.CalledProcessError) else str(err)
            job.update(status='error',error=message)

    def finish(self, client_ms=None):
        if self.finished:
            return self.response_state()
        self.capture('STOP',client_ms)
        duration = self.elapsed(); self.ended_elapsed=duration; self.finished=True
        info=self.guidance(); self.goal_reached=info['next_action']=='stop'
        self.event({'type':'session_finished'})
        session=self.session
        manifest={
            'scene':self.case['scene'],'episode_key':self.case['episode_key'],'episode_title':self.case['title'],
            'recording_source':self.recording_source,'completed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'frame_count':self.frame_index,'movement_actions':self.actions,'wall_duration_seconds':duration,
            'path_length_m':self.path_length,'forward_step_m':.25,'turn_degrees':15,
            'allowed_actions':['FORWARD','LEFT','RIGHT','STOP'],'backward_enabled':False,
            'action_limit':None,'duration_limit_seconds':None,'native_goal_distance_m':info['distance_m'],
            'stop_within_original_3m':info['distance_m'] is not None and info['distance_m']<3,
            'scenario_matches_original_benchmark':json.loads((session/'inputs.json').read_text()).get('scenario_matches_original_benchmark',False),
            'assumed_item_is_rendered':False,
            'intermediate_stops_reached':self.goal_stage,
            'intermediate_stops_total':len(self.case['route']['goals'])-1,
            'ordered_navigation_complete':self.goal_reached,
            'navigation_policy_loaded':False,'vila_inference_run':False,'dashboard_version':2,
            'raw_video':'navigation.mp4','video_fps':5,'navigation_video_status':'processing',
            'video_timing':'Action frames held to their wall-clock durations; PNG ledger preserves each action.',
            'model_input_warning':'Keep evaluation coordinates, poses and oracle guidance out of model input.',
        }
        write_json(session/'manifest.json',manifest)
        job_id=uuid.uuid4().hex
        self.jobs[job_id]={'id':job_id,'session_id':str(session.relative_to(ROOT)),
                           'kind':'navigation','status':'queued','path':'navigation.mp4'}
        self.media_executor.submit(self.export_video,job_id,session,list(self.frames),
                                   list(self.frame_futures),self.rgb.copy(),duration,manifest)
        return self.response_state()

    def export_video(self, job_id, session, frames, frame_futures, final_rgb, duration, manifest):
        import imageio_ffmpeg
        job=self.jobs[job_id];job['status']='processing'
        try:
            for future in frame_futures:future.result()
            fps=5;temporary=session/'.navigation.partial.mp4'
            writer=imageio_ffmpeg.write_frames(str(temporary),(512,512),fps=fps,codec='libx264',macro_block_size=1,
                output_params=['-crf','20','-preset','veryfast','-threads','2','-movflags','+faststart'])
            writer.send(None);idx=0;old=-1;cached=None
            try:
                for frame in range(max(1,math.ceil(duration*fps))):
                    t=frame/fps
                    while idx+1<len(frames) and frames[idx+1]['elapsed_seconds']<=t:idx+=1
                    if idx!=old:
                        with self.Image.open(session/frames[idx]['frame_path']) as image:
                            cached=self.np.asarray(image.convert('RGB')).copy()
                        old=idx
                    writer.send(cached)
                writer.send(final_rgb)
            finally:writer.close()
            temporary.replace(session/'navigation.mp4')
            manifest['navigation_video_status']='ready';write_json(session/'manifest.json',manifest)
            job['status']='ready';job['download_url']=media_download_url(str(session.relative_to(ROOT)),'navigation.mp4')
        except Exception as err:
            job.update(status='error',error=str(err))
            manifest['navigation_video_status']='error';manifest['export_error']=str(err)
            write_json(session/'manifest.json',manifest)


class RendererActor:
    """Keep GL on one thread; HTTP uploads/downloads run on other threads."""
    def __init__(self):
        self.commands=Queue();self.ready=Future()
        self.thread=threading.Thread(target=self.run,name='habitat-renderer',daemon=True)
        self.thread.start();self.ready.result(timeout=90)

    def run(self):
        try:
            app=Collector();self.ready.set_result(True)
        except Exception as err:
            self.ready.set_exception(err);return
        while True:
            name,args,result=self.commands.get()
            try:
                if name=='_close':
                    app.frame_executor.shutdown(wait=True);app.media_executor.shutdown(wait=True);app.sim.close()
                    result.set_result(None);return
                value=getattr(app,args[0]) if name=='_property' else getattr(app,name)(*args)
                result.set_result(value)
            except Exception as err:result.set_exception(err)

    def call(self,name,*args):
        result=Future();self.commands.put((name,args,result));return result.result()

    def __getattr__(self,name):
        if name in ['case','session','jpeg','jobs']:
            return self.call('_property',name)
        return lambda *args:self.call(name,*args)

    def close(self):
        self.call('_close');self.thread.join()


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
                return self.response(app.public_case())
            if path == '/api/environments': return self.response(app.environments())
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
                    info=json.loads((p.parent/'inputs.json').read_text())
                    result.append({'id':str(p.parent.relative_to(ROOT)), 'download':'/api/download?session='+str(p.parent.relative_to(ROOT)),
                                   'scene':info['scene'], 'episode_key':info['episode_key'],
                                   'episode_title':info.get('episode_title', info['episode_key']),
                                   'videos': session_videos(p.parent), 'inputs':info,
                                   'audio':session_audio(p.parent)})
                return self.response(result)
            if path == '/api/jobs':
                return self.response([dict(j) for j in list(app.jobs.values())])
            if path == '/api/videos':
                relative = parse_qs(parsed.query)['session'][0]
                return self.response(session_videos(session_directory(relative)))
            if path == '/api/media':
                params = parse_qs(parsed.query)
                directory = session_directory(params['session'][0])
                relative = params['file'][0]
                if relative != 'navigation.mp4' and not re.fullmatch(r'(screen/screen_\d+\.mp4|audio/voice_\d+\.mp4|audio/screen_\d+\.m4a)', relative):
                    raise ValueError('Unknown recording media.')
                file = (directory / relative).resolve()
                if not file.is_relative_to(directory) or not file.is_file():
                    raise ValueError('Recording file is not available yet.')
                if relative == 'navigation.mp4' and not (directory / 'manifest.json').is_file():
                    raise ValueError('Finish navigation before downloading its MP4.')
                mime = 'audio/mp4' if relative.startswith('audio/') else 'video/mp4'
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
                session_id=str(directory.relative_to(ROOT))
                if any(j['session_id']==session_id and j['status'] in ['queued','processing'] for j in list(app.jobs.values())):
                    raise ValueError('MP4 files are still being prepared. Please wait a moment.')
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
                    for file in sorted(directory.rglob('*')):
                        if file.is_file() and not file.name.startswith('.') and file.suffix not in ['.webm','.ogg','.tmp']:
                            archive.write(file,str(file.relative_to(directory)))
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
                      '/api/delete':app.delete_sample, '/api/load':app.load_session, '/api/select':app.select_case}
            if parsed.path == '/api/reset': app.reset(); return self.response(app.response_state())
            if parsed.path not in routes: return self.response({'error':'Not found'},code=404)
            return self.response(routes[parsed.path](data))
        except Exception as err:
            self.response({'error':str(err)},code=400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--port',type=int,default=8878)
    args = parser.parse_args()
    if args.prepare: prepare(); return
    # The actor owns GL. Threaded HTTP keeps large media transfers off controls.
    app = RendererActor(); server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler); server.app = app
    print(f'READY http://127.0.0.1:{args.port} (one renderer; no model inference)',flush=True)
    try: server.serve_forever()
    finally:
        server.server_close(); app.close()


if __name__ == '__main__': main()
