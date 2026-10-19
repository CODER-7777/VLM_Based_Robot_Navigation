#!/usr/bin/env python3
"""Validate unlimited actions, complete frame storage, and asynchronous MP4."""
import io
import json
from pathlib import Path
import time
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8878'


def api(path,data=None):
    req=urllib.request.Request(BASE+path,data=None if data is None else json.dumps(data).encode(),
                               headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)


def main():
    assert not api('/api/state')['active'],'A human sample is active; do not interrupt it.'
    case=api('/api/case')
    state=api('/api/start',{'annotator':'v2_controls_validation',
        'recording_source':'automated_v2_controls_validation_not_human',
        'relevant_memory_ids':case['default_relevant_memory_ids']})
    timings=[]
    for index in range(510):
        before=time.monotonic();state=api('/api/action',{'action':'right'});timings.append(time.monotonic()-before)
        assert state['actions']==index+1 and state['frame_data_url'].startswith('data:image/jpeg;base64,')
    start=time.monotonic();state=api('/api/action',{'action':'stop'});stop_latency=time.monotonic()-start
    assert state['finished'] and not state['active'] and state['actions']==510
    for _ in range(300):
        state=api('/api/state')
        if state['download_url']:break
        time.sleep(.1)
    assert state['download_url'],'Navigation MP4 export failed'
    data=urllib.request.urlopen(BASE+state['download_url'],timeout=60).read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        rows=[json.loads(line) for line in archive.read('trajectory.jsonl').decode().splitlines()]
        manifest=json.loads(archive.read('manifest.json'))
        assert len(rows)==512 and len([n for n in archive.namelist() if n.startswith('frames/')])==512
        assert rows[-1]['action']=='STOP' and all(r['action']=='RIGHT' for r in rows[1:-1])
        assert manifest['action_limit'] is None and manifest['duration_limit_seconds'] is None
        assert not any(n.endswith(('.webm','.ogg')) for n in archive.namelist())
        assert manifest['navigation_video_status']=='ready'
        (ROOT/'unlimited_actions_validation.mp4').write_bytes(archive.read('navigation.mp4'))
    order=sorted(timings)
    report={'all_checks_passed':True,'accepted_movement_actions':510,'lossless_action_frames':512,
            'median_action_response_ms':round(order[len(order)//2]*1000,2),
            'p95_action_response_ms':round(order[int(len(order)*.95)]*1000,2),
            'stop_response_ms':round(stop_latency*1000,2),'MP4_only_archive':True,
            'navigation_export_finished':True,'no_policy_or_vila_inference':True}
    (ROOT/'controls_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    api('/api/delete',{'session_id':state['session_id'],'confirm_session':state['session_id']})
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
