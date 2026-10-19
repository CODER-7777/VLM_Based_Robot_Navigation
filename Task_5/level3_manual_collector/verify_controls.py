#!/usr/bin/env python3
"""Record a clearly labelled automated control check, never a human demo."""
import io
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8876'


def request(path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(BASE+path,data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as response:
        return json.load(response)


def main():
    assert not request('/api/state')['active'], 'Human recording active; do not interrupt it.'
    case = request('/api/case')
    assert len(case['memories']) == 3 and 'route' not in case
    state = request('/api/start', {'annotator':'controls_validation',
        'recording_source':'scripted_controls_verification_not_human',
        'relevant_memory_ids':['uniforms'], 'request':case['default_request'],
        'current_state':case['default_current_state']})
    session = state['session_id']
    request('/api/annotate', {'kind':'validation_provenance',
        'text':'Automated controls verification using the optional navmesh route aid. No person spoke or controlled this run.'})
    try:
        request('/api/action', {'action':'backward'})
        raise AssertionError('Backward motion was accepted')
    except urllib.error.HTTPError as error:
        assert error.code == 400
    assert request('/api/state')['actions'] == 0
    for _ in range(12):
        request('/api/action', {'action':'right'})
        time.sleep(.08)
    reached = False
    for index in range(250):
        guide = request('/api/guidance')
        if guide['next_action'] == 'stop':
            reached = True; break
        assert guide['next_action'] in ['forward','left','right']
        request('/api/action', {'action':guide['next_action']})
        time.sleep(.08)
    assert reached, 'Route aid did not reach the destination within 250 actions'
    state = request('/api/action', {'action':'stop'})
    assert state['finished'] and not state['active']
    assert any(s['id']==session for s in request('/api/sessions?annotator=controls_validation'))
    sample = urllib.request.urlopen(BASE+state['download_url'],timeout=60).read()
    (ROOT/'controls_validation.zip').write_bytes(sample)
    with zipfile.ZipFile(io.BytesIO(sample)) as archive:
        assert archive.testzip() is None
        rows = [json.loads(x) for x in archive.read('trajectory.jsonl').decode().splitlines()]
        manifest = json.loads(archive.read('manifest.json'))
        assert rows[-1]['action'] == 'STOP'
        assert set(r['action'] for r in rows).issubset({'START','STOP','FORWARD','LEFT','RIGHT'})
        assert len(rows)==manifest['frame_count']
        start = rows[0]['pose']; turned = rows[12]['pose']
        assert max(abs(a-b) for a,b in zip(start['position'],turned['position'])) < 1e-5
        qa,qb=start['rotation_xyzw'],turned['rotation_xyzw']
        # Twelve 15-degree turns rotate 180 degrees; quaternion dot is cos(90°).
        assert abs(sum(a*b for a,b in zip(qa,qb))) < .001
        assert manifest['native_goal_distance_m'] <= .65
        assert not manifest['navigation_policy_loaded'] and not manifest['vila_inference_run']
        assert archive.getinfo('navigation.mp4').file_size > 0
        assert len([n for n in archive.namelist() if n.startswith('memory_images/')]) == 9
        (ROOT/'validation_navigation.mp4').write_bytes(archive.read('navigation.mp4'))
        (ROOT/'validation_final_frame.png').write_bytes(archive.read(rows[-1]['frame_path']))
    report={'all_checks_passed':True,'session_id':session,'movement_actions':state['actions'],
        'frame_count':len(rows),'final_geodesic_distance_m':manifest['native_goal_distance_m'],
        'backward_rejected':True,'twelve_right_turns_preserve_position_and_rotate_180_degrees':True,
        'all_frames_and_memories_bundled':True,'zip_crc_passed':True,
        'human_voice_recorded':False,'recording_source':manifest['recording_source']}
    (ROOT/'controls_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    request('/api/reset',{})
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
